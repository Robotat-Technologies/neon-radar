"""The OpenSanctions bulk loader (PHASE-2.md M2.7), only where `access.opensanctions` allows it.

This part is the download: `data fetch` reads the collection's `index.json` (following the 307
redirect) and downloads it with `entities.ftm.json`, whose size it checks. The loader refuses
first, before any request, unless `access.opensanctions` is `licensed` or `exempt` (the data
manager's gate runs before it). The builder follows in the second M2.7 pull request.
"""

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool

from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.project import Project, load_project
from neonradar_ingest.data.sources import RemoteFile, SourceSpec, register_source
from neonradar_ingest.http import HttpClient
from neonradar_ingest.sources.opensanctions.mapping import DATASET
from neonradar_ingest.sources.opensanctions.spike import ENTITIES_FILE, make_client, read_index

INDEX_FILE = "index.json"


class OpenSanctionsSource(BaseModel):
    """The profile block: `collection` is `sanctions` (the default) or `default` (everything)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    collection: Literal["sanctions", "default"] = "sanctions"


def refuse_unless_allowed(project: Project) -> None:
    """RealDataRefused (exit 3, the Phase 1 message) unless `licensed` or `exempt`."""
    refusal = project.access_refusal(DATASET)
    if refusal is not None:
        raise RealDataRefused(*refusal)


def discover_for(collection: str) -> Callable[[HttpClient], list[RemoteFile]]:
    def discover(client: HttpClient) -> list[RemoteFile]:
        project = load_project()
        refuse_unless_allowed(project)  # before any request
        info = read_index(client, collection, access=project.access.opensanctions)
        version = info.version or datetime.now(UTC).strftime("%Y-%m-%d")
        return [
            RemoteFile(INDEX_FILE, info.url, version, None, None, product=collection),
            RemoteFile(ENTITIES_FILE, info.entities_url, version, info.size, None, collection),
        ]

    return discover


def products(profile: Profile) -> Mapping[str, Callable[[HttpClient], list[RemoteFile]]]:
    """Only the collection the profile names is downloaded (data minimisation)."""
    collection = profile.options(DATASET).collection
    return {collection: discover_for(collection)}


register_source_model(DATASET, OpenSanctionsSource)
register_source(SourceSpec(DATASET, discover_for("sanctions"), make_client, products))
