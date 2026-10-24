"""Error redaction for real-profile commands (PHASE-2.md M2.2 deliverable 10, 7.4 rule 5).

Every command enters `guard(profile, command)` with its profile. On a real profile an exception
prints only its class, the step, the dataset, the rule id (when it carries one) and a run-local
reference such as `err-3`; the full traceback goes to `logs_dir()/<command>-<UTC timestamp>.log`
under `data/cache/real/`, which is purged with the rest. An exception whose `counts_only` is
true (gate refusals, download and summary errors, counts-only checks) also prints its message,
and writes no log. The exit code is the exception's `exit_code` (2 a refusal such as L17, 3 the
gate, 4 a size or comparison cap), else 1. On a synthetic profile nothing is redacted: an
exception with an `exit_code` prints its message, any other propagates with its traceback.
"""

import itertools
import re
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

import typer

from neonradar_ingest.data import layout
from neonradar_ingest.data.gate import machine_approved
from neonradar_ingest.data.profiles import Profile

_REFERENCES = itertools.count(1)
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}")
# Typer's own exits and usage errors (typer.Exit is not a TyperException).
PASS_THROUGH = (typer.Exit, typer.Abort, typer.TyperException, KeyboardInterrupt)


@dataclass(slots=True)
class Where:
    """Where a command is: it sets `step` and `dataset` as it goes; they appear in errors."""

    step: str | None = None
    dataset: str | None = None


def _exit_code(exc: BaseException) -> int:
    code = getattr(exc, "exit_code", 1)
    return code if isinstance(code, int) and not isinstance(code, bool) and code > 0 else 1


def _safe(value: object) -> str:
    """`value` if it is a plain name (the summary key pattern, capitals allowed for variable
    names such as CI or NR_REAL_DATA_MACHINE), else `-`: an attribute could hold a value."""
    return value if isinstance(value, str) and SAFE_NAME.fullmatch(value) else "-"


def _report(exc: Exception, command: str, where: Where) -> None:
    reference = f"err-{next(_REFERENCES)}"
    rule = getattr(exc, "rule", None)
    parts = [
        type(exc).__name__,
        f"step {_safe(getattr(exc, 'step', None) or where.step)}",
        f"dataset {_safe(getattr(exc, 'dataset', None) or where.dataset)}",
        *([f"rule {_safe(rule)}"] if rule else []),
        reference,
    ]
    line = ", ".join(parts)
    if getattr(exc, "counts_only", False) is True:
        typer.echo(f"{line}: {exc}", err=True)
        return
    try:
        if where.step == "gate" and not machine_approved():
            # The gate runs before anything is written, so on a machine that may not hold
            # real data nothing goes under data/cache/real/, not even a traceback.
            typer.echo(f"{line} (no traceback kept on an unapproved machine)", err=True)
            return
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        log = layout.logs_dir() / f"{'-'.join(command.split())}-{stamp}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:  # errors in one second share the file
            handle.write(f"{reference}\n{''.join(traceback.format_exception(exc))}")
    except Exception:  # never let a failed log show the original error or chain it
        typer.echo(f"{line} (traceback not saved)", err=True)
        return
    typer.echo(f"{line} (traceback in {log.parent.name}/{log.name})", err=True)


def report(exc: Exception, command: str, step: str) -> None:
    """Report `exc` as `guard` does when redacting, for errors a server answers itself."""
    _report(exc, command, Where(step=step))


@contextmanager
def guard(profile: Profile | None, command: str, *, real: bool | None = None) -> Iterator[Where]:
    """Redact errors when `profile` is real (or `real` is true, for commands on real folders)."""
    where = Where()
    redacting = real if real is not None else profile is not None and profile.real_data
    try:
        yield where
    except PASS_THROUGH:
        raise
    except Exception as exc:
        if redacting:
            _report(exc, command, where)
        elif hasattr(exc, "exit_code"):
            typer.echo(f"FAIL  {exc}", err=True)
        else:
            raise
        raise typer.Exit(code=_exit_code(exc)) from None
