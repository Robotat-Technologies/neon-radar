"""The licence gate: `access.opensanctions` in docs/build/project.yaml (PHASE-1.md 1.2, G7).

`none` (the default) fetches nothing. `evaluation` needs OpenSanctions' written confirmation
filed in docs/data/licences/opensanctions.md with the data steward's `confirmed:` line; it
streams a slice and writes nothing. `exempt` also writes nothing. `licensed` may write records,
to the spike cache only. A missing file, a missing key or an unknown value counts as `none`,
in project.yaml and from Python alike: the gate fails closed.
"""

import logging
import re
from enum import StrEnum
from pathlib import Path

import yaml

from neonradar_ingest.spikes import PROJECT_FILE, REPO_ROOT

logger = logging.getLogger(__name__)

LICENCE_FILE = REPO_ROOT / "docs" / "data" / "licences" / "opensanctions.md"
REFUSAL = "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md"
# The human step for `evaluation`: the data steward files OpenSanctions' written answer in
# LICENCE_FILE and adds a line such as `confirmed: 2026-11-02 @robotat-com`.
CONFIRMED = re.compile(r"^confirmed: \d{4}-\d{2}-\d{2} \S+", re.MULTILINE)


class Access(StrEnum):
    """The four routes of PHASE-1.md 1.2."""

    NONE = "none"
    EVALUATION = "evaluation"
    LICENSED = "licensed"
    EXEMPT = "exempt"


class LicenceRequired(PermissionError):
    """The access setting does not allow fetching OpenSanctions data."""


def read_access(project_file: Path | None = None) -> Access:
    """Return `access.opensanctions`; a missing file, key or unknown value counts as none."""
    path = project_file or PROJECT_FILE
    try:
        with path.open(encoding="utf-8") as handle:
            project = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("cannot read %s (%s); OpenSanctions access counts as none", path, exc)
        return Access.NONE
    access = project.get("access") if isinstance(project, dict) else None
    value = access.get("opensanctions") if isinstance(access, dict) else None
    if isinstance(value, str) and value in set(Access):
        return Access(value)
    logger.warning(
        "access.opensanctions in %s is %r, not none, evaluation, licensed or exempt;"
        " it counts as none",
        path,
        value,
    )
    return Access.NONE


def _route(access: object) -> Access | None:
    """`access` as an Access, or None for anything else (None, "NONE", 0, a list, ...)."""
    if isinstance(access, Access):
        return access
    if isinstance(access, str) and access in set(Access):
        return Access(access)
    return None


def confirmed(licence_file: Path | None = None) -> bool:
    """True if the licence file has the data steward's `confirmed: <YYYY-MM-DD> <who>` line."""
    try:
        text = (licence_file or LICENCE_FILE).read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return False
    return CONFIRMED.search(text) is not None


def require_access(access: object, licence_file: Path | None = None) -> Access:
    """Return the route if it allows fetching OpenSanctions data; raise LicenceRequired if not.

    Fails closed: anything that is not one of the four routes refuses like `none`.
    `evaluation` counts only while docs/data/licences/opensanctions.md holds the data steward's
    `confirmed: <YYYY-MM-DD> <who>` line for OpenSanctions' written answer (M1.8d step 1).
    """
    route = _route(access)
    if route is None or route is Access.NONE:
        raise LicenceRequired(REFUSAL)
    if route is Access.EVALUATION and not confirmed(licence_file):
        raise LicenceRequired(
            f"{REFUSAL} (access.opensanctions is evaluation, but"
            f" {licence_file or LICENCE_FILE} has no 'confirmed: <YYYY-MM-DD> <who>' line"
            " recording OpenSanctions' written answer)"
        )
    return route


def may_write(access: object) -> bool:
    """Only `licensed` access writes records, and only to the spike cache (M1.8d step 4)."""
    return _route(access) is Access.LICENSED
