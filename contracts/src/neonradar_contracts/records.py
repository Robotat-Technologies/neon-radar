"""C1 NeonRadar Record v1.0.0: the `nr` extension, the validator and the manifest (5.1).

`validate_record` checks one record; `validate_batch` checks the rules that need the whole
load (R4 references and duplicate ids, R8 account holders). Issue codes are R1 to R10, plus
FORMAT for the record envelope and NR for the `nr` object. Each problem is reported once: a
check whose input already failed another rule is skipped. See contracts/C1-record.md.
"""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import cache
from importlib.metadata import version
from itertools import chain
from pathlib import Path
from typing import Any, Literal, Self, TypeGuard

from followthemoney import Schema, model, registry
from followthemoney.exc import InvalidData
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, ValidationError, model_validator

from neonradar_contracts import versions
from neonradar_contracts.datasets import Dataset, load_registry

ALLOWED_SCHEMATA = frozenset(
    {
        "Person", "Company", "Organization", "LegalEntity", "PublicBody", "Address",
        "BankAccount", "Position", "Ownership", "Control", "Directorship", "Representation",
        "Family", "Associate", "Membership", "Employment", "UnknownLink", "Succession",
        "Occupancy", "Payment", "Sanction",
    }
)  # fmt: skip
SYNTHETIC_DATASET = "nr_synthetic"
SYNTHETIC_PREFIX = "syn"
# R1. `rest` is narrowed to FollowTheMoney's entity reference format (letters, digits, dots and
# hyphens, ending in a letter or digit), so every valid id can be referenced (CHANGELOG 1.0.0).
# Python `re` patterns end with \Z (in `re`, `$` also matches before a final newline); pydantic
# field patterns end with `$`, which pydantic's engine matches only at the very end.
ID_RE = re.compile(r"^(?P<prefix>[a-z][a-z0-9]{1,15})-(?P<rest>[A-Za-z0-9.-]{0,99}[A-Za-z0-9])\Z")
ID_KIND_RE = re.compile(r"^[a-z0-9]{1,20}\Z")
PAYMENT_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
AMOUNT_RE = re.compile(r"^[0-9]+(\.[0-9]{1,2})?\Z")
CURRENCY_RE = re.compile(r"^[A-Z]{3}\Z")
SYNTHETIC_ACCOUNT_RE = re.compile(r"^NRSYN[0-9]{10}\Z")
# A pydantic field pattern: `$` matches only at the very end there, so a trailing newline fails,
# and unlike `\z` it is valid ECMA-262 in the exported JSON Schema. Python's `re` (used by the
# jsonschema package) lets `$` match before a final newline, so fixed-length fields also carry
# their length, which rejects it there.
UTC_TIMESTAMP = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
UTC_TIMESTAMP_LENGTH = 20
# Topics that set the C2 flag labels :Sanctioned, :PEP and :RCA; the only ones synthetic
# records may carry (R9), so that no other topic can hint at a scenario.
SYNTHETIC_TOPICS = frozenset({"sanction", "role.pep", "role.rca"})
# R6, guardrail G1: what C2 would say about a real record named by a synthetic one of these
# schemata, so they reference only synthetic records (Sanction: M1.7c follow-up; the others:
# orchestrator decision under OD-10, listed for Gate 1). Ownership, Representation, Membership
# and the other links may name real records: that is synthetic background activity.
SYNTHETIC_ONLY_LINKS = {
    "Sanction": "SUBJECT_OF would mark a real entity as sanctioned",
    "Family": "FAMILY_OF would make a real person a relative of someone",
    "Associate": "ASSOCIATE_OF would make a real person a close associate of someone",
    "Occupancy": "HOLDS_POSITION would give a real person a post",
}
LABEL_KEY_RE = re.compile(r"typolog|scenario|illicit|lookalike|ground.?truth|label", re.IGNORECASE)
ENVELOPE_KEYS = ("id", "schema", "properties", "datasets")
OPTIONAL_KEYS = ("referents", "caption", "first_seen", "last_seen", "last_change", "nr")
PAYMENT_PROPS = (
    "payer", "beneficiary", "payerAccount", "beneficiaryAccount", "amount", "currency", "date",
)  # fmt: skip
NR_USED_ON: dict[str, tuple[str, ...]] = {
    "channel": ("Payment",),
    "account_kind": ("BankAccount",),
    "address_roles": ("LegalEntity",),
    "natures_of_control": ("Ownership", "Control"),
    "share_pct_min": ("Ownership",),
    "share_pct_max": ("Ownership",),
    "is_nominee": ("Directorship",),
    "consolidation": ("Ownership",),
}
# R4 in strict mode: a reference points to a record of its property's FtM range, except that
# an Ownership asset may also be any LegalEntity (C2 builds OWNS between legal entities).
REFERENCE_RANGES: dict[tuple[str, str], tuple[str, ...]] = {
    ("Ownership", "asset"): ("Asset", "LegalEntity"),
}
ID_ALPHABET_HINT = (
    "record ids use letters, digits, dots and hyphens and end in a letter or digit;"
    " map source ids with neonradar_contracts.records.make_id"
)

