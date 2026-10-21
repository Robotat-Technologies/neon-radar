"""`neonradar data purge --graph`: wipe the real-data Neo4j instance (PHASE-2.md 4.5, M2.2).

It first removes the `neo4j-real` container (stopping it; its logs live inside it), then deletes
its volume, which Docker names `neonradar_neo4j-real-data` (the Compose project, then the volume
key; reconciliation A11), found by its Compose labels and by that exact name. So the store
files and the transaction logs, where deleted nodes would otherwise linger, go too. The default
instance is never touched (C2 L17). Plain `docker` commands are used, so `compose.yaml` and
`.env` are not read.
"""

import subprocess
from collections.abc import Callable

from neonradar_cli.doctor import COMPOSE_PROJECT

SERVICE = "neo4j-real"
VOLUME = "neo4j-real-data"
VOLUME_NAME = f"{COMPOSE_PROJECT}_{VOLUME}"  # neonradar_neo4j-real-data
PROJECT_LABEL = f"label=com.docker.compose.project={COMPOSE_PROJECT}"
TIMEOUT = 120

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class RealGraphError(Exception):
    exit_code = 1
    counts_only = True  # Docker's own output is never printed


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 (fixed docker arguments, no shell)
        command, capture_output=True, text=True, check=False, timeout=TIMEOUT
    )


def _ids(run: Runner, command: list[str]) -> list[str]:
    result = run(command)
    if result.returncode != 0:
        raise RealGraphError(f"`{' '.join(command[:3])}` failed (exit {result.returncode})")
    return result.stdout.split()


def wipe(run: Runner | None = None) -> tuple[int, int]:
    """Remove the real instance's containers, then its volumes; return how many of each."""
    run = run or _run  # looked up per call, so tests can replace it
    try:
        containers = _ids(
            run,
            ["docker", "ps", "--all", "--quiet", "--filter", PROJECT_LABEL,
             "--filter", f"label=com.docker.compose.service={SERVICE}"],
        )  # fmt: skip
        if containers:
            _ids(run, ["docker", "rm", "--force", "--volumes", *containers])
        volumes = _ids(
            run,
            ["docker", "volume", "ls", "--quiet", "--filter", PROJECT_LABEL,
             "--filter", f"label=com.docker.compose.volume={VOLUME}"],
        )  # fmt: skip
        named = _ids(run, ["docker", "volume", "ls", "--quiet", "--filter", f"name={VOLUME_NAME}"])
        volumes += [name for name in named if name == VOLUME_NAME and name not in volumes]
        if volumes:
            _ids(run, ["docker", "volume", "rm", *volumes])
    except FileNotFoundError:
        raise RealGraphError("Docker is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        raise RealGraphError(f"Docker did not answer within {TIMEOUT} s") from None
    return len(containers), len(volumes)
