"""Check synthetic names against other record files: `neonradar synth check-names`.

Used before committing a regenerated fixture: pass the synthetic files, and with `--against`
any other C1 files at hand, for example spike output in `data/cache/spikes/`. A synthetic
name collides when its `name_key` equals the key of any name, alias or previous name of a
legal entity in those files. The check reads files only; it never changes the generator's
output, which must not depend on what a machine has cached (ADR-0005).
"""

from collections.abc import Iterable, Iterator
from pathlib import Path

from followthemoney import model

from neonradar_contracts.records import iter_records
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.names import is_denied

NAME_PROPS = ("name", "alias", "previousName")


def legal_entity_names(paths: Iterable[Path], props: tuple[str, ...]) -> Iterator[tuple[str, str]]:
    """(record id, name) for every legal entity in the files."""
    for path in paths:
        for data in iter_records(path):
            schema = model.get(str(data.get("schema")))
            if schema is None or not schema.is_a("LegalEntity"):
                continue
            properties = data.get("properties") or {}
            for prop in props:
                for value in properties.get(prop) or []:
                    yield str(data.get("id")), str(value)


def check_names(
    synthetic: Iterable[Path], against: Iterable[Path]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Return the synthetic names, the denylisted ones and the ones that collide."""
    names = list(legal_entity_names(synthetic, ("name",)))
    taken = {name_key(name) for _, name in legal_entity_names(against, NAME_PROPS)}
    denied = [(rid, name) for rid, name in names if is_denied(name)]
    collisions = [(rid, name) for rid, name in names if name_key(name) in taken]
    return names, denied, collisions
