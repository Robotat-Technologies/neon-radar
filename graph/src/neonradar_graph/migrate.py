"""Schema migration runner: `neonradar graph migrate` (PHASE-1.md 5.2, M1.7b).

Applies `graph/schema/migrations/NNNN_<name>.cypher` in order, one statement per auto-commit
transaction, waits for the new indexes, then records `(:SchemaMigration {id, checksum,
applied_at})`. Re-running is a no-op. An applied migration whose file changed, or one the
folder no longer has, stops the run before anything is applied.

File format: one statement per line, ending with `;`; lines starting with `//` and blank lines
are skipped. Every statement must be idempotent (`IF NOT EXISTS`), because a run that fails
half-way has already applied the statements before the failure.
"""

import hashlib
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from neo4j import Driver

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "schema" / "migrations"
FILE_RE = re.compile(r"^(?P<number>\d{4})_[a-z0-9_]+\.cypher\Z")
APPLIED = "MATCH (m:SchemaMigration) RETURN m.id AS id, m.checksum AS checksum"
RECORD = (
    "MERGE (m:SchemaMigration {id: $id}) SET m.checksum = $checksum, m.applied_at = $applied_at"
)
AWAIT_INDEXES = "CALL db.awaitIndexes($seconds)"


class MigrationError(Exception):
    """The migrations folder or the database's migration history is not usable."""


@dataclass(frozen=True, slots=True)
class Migration:
    """One migration file: `id` is the file name without `.cypher`, for example `0001_init`."""

    id: str
    path: Path
    checksum: str
    statements: tuple[str, ...]


@dataclass(slots=True)
class MigrationReport:
    """What a run did: the migrations it applied and those that were already applied."""

    applied: list[Migration] = field(default_factory=list)
    already_applied: list[str] = field(default_factory=list)


def checksum(text: str) -> str:
    """SHA-256 of the file text with line endings normalised to LF (a checkout may use CRLF)."""
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def parse_statements(text: str, source: str) -> tuple[str, ...]:
    """The statements of a migration file, without their trailing `;`."""
    statements = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if not line.endswith(";") or len(line) == 1:
            raise MigrationError(
                f"{source}:{number}: each statement is one line that ends with ';'"
            )
        statements.append(line.removesuffix(";").rstrip())
    if not statements:
        raise MigrationError(f"{source}: no statements")
    return tuple(statements)


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Every migration in `directory`, ordered by number. Other `.cypher` names are refused."""
    paths = sorted(directory.glob("*.cypher"))
    if not paths:
        raise MigrationError(f"no migrations in {directory}")
    migrations: dict[str, Migration] = {}
    for path in paths:
        match = FILE_RE.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"{path.name}: migration files are named NNNN_<name>.cypher")
        if match["number"] in migrations:
            other = migrations[match["number"]].path.name
            raise MigrationError(f"{path.name} and {other} have the same number")
        text = path.read_text(encoding="utf-8")
        migrations[match["number"]] = Migration(
            id=path.stem,
            path=path,
            checksum=checksum(text),
            statements=parse_statements(text, path.name),
        )
    return [migrations[number] for number in sorted(migrations)]


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def migrate(
    driver: Driver,
    database: str = "neo4j",
    directory: Path = MIGRATIONS_DIR,
    *,
    await_indexes_s: int = 300,
    clock: Callable[[], str] = _now,
) -> MigrationReport:
    """Apply the pending migrations in order; raise MigrationError before applying anything if
    an applied migration was edited or is missing from `directory`."""
    migrations = discover(directory)
    # Before 0001 the label and its properties do not exist yet; the server's warnings about
    # that are expected, so this one read asks for no notifications.
    with driver.session(database=database, notifications_min_severity="OFF") as session:
        applied = {str(record["id"]): str(record["checksum"]) for record in session.run(APPLIED)}
    on_disk = {migration.id: migration for migration in migrations}
    missing = sorted(set(applied) - set(on_disk))
    if missing:
        raise MigrationError(
            f"the database has migration {', '.join(missing)}, which is not in {directory}:"
            " use the repository version that applied it"
        )
    for migration in migrations:
        stored = applied.get(migration.id)
        if stored is not None and stored != migration.checksum:
            raise MigrationError(
                f"{migration.path.name} changed after it was applied (database checksum"
                f" {stored[:12]}, file {migration.checksum[:12]}): add a new migration;"
                " never edit an applied one"
            )
    report = MigrationReport(already_applied=[m.id for m in migrations if m.id in applied])
    for migration in migrations:
        if migration.id in applied:
            continue
        logger.info("applying %s (%d statements)", migration.id, len(migration.statements))
        with driver.session(database=database) as session:
            for statement in migration.statements:
                session.run(statement).consume()  # auto-commit: one transaction per statement
            session.run(AWAIT_INDEXES, seconds=await_indexes_s).consume()
        driver.execute_query(
            RECORD,
            id=migration.id,
            checksum=migration.checksum,
            applied_at=clock(),
            database_=database,
        )
        report.applied.append(migration)
    return report
