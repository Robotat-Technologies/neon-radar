"""Counts-only summaries (PHASE-2.md M2.2 deliverable 9, 4.5, G9).

`emit` prints a summary and writes it to `reports_dir(profile)/<command>-<UTC timestamp>.json`,
the one place under data/cache/ the agent reads for a real profile. It refuses (SummaryRefused)
any value that is not a number, a boolean, null, a short string under an allowed key, a list of
short strings under `headers` or a registered list key, or a dict of these. Keys are lower-case
names; under a key ending in `_by_value` they may be enumeration values instead, and every one
counted fewer than 10 times is folded into `<key>_rare`, so a value seen once never appears.
"""

import json
import math
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

import typer

from neonradar_ingest.data import layout
from neonradar_ingest.data.profiles import Profile

SHORT = re.compile(r"^[A-Za-z0-9 ._:/+()#,'&-]*\Z")
SHORT_MAX = 80
KEY = re.compile(r"^[a-z0-9][a-z0-9_.:-]{0,79}\Z")
VALUE_KEY = re.compile(r"^[a-z0-9][a-z0-9 ._#:/()&,'-]{0,79}\Z")
BY_VALUE = "_by_value"
RARE = 10
STRING_KEYS = frozenset(
    {
        "version", "versions", "product", "run_id", "dataset", "datasets", "profile", "step",
        "steps", "file", "files", "status", "rule", "project_file", "project_sha256",
        "resolver_version", "config_sha256", "started_at", "finished_at",
    }
)  # fmt: skip
LIST_KEYS = frozenset({"headers"})


class SummaryRefused(ValueError):
    """A summary value that could hold record data; the message names the key, not the value."""

    exit_code = 1
    counts_only = True


def _short(value: object) -> bool:
    return isinstance(value, str) and len(value) <= SHORT_MAX and bool(SHORT.match(value))


def _check(value: Any, key: str, path: str, strings: frozenset[str], lists: frozenset[str]) -> Any:
    """`value` cleaned (rare `_by_value` keys folded), or SummaryRefused."""
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SummaryRefused(f"{path}: not a finite number")
        return value
    if isinstance(value, str):
        if key not in strings and not key.startswith("threshold"):
            raise SummaryRefused(f"{path}: a string under a key that is not allowed")
        if not _short(value):
            raise SummaryRefused(f"{path}: not a short string (80 characters of {SHORT.pattern})")
        return value
    if isinstance(value, list | tuple):
        if key not in lists:
            raise SummaryRefused(f"{path}: a list under a key that is not registered")
        if not all(_short(item) for item in value):
            raise SummaryRefused(f"{path}: a list item that is not a short string")
        return list(value)
    if isinstance(value, Mapping):
        return _mapping(value, key, path, strings, lists)
    raise SummaryRefused(f"{path}: a {type(value).__name__} is not allowed")


def _mapping(
    value: Mapping[Any, Any], key: str, path: str, strings: frozenset[str], lists: frozenset[str]
) -> dict[str, Any]:
    vocabulary = key.endswith(BY_VALUE)
    cleaned: dict[str, Any] = {}
    for name, item in value.items():
        if not isinstance(name, str) or not (VALUE_KEY if vocabulary else KEY).match(name):
            raise SummaryRefused(f"{path}: a key that is not a lower-case name")
        if vocabulary and (isinstance(item, bool) or not isinstance(item, int)):
            raise SummaryRefused(f"{path}.<value>: a {BY_VALUE} entry must be a whole count")
        where = f"{path}.<value>" if vocabulary else f"{path}.{name}"
        cleaned[name] = _check(item, name, where, strings, lists)
    out: dict[str, Any] = {}
    for name, item in cleaned.items():
        if isinstance(item, dict) and name.endswith(BY_VALUE):
            common = {k: v for k, v in item.items() if v >= RARE}
            out[name], out[f"{name}_rare"] = common, sum(item.values()) - sum(common.values())
        else:
            out[name] = item
    return out


def clean(
    summary: Mapping[str, Any], *, string_keys: Iterable[str] = (), list_keys: Iterable[str] = ()
) -> dict[str, Any]:
    """The summary as `emit` would write it, or SummaryRefused."""
    strings = STRING_KEYS | frozenset(string_keys)
    lists = LIST_KEYS | frozenset(list_keys)
    return _mapping(summary, "summary", "summary", strings, lists)


def emit(
    profile: Profile | str,
    command: str,
    summary: Mapping[str, Any],
    *,
    string_keys: Iterable[str] = (),
    list_keys: Iterable[str] = (),
) -> dict[str, Any]:
    """Check, print and write the summary of `command` (for example "ingest build")."""
    cleaned = clean(summary, string_keys=string_keys, list_keys=list_keys)
    text = json.dumps(cleaned, indent=2, ensure_ascii=True)
    folder = layout.reports_dir(profile)
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{'-'.join(command.split())}-{datetime.now(UTC):%Y%m%dT%H%M%S}"
    path, number = folder / f"{stem}.json", 1
    while path.exists():
        number += 1
        path = folder / f"{stem}-{number}.json"
    path.write_text(text + "\n", encoding="utf-8")
    typer.echo(text)
    return cleaned
