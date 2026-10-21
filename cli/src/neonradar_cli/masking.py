"""Validation messages that never show a value from a real record (PHASE-2.md M2.0, G9).

`neonradar contracts validate-records` prints each issue with the file and line of its record.
A synthetic record's line is `<file>:<line>: <rule> <record id>: <message>`, as in Phase 1 with
the place in front, except that a quoted id of a record that is not synthetic (a synthetic record
may reference a real one) shows as `<record id>`. Every other record (a dataset that is not
synthetic or not in the registry, or an id without the `syn` prefix) gets
`<file>:<line>: <rule>: <message>` with each quoted value replaced by `<value>`, anything after
`input_value=` up to the next comma or closing bracket replaced too, the dict keys and unknown
keys in an `nr.` path replaced, numbers of five or more digits replaced (and any value in the
envelope messages about dates and datasets), and its record id left out: the line number
identifies the record. A schema name that FollowTheMoney does not know is counted as
`<unknown schema>`. Line breaks inside a message are printed as escapes (`\\n`), so one issue is
always one line.

The frozen validator in `neonradar_contracts.records` is used as it is: this module only reads
each file once more to number its records, then formats what the validator reports.
"""

import re
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Any

from followthemoney import model

from neonradar_contracts import records
from neonradar_contracts.datasets import Registry, load_registry

VALUE = "<value>"
RECORD_ID = "<record id>"
# A value written as a Python repr: a quote that does not follow a letter or digit (so "it's"
# starts nothing), up to the matching quote, with backslash escapes inside.
QUOTED = re.compile(r"""(?<![A-Za-z0-9])(?:'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*")""")
INPUT_VALUE = re.compile(r"input_value=[^,\])}]*")
# `nr.<path>: <message>` (records._check_nr): the path holds pydantic's location, whose dict keys
# can be another record's id and whose first part, for an unknown key, can be any text. Greedy,
# so a key with ": " in it is masked whole (pydantic messages start with a capital letter).
NR_PATH = re.compile(r"^nr\.(?P<path>.*): (?=[A-Z])", re.DOTALL)
NR_FIELDS = frozenset(records.NrExtension.model_fields)
LONG_NUMBER = re.compile(r"\d{5,}")  # a number that is not a string value, such as 19790801
# Envelope messages that print a value of any type (records._check_envelope, _check_dataset), so
# a short number such as a year is masked there too.
ENVELOPE = (
    re.compile(
        r"^(?:first_seen|last_seen|last_change) (?P<value>.*) is not an ISO 8601 date$", re.DOTALL
    ),
    re.compile(r"\(got (?P<value>.*)\); create records", re.DOTALL),
)
# One issue is one output line: line breaks in a message are printed as escapes.
LINE_BREAKS = str.maketrans(
    {char: repr(char)[1:-1] for char in "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"}
)
UNKNOWN_SCHEMA = "<unknown schema>"
DUPLICATE = "duplicate id"  # the start of the validator's R4 message for a repeated id


@dataclass(frozen=True, slots=True)
class Place:
    """Where a record is, and whether its messages must be masked."""

    path: Path
    line: int
    record_id: str | None
    masked: bool


def _nr_path(match: re.Match[str]) -> str:
    field, _, rest = match["path"].partition(".")
    return f"nr.{field if field in NR_FIELDS else VALUE}{'.' + VALUE if rest else ''}: "


def mask(message: str, record_id: str | None = None) -> str:
    """The message with the record id, quoted values, `input_value=`, `nr.` keys and long
    numbers left out."""
    if record_id:
        message = message.replace(record_id, RECORD_ID)
    message = NR_PATH.sub(_nr_path, message, count=1)
    for pattern in ENVELOPE:
        if found := pattern.search(message):
            message = message[: found.start("value")] + VALUE + message[found.end("value") :]
    message = INPUT_VALUE.sub("input_value=" + VALUE, message)
    message = QUOTED.sub(VALUE, message)
    return LONG_NUMBER.sub(VALUE, message)


