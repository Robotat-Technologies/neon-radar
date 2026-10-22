"""`neonradar data purge --graph`: wipe the real-data Neo4j instance (PHASE-2.md 4.5, M2.2).

It first removes the `neo4j-real` container (stopped and removed with its anonymous volumes),
then deletes its two named volumes, which Docker names `neonradar_neo4j-real-data` (the store,
transaction logs included, where deleted nodes would otherwise linger) and
`neonradar_neo4j-real-logs` (the server and query logs): the Compose project, then the volume
key (reconciliation A11). Each is found by its Compose labels and by its exact name. The default
instance is never touched (C2 L17). Plain `docker` commands are used, so `compose.yaml` and
`.env` are not read.
"""

import subprocess
from collections.abc import Callable

from neonradar_cli.doctor import COMPOSE_PROJECT

SERVICE = "neo4j-real"
VOLUMES = ("neo4j-real-data", "neo4j-real-logs")  # the volume keys in compose.yaml
PROJECT_LABEL = f"label=com.docker.compose.project={COMPOSE_PROJECT}"
TIMEOUT = 120

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class RealGraphError(Exception):
    exit_code = 1
    counts_only = True  # Docker's own output is never printed


def volume_names() -> list[str]:
    """`neonradar_neo4j-real-data` and `neonradar_neo4j-real-logs`."""
    return [f"{COMPOSE_PROJECT}_{key}" for key in VOLUMES]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 (fixed docker arguments, no shell)
        command, capture_output=True, text=True, check=False, timeout=TIMEOUT
    )


def _ids(run: Runner, command: list[str]) -> list[str]:
    result = run(command)
    if result.returncode != 0:
        raise RealGraphError(f"`{' '.join(command[:3])}` failed (exit {result.returncode})")
    return result.stdout.split()


def _volumes(run: Runner) -> list[str]:
    found: list[str] = []
    for key, name in zip(VOLUMES, volume_names(), strict=True):
        labelled = _ids(
            run,
            ["docker", "volume", "ls", "--quiet", "--filter", PROJECT_LABEL,
             "--filter", f"label=com.docker.compose.volume={key}"],
        )  # fmt: skip
        named = _ids(run, ["docker", "volume", "ls", "--quiet", "--filter", f"name={name}"])
        for volume in [*labelled, *(v for v in named if v == name)]:  # the name filter is partial
            if volume not in found:
                found.append(volume)
    return found


def check_project_name() -> None:
    """Refuse when `COMPOSE_PROJECT_NAME` (environment or `.env`) names another Compose project:
    the real instance's container and volumes would then carry other names and labels."""
    from neonradar_ingest.data import gate
    from neonradar_ingest.settings import IngestSettings

    name = IngestSettings(_env_file=gate.ENV_FILE).compose_project_name.strip()
    if name and name != COMPOSE_PROJECT:
        raise RealGraphError(
            f"COMPOSE_PROJECT_NAME is set to another project; purge --graph works only for the"
            f" project {COMPOSE_PROJECT} (compose.yaml): unset it and run the purge again"
        )


def wipe(run: Runner | None = None) -> tuple[int, int]:
    """Remove the real instance's containers, then its volumes; return how many of each."""
    run = run or _run  # looked up per call, so tests can replace it
    check_project_name()
    try:
        containers = _ids(
            run,
            ["docker", "ps", "--all", "--quiet", "--filter", PROJECT_LABEL,
             "--filter", f"label=com.docker.compose.service={SERVICE}"],
        )  # fmt: skip
        if containers:
            _ids(run, ["docker", "rm", "--force", "--volumes", *containers])
        volumes = _volumes(run)
        if volumes:
            _ids(run, ["docker", "volume", "rm", *volumes])
    except FileNotFoundError:
        raise RealGraphError("Docker is not installed or not on PATH") from None
    except subprocess.TimeoutExpired:
        raise RealGraphError(f"Docker did not answer within {TIMEOUT} s") from None
    return len(containers), len(volumes)
