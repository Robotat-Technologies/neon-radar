"""The licence gate: `access.opensanctions` in docs/build/project.yaml (PHASE-1.md 1.2, G7).

`none` (the default) fetches nothing. `evaluation` needs OpenSanctions' written confirmation
filed in docs/data/licences/opensanctions.md; it streams a slice and writes nothing. `exempt`
also writes nothing. `licensed` may write records, to the spike cache only. A missing file, a
missing key or an unknown value counts as `none`: the gate fails closed.
"""

import logging
from enum import StrEnum
from pathlib import Path

import yaml

from neonradar_ingest.spikes import PROJECT_FILE, REPO_ROOT

logger = logging.getLogger(__name__)

LICENCE_FILE = REPO_ROOT / "docs" / "data" / "licences" / "opensanctions.md"
REFUSAL = "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md"


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


def require_access(access: Access, licence_file: Path | None = None) -> None:
    """Raise LicenceRequired unless `access` allows fetching OpenSanctions data.

    `evaluation` counts only while OpenSanctions' written confirmation is on file
    (PHASE-1.md M1.8d step 1).
    """
    if access is Access.NONE:
        raise LicenceRequired(REFUSAL)
    path = licence_file or LICENCE_FILE
    if access is Access.EVALUATION and not path.is_file():
        raise LicenceRequired(
            f"{REFUSAL} (access.opensanctions is evaluation, but OpenSanctions' written"
            f" confirmation is not filed in {path})"
        )


def may_write(access: Access) -> bool:
    """Only `licensed` access writes records, and only to the spike cache (M1.8d step 4)."""
    return access is Access.LICENSED