def _real_id(match: re.Match[str]) -> str:
    ref = records.ID_RE.fullmatch(match.group(0)[1:-1])
    return RECORD_ID if ref and ref["prefix"] != records.SYNTHETIC_PREFIX else match.group(0)


def hide_real_ids(message: str) -> str:
    """The message with every quoted id of a record that is not synthetic left out."""
    return QUOTED.sub(_real_id, message)


def is_synthetic(data: dict[str, Any], registry: Registry) -> bool:
    """True only for a record whose datasets are all synthetic ones and whose id starts `syn-`."""
    slugs = data.get("datasets")
    if not isinstance(slugs, list) or not slugs:
        return False
    for slug in slugs:
        dataset = registry.get(slug) if isinstance(slug, str) else None
        if dataset is None or not dataset.synthetic:
            return False
    rid = data.get("id")
    return isinstance(rid, str) and rid.startswith(records.SYNTHETIC_PREFIX + "-")


def numbered_records(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """`records.iter_records(path)` with the line number of each record.

    `iter_records` skips the lines that are blank once decoded, so the same lines are skipped
    here; a line it cannot read raises `RecordFileError` from `iter_records` itself.
    """
    yield from zip(_line_numbers(path), records.iter_records(path), strict=False)


def _line_numbers(path: Path) -> Iterator[int]:
    with path.open("rb") as handle:
        for number, raw in enumerate(handle, start=1):
            if raw.decode("utf-8", errors="replace").strip():
                yield number


def schema_name(data: dict[str, Any]) -> str:
    """The record's schema for the counts, or `<unknown schema>` (it could be any text)."""
    name = data.get("schema")
    return name if isinstance(name, str) and model.get(name) is not None else UNKNOWN_SCHEMA


def _seen_by_batch(data: dict[str, Any]) -> bool:
    """The records `records.validate_batch` takes into account (it skips the others)."""
    name = data.get("schema")
    schema = model.get(name) if isinstance(name, str) else None
    return schema is not None and isinstance(data.get("properties"), dict)


def line_for(place: Place, issue: records.RecordIssue) -> str:
    where = f"{place.path}:{place.line}"
    if place.masked:
        line = f"{where}: {issue.rule}: {mask(issue.message, issue.record_id)}"
    else:
        rid = issue.record_id or "<no id>"
        line = f"{where}: {issue.rule} {rid}: {hide_real_ids(issue.message)}"
    return line.translate(LINE_BREAKS)


def validate(paths: Sequence[Path], strict: bool) -> tuple[Counter[str], list[str]]:
    """Validate the files as one load, like `records.validate_files`; one output line per issue.

    Raises `records.RecordFileError` on a line that is not one JSON object.
    """
    registry = load_registry()
    counts: Counter[str] = Counter()
    lines: list[str] = []
    places: dict[str, list[Place]] = {}
    for path in paths:
        for number, data in numbered_records(path):
            counts[schema_name(data)] += 1
            rid = data["id"] if isinstance(data.get("id"), str) else None
            place = Place(path, number, rid, masked=not is_synthetic(data, registry))
            if rid is not None and _seen_by_batch(data):
                places.setdefault(rid, []).append(place)
            lines.extend(line_for(place, issue) for issue in records.validate_record(data))
    batch = chain.from_iterable(records.iter_records(path) for path in paths)
    repeats: Counter[str] = Counter()
    for issue in records.validate_batch(batch, strict):
        rid = issue.record_id or ""
        found = places.get(rid)
        if not found:  # the batch rules report only ids they saw; masked to be safe
            lines.append(f"<load>: {issue.rule}: {mask(issue.message, rid)}".translate(LINE_BREAKS))
            continue
        index = 0
        if issue.rule == "R4" and issue.message.startswith(DUPLICATE):
            repeats[rid] += 1  # the n-th "duplicate id" issue is about the (n + 1)-th record
            index = min(repeats[rid], len(found) - 1)
        lines.append(line_for(found[index], issue))
    return counts, lines
