"""`neonradar doctor`: check that this machine can build and run NeonRadar (PHASE-1.md M1.3).

Phase 2 (PHASE-2.md M2.0) adds disk space, DuckDB, real data and its age, DuckDB spill folders,
the real-data instance and the real-profile settings. Those checks only warn: doctor still exits
1 only on a Phase 1 FAIL. They read file ages and counts, never a file's contents.
"""

import importlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PROJECT = "neonradar"  # `name:` in compose.yaml (M1.4)
GIB = 1024**3
STANDARD_MEMORY = 5 * GIB  # NEO4J_MEM_LIMIT=5g, the "standard" memory profile (M1.4)
SMALL_MEMORY = 2500 * 1024**2  # NEO4J_MEM_LIMIT=2500m, the "small" memory profile
GB = 1000**3
DISK_NEEDED = 25 * GB  # free space uk-sample needs (PHASE-2.md 1.1)
DAY = 86_400
REAL_DIR = Path("data", "cache", "real")
SPILL_DIRS = (REAL_DIR / "duckdb-tmp", Path("data", "cache", "synthetic", "duckdb-tmp"))
PROJECT_FILE = Path("docs", "build", "project.yaml")
MACHINES_DOC = "docs/data/real-data-machines.md"


class Status(StrEnum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class Check:
    name: str
    status: Status
    detail: str

    def line(self) -> str:
        return f"{self.status:<5} {self.name:<14} {self.detail}"


# Neo4j runs only in the Compose stack, so another program on its ports blocks `make up`. The API
# and the UI dev server may also run as plain processes (`make demo-dev`), which doctor cannot tell
# apart from other programs, so a busy port there is only a warning.
PORTS = {
    7474: ("Neo4j Browser", Status.FAIL),
    7687: ("Neo4j Bolt", Status.FAIL),
    8000: ("the API", Status.WARN),
    5173: ("the UI dev server", Status.WARN),
}


def run(*args: str) -> str | None:
    """Run a command; return its stripped stdout, or None if it is missing, fails or hangs."""
    if shutil.which(args[0]) is None:
        return None
    try:
        # Fixed argument lists from this module, never shell strings or user input.
        result = subprocess.run(  # noqa: S603
            args, capture_output=True, text=True, timeout=20, check=False
        )
    except OSError, subprocess.TimeoutExpired:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def check_python() -> Check:
    found = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info[:2] == (3, 14):
        return Check("Python", Status.OK, found)
    return Check("Python", Status.FAIL, f"{found}; NeonRadar needs 3.14 (uv python install 3.14)")


def check_uv() -> Check:
    output = run("uv", "--version")  # "uv 0.13.4 (7456b60bc 2026-10-20 ...)"
    if not output or len(output.split()) < 2:
        return Check("uv", Status.FAIL, "not found; install uv 0.13 (https://docs.astral.sh/uv/)")
    found = output.split()[1]
    if found.startswith("0.13."):
        return Check("uv", Status.OK, found)
    return Check("uv", Status.WARN, f"{found}; the project is tested with uv 0.13.x")


def docker_info() -> dict[str, Any] | None:
    """`docker info` as a dict, or None when Docker is missing or its daemon is not reachable."""
    output = run("docker", "info", "--format", "{{json .}}")
    try:
        info = json.loads(output or "null")
    except json.JSONDecodeError:
        return None
    if not isinstance(info, dict) or not info.get("ServerVersion") or info.get("ServerErrors"):
        return None
    return info


def check_docker(info: dict[str, Any] | None) -> Check:
    if shutil.which("docker") is None:
        return Check("Docker", Status.FAIL, "not found; install Docker Desktop or Docker Engine")
    if info is None:
        return Check("Docker", Status.FAIL, "daemon not reachable; start Docker")
    return Check("Docker", Status.OK, f"server {info['ServerVersion']}")


def check_compose() -> Check:
    found = run("docker", "compose", "version", "--short") or ""  # "5.4.0" or "v2.29.1"
    major = found.lstrip("v").split(".")[0]
    if not major.isdigit():
        return Check(
            "Compose", Status.FAIL, "docker compose not found; install Compose v2 or later"
        )
    if int(major) < 2:
        return Check("Compose", Status.FAIL, f"{found}; NeonRadar needs Compose v2 or later")
    return Check("Compose", Status.OK, found)


def check_env_file(root: Path) -> Check:
    if (root / ".env").is_file():
        return Check(".env", Status.OK, "present")
    return Check(".env", Status.WARN, "missing; the Neo4j stack reads it (copy .env.example)")


def port_in_use(port: int) -> bool:
    """True if a program accepts connections on this port on 127.0.0.1 or ::1."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                if sock.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue  # for example no IPv6 on this machine
    return False


def stack_ports() -> set[int]:
    """Host ports published by containers of the NeonRadar Compose project."""
    label = f"label=com.docker.compose.project={COMPOSE_PROJECT}"
    output = run("docker", "ps", "--filter", label, "--format", "{{.Ports}}") or ""
    return {int(port) for port in re.findall(r":(\d+)->", output)}


def check_port(port: int, stack: set[int]) -> Check:
    purpose, severity = PORTS[port]
    if port in stack:
        return Check(f"port {port}", Status.OK, "used by the NeonRadar stack")
    if not port_in_use(port):
        return Check(f"port {port}", Status.OK, "free")
    return Check(f"port {port}", severity, f"in use by another program; {purpose} needs it")


def check_memory(info: dict[str, Any] | None) -> Check:
    if info is None:
        return Check("Docker memory", Status.WARN, "not checked; Docker is not reachable")
    if not isinstance(info.get("MemTotal"), int):
        return Check("Docker memory", Status.WARN, "unknown; docker info reports no MemTotal")
    total = info["MemTotal"]
    found = f"{total / GIB:.1f} GiB"
    if total >= STANDARD_MEMORY:
        return Check("Docker memory", Status.OK, f"{found}; standard memory profile")
    if total >= SMALL_MEMORY:
        return Check("Docker memory", Status.WARN, f"{found}; use the small profile in .env")
    return Check("Docker memory", Status.FAIL, f"{found}; Neo4j needs at least 2.5 GiB")


def check_icu() -> Check:
    # A warning, not a failure: PyICU (built from source against ICU) is needed only once
    # followthemoney joins the workspace in M1.7a.
    if shutil.which("pkg-config") is None:
        return Check("ICU", Status.WARN, "pkg-config not found; install pkg-config and ICU")
    if run("pkg-config", "--exists", "icu-uc") is None:
        return Check(
            "ICU",
            Status.WARN,
            "icu-uc not found by pkg-config; install ICU headers or point PKG_CONFIG_PATH at them",
        )
    return Check("ICU", Status.OK, run("pkg-config", "--modversion", "icu-uc") or "found")


def check_disk(root: Path) -> Check:
    free = shutil.disk_usage(root).free
    found = f"{free / GB:.0f} GB free"
    if free < DISK_NEEDED:
        return Check("disk space", Status.WARN, f"{found}; the uk-sample profile needs about 25 GB")
    return Check("disk space", Status.OK, found)


def check_duckdb() -> Check:
    try:
        duckdb = importlib.import_module("duckdb")
    except ImportError:
        return Check("DuckDB", Status.WARN, "not importable; run uv sync --all-packages")
    return Check("DuckDB", Status.OK, str(getattr(duckdb, "__version__", "importable")))


def read_access(root: Path) -> dict[str, Any]:
    """The `access` mapping of docs/build/project.yaml, or {} when it cannot be read."""
    try:
        data = yaml.safe_load((root / PROJECT_FILE).read_text(encoding="utf-8"))
    except OSError, yaml.YAMLError:
        return {}
    access = data.get("access") if isinstance(data, dict) else None
    return access if isinstance(access, dict) else {}


def _days(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def check_real_data(root: Path, access: dict[str, Any], now: float | None = None) -> Check:
    """Count real files and compare their ages with the retention settings (stat only)."""
    folder = root / REAL_DIR
    now = time.time() if now is None else now
    data_days, label_days = _days(access.get("real_data_days")), _days(access.get("label_days"))
    files = expired = 0
    oldest = now
    for directory, _, names in os.walk(folder):  # symbolic links to folders are not followed
        labels = Path(directory).relative_to(folder).parts[:1] == ("labels",)
        limit = label_days if labels else data_days
        for name in names:
            try:
                modified = os.lstat(os.path.join(directory, name)).st_mtime
            except OSError:
                continue
            files += 1
            oldest = min(oldest, modified)
            if limit is not None and now - modified > limit * DAY:
                expired += 1
    if not files:
        return Check("real data", Status.OK, f"none under {REAL_DIR.as_posix()}/")
    age = int((now - oldest) // DAY)
    found = f"{files} files under {REAL_DIR.as_posix()}/, the oldest {age} days old"
    if data_days is None or label_days is None:
        return Check(
            "real data", Status.WARN, f"{found}; access.real_data_days or label_days unset"
        )
    if expired:
        return Check(
            "real data",
            Status.WARN,
            f"{found}; {expired} older than access.real_data_days ({data_days}) or label_days"
            f" ({label_days}): purge them (neonradar data purge --expired)",
        )
    return Check("real data", Status.OK, f"{found}; within access.real_data_days ({data_days})")


def check_spill(root: Path) -> Check:
    folders = 0
    for spill in SPILL_DIRS:
        try:
            folders += sum(1 for entry in (root / spill).iterdir() if entry.is_dir())
        except OSError:  # missing or unreadable: nothing to count
            continue
    if folders:
        return Check(
            "DuckDB spill",
            Status.WARN,
            f"{folders} leftover run folder(s) in data/cache/*/duckdb-tmp/; a finished run deletes"
            " its own, so a run crashed: purge them",
        )
    return Check("DuckDB spill", Status.OK, "no leftover folders")


def check_real_instance(info: dict[str, Any] | None) -> Check:
    if info is None:
        return Check("neo4j-real", Status.OK, "not running (Docker is not reachable)")
    project = f"label=com.docker.compose.project={COMPOSE_PROJECT}"
    service = "label=com.docker.compose.service=neo4j-real"
    names = run("docker", "ps", "--filter", project, "--filter", service, "--format", "{{.Names}}")
    if names:
        return Check(
            "neo4j-real",
            Status.WARN,
            "the real-data instance is running; stop it with `make down-real` when you are done",
        )
    return Check("neo4j-real", Status.OK, "not running")


def check_real_profiles(access: dict[str, Any]) -> Check:
    profiles = access.get("real_data_profiles")
    if not profiles:
        return Check("real profiles", Status.OK, "none allowed (access.real_data_profiles is [])")
    allowed = (
        ", ".join(str(profile) for profile in profiles)
        if isinstance(profiles, list)
        else str(profiles)
    )
    reminder = f"this machine must be listed in {MACHINES_DOC} before NR_REAL_DATA_MACHINE=approved"
    if access.get("data_protection_filed") is not True:
        return Check(
            "real profiles",
            Status.WARN,
            f"{allowed} allowed, but access.data_protection_filed is false, so they refuse to"
            f" run; {reminder}",
        )
    return Check("real profiles", Status.OK, f"{allowed} allowed; {reminder}")


def run_checks(root: Path = REPO_ROOT) -> list[Check]:
    info = docker_info()
    stack = stack_ports() if info else set()
    access = read_access(root)
    return [
        check_python(),
        check_uv(),
        check_docker(info),
        check_compose(),
        check_env_file(root),
        *(check_port(port, stack) for port in PORTS),
        check_memory(info),
        check_icu(),
        check_disk(root),
        check_duckdb(),
        check_real_data(root, access),
        check_spill(root),
        check_real_instance(info),
        check_real_profiles(access),
    ]