AddressRole = Literal["registered", "service", "residential", "business", "unknown"]


class NrExtension(BaseModel):
    """The closed `nr` extension object (5.1). Unknown keys fail validation.

    `v` is the record contract's major.minor. It is "1.0" for every 1.0.x release; a minor
    release (for example 1.1.0, a new optional key) adds "1.1" here and keeps accepting "1.0".
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    v: Literal["1.0"]
    synthetic: bool | None = None
    synthetic_kind: Literal["registry", "activity"] | None = None
    channel: Literal["wire", "card", "cash_deposit", "cash_withdrawal", "internal"] | None = None
    account_kind: Literal["customer", "cash_ledger"] | None = None
    address_roles: dict[str, AddressRole] | None = None
    source_ref: str | None = None
    natures_of_control: list[str] | None = None
    share_pct_min: float | None = Field(default=None, ge=0, le=100)
    share_pct_max: float | None = Field(default=None, ge=0, le=100)
    is_nominee: bool | None = None
    consolidation: Literal["direct", "ultimate"] | None = None


@dataclass(frozen=True, slots=True)
class RecordIssue:
    """One broken rule. `rule` is R1 to R10, FORMAT or NR."""

    rule: str
    record_id: str | None
    message: str

    def __str__(self) -> str:
        return f"{self.rule} {self.record_id or '<no id>'}: {self.message}"


class RecordFileError(ValueError):
    """A line of a `.ftm.jsonl` file is not one JSON object; the message names path and line."""


def make_id(prefix: str, kind: str, native: str) -> str:
    """The one rule for turning a source identifier into a record id (C1-record.md).

    Returns `<prefix>-<kind>-<native>` with each `_` in `native` replaced by `.`. If that still
    breaks R1 (another character outside `[A-Za-z0-9.-]`, a last character that is not a letter
    or digit, or too long), returns `<prefix>-<kind>-<first 20 hex of SHA-1(native)>` instead.
    Deterministic; loaders keep the native identifier in `nr.source_ref`.
    """
    if not ID_RE.fullmatch(f"{prefix}-x") or not ID_KIND_RE.fullmatch(kind) or not native:
        raise ValueError(f"make_id needs a dataset prefix, a short kind and a native id: {kind!r}")
    candidate = f"{prefix}-{kind}-{native.replace('_', '.')}"
    if ID_RE.fullmatch(candidate):
        return candidate
    digest = hashlib.sha1(native.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
    return f"{prefix}-{kind}-{digest}"


def iter_records(path: Path | str) -> Iterator[dict[str, Any]]:
    """Stream the records of a `.ftm.jsonl` file. Blank lines are skipped."""
    path = Path(path)
    with path.open("rb") as handle:
        for number, raw in enumerate(handle, start=1):
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise RecordFileError(f"{path}:{number}: not UTF-8 ({exc.reason})") from exc
            if not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RecordFileError(f"{path}:{number}: invalid JSON ({exc.msg})") from exc
            if not isinstance(data, dict):
                raise RecordFileError(f"{path}:{number}: each line must be one JSON object")
            yield data


def _is_str_list(value: Any) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


@cache
def _iso_currencies() -> frozenset[str]:
    from babel.numbers import list_currencies  # loaded on first use: CLDR data is large

    return frozenset(list_currencies())


def _label_issue(where: str, key: str) -> str:
    return f"{where} {key!r} looks like a ground-truth label; labels go to separate label files"


Add = Callable[[str, str], None]


def _check_envelope(data: dict[str, Any], add: Add) -> None:
    for key in sorted(set(data) - set(ENVELOPE_KEYS) - set(OPTIONAL_KEYS)):
        if LABEL_KEY_RE.search(key):
            add("R9", _label_issue("top-level key", key))
        else:
            allowed = ", ".join(ENVELOPE_KEYS + OPTIONAL_KEYS)
            add("FORMAT", f"unknown top-level key {key!r} (allowed: {allowed})")
    if "caption" in data and not isinstance(data["caption"], str):
        add("FORMAT", "caption must be a string")
    if "referents" in data and not _is_str_list(data["referents"]):
        add("FORMAT", "referents must be a list of strings")
    for key in ("first_seen", "last_seen", "last_change"):
        value = data.get(key)
        if value is not None and not (isinstance(value, str) and registry.date.validate(value)):
            add("R5", f"{key} {value!r} is not an ISO 8601 date")


def _check_dataset(data: dict[str, Any], add: Add) -> Dataset | None:
    datasets = data.get("datasets")
    if not _is_str_list(datasets) or len(datasets) != 1:
        add(
            "R2",
            "datasets must list exactly one slug from contracts/datasets.yaml"
            f" ({'missing' if datasets is None else f'got {datasets!r}'});"
            " create records with ValueEntity(model[schema], {'id': ..., 'datasets': [slug]}),"
            " not model.make_entity, whose output has no datasets",
        )
        return None
    dataset = load_registry().get(datasets[0])
    if dataset is None:
        add("R2", f"dataset {datasets[0]!r} is not in contracts/datasets.yaml")
    return dataset


def _check_id(rid: str | None, dataset: Dataset | None, add: Add) -> re.Match[str] | None:
    """R1. Returns the match only when the prefix fits the dataset (or the dataset is unknown)."""
    match = ID_RE.fullmatch(rid) if rid is not None else None
    if match is None:
        add(
            "R1",
            f"id {rid!r} is not <prefix>-<rest>: a lower-case prefix of 2 to 16 letters or digits,"
            " a hyphen, then up to 100 letters, digits, dots or hyphens ending in a letter or"
            " digit (for example syn-co-0001)",
        )
        return None
    if dataset is not None and match["prefix"] != dataset.id_prefix:
        add(
            "R1",
            f"id prefix {match['prefix']!r} does not match dataset {dataset.slug},"
            f" whose id_prefix is {dataset.id_prefix!r}",
        )
        return None
    return match


def _check_properties(schema: Schema, props: dict[str, list[str]], add: Add) -> None:
    known = {}
    for name in sorted(props):
        if name in schema.properties:
            known[name] = props[name]
        elif LABEL_KEY_RE.search(name):
            add("R9", _label_issue("property", name))
        else:
            add("R3", f"{schema.name} has no property {name!r} (FollowTheMoney would drop it)")
    flagged: set[str] = set()
    try:
        schema.validate({"properties": known})
    except InvalidData as exc:
        for name, error in sorted(exc.errors.get("properties", {}).items()):
            flagged.add(name)
            kind = schema.properties[name].type
            if kind == registry.date:
                add("R5", f"{name}: {error}; dates are ISO 8601 and may be partial (1979-08)")
            elif kind == registry.entity:
                add("R4", f"{name}: {error}; {ID_ALPHABET_HINT}")
            else:
                add("R3", f"{name}: {error} (FollowTheMoney {schema.name} validation)")
    for name in schema.required:
        if name not in flagged and not props.get(name):
            add("R3", f"{schema.name} needs a non-empty {name!r} (required by FollowTheMoney)")
    for name, values in known.items():
        if name not in flagged and schema.properties[name].type == registry.entity:
            for value in values:
                if not ID_RE.fullmatch(value):
                    add("R4", f"{name} value {value!r} is not a record id; {ID_ALPHABET_HINT}")


def _check_nr(raw: Any, schema: Schema | None, props: dict[str, Any], add: Add) -> None:
    if raw is None:
        return
    if not isinstance(raw, dict):
        add("NR", "nr must be an object")
        return
    try:
        nr = NrExtension.model_validate(raw)
    except ValidationError as exc:
        for error in exc.errors():
            path = ".".join(str(part) for part in error["loc"])
            if error["type"] == "extra_forbidden" and LABEL_KEY_RE.search(path):
                add("R9", _label_issue("nr key", path))
            else:
                add("NR", f"nr.{path}: {error['msg']}")
        return
    if schema is not None:  # placement needs a valid schema and properties (R3)
        for key, used_on in NR_USED_ON.items():
            if getattr(nr, key) is not None and not any(schema.is_a(s) for s in used_on):
                add("NR", f"nr.{key} is only used on {' or '.join(used_on)}, not on {schema.name}")
        addresses = set(props.get("addressEntity") or [])
        for address in sorted(set(nr.address_roles or {}) - addresses):
            add("NR", f"nr.address_roles names {address!r}, which is not in addressEntity")
    low, high = nr.share_pct_min, nr.share_pct_max
    if low is not None and high is not None and low > high:
        add("NR", "nr.share_pct_min is greater than nr.share_pct_max")


def _check_synthetic(
    data: dict[str, Any], dataset: Dataset | None, match: re.Match[str] | None, add: Add
) -> bool:
    raw = data.get("nr")
    flags = raw if isinstance(raw, dict) else {}
    flag = flags.get("synthetic")
    legs: dict[str, bool] = {}
    # Legs that already failed R1, R2 or NR are left out, so each problem is reported once.
    if raw is None or (isinstance(raw, dict) and (flag is None or isinstance(flag, bool))):
        legs["nr.synthetic"] = flag is True
    if dataset is not None:
        legs["dataset"] = dataset.slug == SYNTHETIC_DATASET
    if match is not None:
        legs["prefix"] = match["prefix"] == SYNTHETIC_PREFIX
    synthetic = any(legs.values())
    if synthetic and raw is None:
        add("R6", "synthetic records (dataset nr_synthetic, prefix syn) must carry nr")
    elif synthetic and not all(legs.values()):
        found = ", ".join(f"{leg} {'yes' if value else 'no'}" for leg, value in legs.items())
        add(
            "R6",
            "dataset nr_synthetic, id prefix syn and nr.synthetic: true go together;"
            f" synthetic here: {found}",
        )
    elif not synthetic and "synthetic" in flags:
        add("R6", "only synthetic records may set nr.synthetic; leave it out")
    if not synthetic and "synthetic_kind" in flags:  # a placement rule, like NR_USED_ON
        add("NR", "nr.synthetic_kind is only used on synthetic records")
    return synthetic


def _check_payment(props: dict[str, list[str]], raw_nr: Any, synthetic: bool, add: Add) -> None:
    if not synthetic:
        add("R7", "Payment records are synthetic only in C1 v1 (dataset nr_synthetic)")
    for name in PAYMENT_PROPS:
        count = len(props.get(name, []))
        if count != 1:
            add("R7", f"Payment needs exactly one {name} value (has {count})")
    for value in props.get("amount", []):
        if not AMOUNT_RE.fullmatch(value) or Decimal(value) <= 0:
            add(
                "R7",
                f"amount {value!r} must be a decimal number greater than zero with at most two"
                " decimals, for example 9500.00",
            )
    for value in props.get("currency", []):
        if not CURRENCY_RE.fullmatch(value):
            add("R7", f"currency {value!r} must be a three-letter upper-case ISO 4217 code (EUR)")
        elif value not in _iso_currencies():
            add("R7", f"currency {value!r} is not an ISO 4217 code")
    if not isinstance(raw_nr, dict) or raw_nr.get("channel") is None:  # a bad value is NR
        add("R7", "Payment needs nr.channel (wire, card, cash_deposit, cash_withdrawal, internal)")
    for value in props.get("date", []):  # dates FtM rejects are already R5
        if registry.date.validate(value) and not PAYMENT_DATE_RE.fullmatch(value):
            add(
                "R5",
                f"Payment date {value!r} must be a full UTC timestamp YYYY-MM-DDTHH:MM:SS without"
                " an offset or Z, for example 2026-03-14T10:22:05",
            )


def validate_record(data: dict[str, Any]) -> list[RecordIssue]:
    """Check one record against R1 to R10. R4 and R8 also have batch parts (`validate_batch`)."""
    rid = data["id"] if isinstance(data.get("id"), str) else None
    issues: list[RecordIssue] = []

    def add(rule: str, message: str) -> None:
        issues.append(RecordIssue(rule, rid, message))

    _check_envelope(data, add)
    dataset = _check_dataset(data, add)
    match = _check_id(rid, dataset, add)

    name = data.get("schema")
    schema = model.get(name) if isinstance(name, str) and name in ALLOWED_SCHEMATA else None
    raw_props = data.get("properties")
    props: dict[str, list[str]] = {}
    if schema is None:
        allowed = ", ".join(sorted(ALLOWED_SCHEMATA))
        add("R3", f"schema {name!r} is not a C1 v1 schema (allowed: {allowed})")
    elif not isinstance(raw_props, dict) or not all(_is_str_list(v) for v in raw_props.values()):
        add("R3", "properties must be an object mapping property names to lists of strings")
        schema = None
    else:
        props = raw_props
        _check_properties(schema, props, add)

    _check_nr(data.get("nr"), schema, props, add)
    synthetic = _check_synthetic(data, dataset, match, add)
    if schema is not None and schema.is_a("Payment"):
        _check_payment(props, data.get("nr"), synthetic, add)
    reason = SYNTHETIC_ONLY_LINKS.get(schema.name) if synthetic and schema is not None else None
    if schema is not None and reason is not None:
        # The prefix decides (R1, R6), so this needs no other record and holds in strict and
        # non-strict mode. Malformed references are R4's.
        for reference in schema.properties.values():
            if reference.type != registry.entity:
                continue
            for value in props.get(reference.name, []):
                ref = ID_RE.fullmatch(value)
                if ref and ref["prefix"] != SYNTHETIC_PREFIX:
                    add(
                        "R6",
                        f"a synthetic {schema.name} references only synthetic records (prefix"
                        f" syn) in {reference.name}, not {value!r}: {reason} (G1)",
                    )
    if synthetic:  # R9: only the topics that set C2 flags; others could carry labels
        for topic in props.get("topics", []):
            if topic not in SYNTHETIC_TOPICS:
                add(
                    "R9",
                    f"topic {topic!r} on a synthetic record could carry a ground-truth label;"
                    f" synthetic records use only {', '.join(sorted(SYNTHETIC_TOPICS))}",
                )
    if synthetic:  # R8: no synthetic account can collide with a real one
        for prop in ("iban", "bic"):
            if props.get(prop):
                add("R8", f"synthetic records never set {prop}")
        if schema is not None and schema.is_a("BankAccount"):
            for value in props.get("accountNumber", []):
                if not SYNTHETIC_ACCOUNT_RE.fullmatch(value):
                    add("R8", f"synthetic accountNumber {value!r} must be NRSYN plus 10 digits")
    for text in _strings(data):
        if not unicodedata.is_normalized("NFC", text):
            add(
                "R10",
                f"{text!a} is not Unicode NFC; write unicodedata.normalize('NFC', value)",
            )
            break
    return issues


def validate_batch(records: Iterable[dict[str, Any]], strict: bool) -> list[RecordIssue]:
    """Rules that need the whole load.

    R4: duplicate ids (always); in strict mode also dangling references and references to a
    record of the wrong schema. R8: every BankAccount has a LegalEntity holder (always).
    """
    issues: list[RecordIssue] = []
    schemata: dict[str, Schema] = {}
    references: list[tuple[str, Schema, str, str]] = []
    holdings: list[tuple[str, str]] = []
    accounts: set[str] = set()  # R8 counts every record, duplicates included
    legal_entities: set[str] = set()
    for data in records:
        rid, name, props = data.get("id"), data.get("schema"), data.get("properties")
        schema = model.get(name) if isinstance(name, str) else None
        if not isinstance(rid, str) or schema is None or not isinstance(props, dict):
            continue  # validate_record reports these
        if schema.is_a("BankAccount"):
            accounts.add(rid)
        if schema.is_a("LegalEntity"):
            legal_entities.add(rid)
        owners, assets = props.get("owner"), props.get("asset")
        if schema.is_a("Ownership") and _is_str_list(owners) and _is_str_list(assets):
            holdings.extend((owner, asset) for owner in owners for asset in assets)
        if rid in schemata:  # the first record with this id stays
            issues.append(
                RecordIssue("R4", rid, "duplicate id: another record in this load has it")
            )
            continue
        schemata[rid] = schema
        for prop_name, values in props.items():
            prop = schema.properties.get(prop_name)
            if prop is not None and prop.type == registry.entity and _is_str_list(values):
                # Malformed references are reported by validate_record.
                references.extend(
                    (rid, schema, prop_name, value) for value in values if ID_RE.fullmatch(value)
                )
    if strict:
        for rid, schema, prop_name, value in references:
            target = schemata.get(value)
            if target is None:
                message = (
                    f"{prop_name} points to {value!r}, which is not in this load; add that record"
                    " or validate its file together with this one"
                )
                issues.append(RecordIssue("R4", rid, message))
                continue
            prop_range = schema.properties[prop_name].range
            allowed = REFERENCE_RANGES.get((schema.name, prop_name)) or (
                (prop_range.name,) if prop_range is not None else ()
            )
            if allowed and not any(target.is_a(s) for s in allowed):
                message = (
                    f"{prop_name} points to {value!r}, a {target.name};"
                    f" it must point to a {' or '.join(allowed)}"
                )
                issues.append(RecordIssue("R4", rid, message))
    held = {asset for owner, asset in holdings if owner in legal_entities}
    for rid in sorted(accounts - held):
        message = (
            f"BankAccount has no holder in this load: add an Ownership with asset {rid} and"
            " a Person, Company or other LegalEntity as owner"
        )
        issues.append(RecordIssue("R8", rid, message))
    return issues


def validate_files(
    paths: Sequence[Path | str], strict: bool
) -> tuple[Counter[str], list[RecordIssue]]:
    """Validate files as one load: each record, then the batch rules. Streams the files twice.

    Returns the record counts by schema and every issue; raises RecordFileError on a bad line.
    """
    counts: Counter[str] = Counter()
    issues: list[RecordIssue] = []
    for path in paths:
        for data in iter_records(path):
            counts[str(data.get("schema"))] += 1
            issues.extend(validate_record(data))
    issues.extend(validate_batch(chain.from_iterable(iter_records(p) for p in paths), strict))
    return counts, issues


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ManifestFile(_Strict):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)
    records: NonNegativeInt


class Producer(_Strict):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    git_sha: str | None = None


class Source(_Strict):
    urls: list[str] = Field(default_factory=list)
    retrieved_at: str | None = Field(
        default=None,
        pattern=UTC_TIMESTAMP,
        min_length=UTC_TIMESTAMP_LENGTH,
        max_length=UTC_TIMESTAMP_LENGTH,
    )
    source_version: str | None = None


class ManifestLicence(_Strict):
    id: str = Field(min_length=1)
    attribution: str | None


class Counts(_Strict):
    by_schema: dict[str, NonNegativeInt]
    skipped: dict[str, NonNegativeInt]


class Manifest(_Strict):
    """The `*.manifest.json` that sits next to every `.ftm.jsonl` file (5.1).

    `dataset`, `licence.id` and `synthetic` must agree with contracts/datasets.yaml.
    """

    manifest_version: Literal["1.0"]
    record_contract: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    dataset: str = Field(min_length=1)
    files: list[ManifestFile] = Field(min_length=1)
    created_at: str = Field(
        pattern=UTC_TIMESTAMP, min_length=UTC_TIMESTAMP_LENGTH, max_length=UTC_TIMESTAMP_LENGTH
    )
    producer: Producer
    source: Source
    licence: ManifestLicence
    counts: Counts
    dependencies: dict[str, str]
    synthetic: bool
    seed: int | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _agrees_with_registry(self) -> Self:
        entry = load_registry().get(self.dataset)
        if entry is None:
            raise ValueError(f"dataset {self.dataset!r} is not in contracts/datasets.yaml")
        if self.licence.id != entry.licence.id:
            raise ValueError(f"licence.id must be {entry.licence.id!r} for {self.dataset}")
        if self.synthetic != entry.synthetic:
            raise ValueError(f"synthetic must be {str(entry.synthetic).lower()} for {self.dataset}")
        return self


def manifest_path(record_file: Path) -> Path:
    """`<stem>.ftm.jsonl` -> `<stem>.manifest.json` in the same folder."""
    if not record_file.name.endswith(".ftm.jsonl"):
        raise ValueError(f"{record_file} is not a .ftm.jsonl file")
    return record_file.with_name(record_file.name.removesuffix(".ftm.jsonl") + ".manifest.json")


def write_manifest(
    record_file: Path,
    *,
    dataset: str,
    producer: Producer,
    source: Source | None = None,
    skipped: Mapping[str, int] | None = None,
    seed: int | None = None,
    notes: Sequence[str] = (),
    created_at: str | None = None,
) -> Path:
    """Write the sibling manifest of `record_file` (SHA-256, counts, licence); return its path."""
    entry = load_registry().get(dataset)
    if entry is None:
        raise ValueError(f"dataset {dataset!r} is not in contracts/datasets.yaml")
    by_schema = Counter(str(data.get("schema")) for data in iter_records(record_file))
    manifest = Manifest(
        manifest_version="1.0",
        record_contract=versions.RECORD,
        dataset=dataset,
        files=[
            ManifestFile(
                path=record_file.name,
                sha256=hashlib.sha256(record_file.read_bytes()).hexdigest(),
                records=by_schema.total(),
            )
        ],
        created_at=created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        producer=producer,
        source=source or Source(),
        licence=ManifestLicence(id=entry.licence.id, attribution=entry.attribution),
        counts=Counts(by_schema=dict(sorted(by_schema.items())), skipped=dict(skipped or {})),
        dependencies={"followthemoney": version("followthemoney")},
        synthetic=entry.synthetic,
        seed=seed,
        notes=list(notes),
    )
    path = manifest_path(record_file)
    text = json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
    return path
