"""C4 Alert v1.0.0: the object every detector produces and the API serves (PHASE-1.md 5.4).

`Alert` validates the rules of the field table, plus the clarifications listed in
contracts/CHANGELOG.md: the id is recomputed from the evidence, ids have C2 form, steps cite
evidence edges, and an alert never calls itself a synthetic scenario while it names an entity
or dataset that is not synthetic (guardrail G1). See contracts/C4-alert.md.
"""

import hashlib
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue, model_validator

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.wording import find_forbidden

# C1 rule R1 (records.ID_RE, as changed by OD-11) without named groups and anchors, so that it
# also works in JSON Schema. contracts/tests/test_alert.py checks that the two agree.
_ID = r"[a-z][a-z0-9]{1,15}-[A-Za-z0-9.-]{0,99}[A-Za-z0-9]"
ENTITY_ID_PATTERN = rf"^{_ID}$"
# C2 relationship ids: the FtM interval entity id, or `<entity id>|addr|<address id>` for
# HAS_ADDRESS, or `<entity id>|sanction|<sanction id>` for SUBJECT_OF (5.2).
EDGE_ID_PATTERN = rf"^{_ID}(\|(addr|sanction)\|{_ID})?$"
SLUG_PATTERN = r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$"
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"
MODULE_PATTERN = r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+$"
RUN_ID_PATTERN = r"^run-\d{8}T\d{6}-[0-9a-f]{4}$"
ALERT_ID_PATTERN = r"^alr-[0-9a-f]{20}$"
UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
HEADLINE_MAX = 140
STEP_TEXT_MAX = 280

Priority = Literal["high", "medium", "low"]
WordingClass = Literal["structural_pattern", "synthetic_scenario"]


def _is_utc_time(value: str) -> str:
    datetime.fromisoformat(value)  # rejects impossible dates such as month 13
    return value


EntityId = Annotated[str, Field(pattern=ENTITY_ID_PATTERN)]
EdgeId = Annotated[str, Field(pattern=EDGE_ID_PATTERN)]
UtcTime = Annotated[str, Field(pattern=UTC_PATTERN), AfterValidator(_is_utc_time)]
Slug = Annotated[str, Field(pattern=SLUG_PATTERN)]
Text = Annotated[str, Field(min_length=1)]


def compute_alert_id(
    typology: str, detector_version: str, node_ids: Iterable[str], edge_ids: Iterable[str]
) -> str:
    """`alr-` plus the first 20 hex characters of SHA-1 over `typology`, `detector.version`,
    the sorted edge ids and the sorted node ids, joined with `|` (5.4).

    Sorting is by Unicode code point (Python's `sorted`), so the same detector on the same
    graph always yields the same id, whatever order the query returned.
    """
    parts = [typology, detector_version, *sorted(edge_ids), *sorted(node_ids)]
    digest = hashlib.sha1("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"alr-{digest[:20]}"


def default_priority(pattern_strength: float) -> Priority:
    """The default queue rule: at least 0.75 is high, at least 0.5 medium, else low (5.4)."""
    if pattern_strength >= 0.75:
        return "high"
    return "medium" if pattern_strength >= 0.5 else "low"


def _unique(values: list[str], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} must not repeat an id")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Detector(_Strict):
    """The detector that produced the alert: module path, version and its query's hash."""

    name: Annotated[str, Field(pattern=MODULE_PATTERN)]
    version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    query_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Subject(_Strict):
    """An entity the alert is about; the API links it with FLAGS. Roles are typology-defined."""

    entity_id: EntityId
    role: Slug
    caption: Text


class EvidenceQuery(_Strict):
    """The Cypher query and parameters that reproduce the finding."""

    cypher: Text
    parameters: dict[str, JsonValue]


class Window(_Strict):
    """The time span of the evidence (UTC)."""

    start: UtcTime
    end: UtcTime

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("window.start must not be after window.end")
        return self


class Evidence(_Strict):
    """The evidence subgraph as C2 ids, and how to reproduce it."""

    node_ids: Annotated[list[EntityId], Field(min_length=1)]
    edge_ids: list[EdgeId]
    query: EvidenceQuery
    window: Window | None = None

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        _unique(self.node_ids, "evidence.node_ids")
        _unique(self.edge_ids, "evidence.edge_ids")
        return self


class ExplanationStep(_Strict):
    """One step of the explanation, in order, citing the evidence edges it describes."""

    order: Annotated[int, Field(ge=1)]
    text: Annotated[str, Field(min_length=1, max_length=STEP_TEXT_MAX)]
    edge_ids: list[EdgeId]


class TypologyReference(_Strict):
    """Where the typology is defined: catalog slug, explainer and bibliography keys."""

    slug: Slug
    doc_path: Annotated[str, Field(pattern=r"^docs/typologies/[a-z0-9-]+\.md$")]
    citations: Annotated[list[Slug], Field(min_length=1)]


class Explanation(_Strict):
    """Plain-language explanation; texts describe patterns, never accusations (7.1)."""

    summary: Text
    steps: list[ExplanationStep]
    typology_reference: TypologyReference
    false_positive_notes: list[Text]

    @model_validator(mode="after")
    def _in_order(self) -> Self:
        if [step.order for step in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("explanation.steps must be numbered 1, 2, 3, ... in order")
        return self


class DataFlags(_Strict):
    """What kind of data the alert touches (5.4); the UI words the alert from these."""

    involves_real_entities: bool
    synthetic_activity: bool
    datasets: Annotated[list[Slug], Field(min_length=1)]

    @model_validator(mode="after")
    def _registered(self) -> Self:
        _unique(self.datasets, "data_flags.datasets")
        unknown = [slug for slug in self.datasets if load_registry().get(slug) is None]
        if unknown:
            raise ValueError(f"datasets not in contracts/datasets.yaml: {', '.join(unknown)}")
        return self


class Alert(_Strict):
    """C4 Alert v1.0.0 (5.4). `pattern_strength` orders the queue; it is never a risk score."""

    alert_id: Annotated[str, Field(pattern=ALERT_ID_PATTERN)]
    contract_version: Literal["1.0.0"]
    typology: Slug
    typology_version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    detector: Detector
    run_id: Annotated[str, Field(pattern=RUN_ID_PATTERN)]
    created_at: UtcTime
    priority: Priority
    pattern_strength: Annotated[float, Field(ge=0, le=1)]
    headline: Annotated[str, Field(min_length=1, max_length=HEADLINE_MAX)]
    wording_class: WordingClass
    subjects: Annotated[list[Subject], Field(min_length=1)]
    evidence: Evidence
    metrics: dict[str, int | float | str]
    explanation: Explanation
    data_flags: DataFlags
    disclaimer_id: Literal["standing-v1"]

    @model_validator(mode="after")
    def _rules(self) -> Self:
        expected = compute_alert_id(
            self.typology, self.detector.version, self.evidence.node_ids, self.evidence.edge_ids
        )
        if self.alert_id != expected:
            raise ValueError(f"alert_id must be {expected} (compute_alert_id over the evidence)")
        if self.explanation.typology_reference.slug != self.typology:
            raise ValueError("explanation.typology_reference.slug must equal typology")
        stray = sorted(
            {edge for step in self.explanation.steps for edge in step.edge_ids}
            - set(self.evidence.edge_ids)
        )
        if stray:
            raise ValueError(f"explanation steps cite edges not in the evidence: {stray}")
        terms = find_forbidden(self.headline)
        if terms:
            raise ValueError(f"headline fails the wording lint (7.1): {'; '.join(terms)}")
        self._check_wording_class()
        return self

    def _check_wording_class(self) -> None:
        flags = self.data_flags
        if (self.wording_class == "synthetic_scenario") == flags.involves_real_entities:
            raise ValueError(
                "wording_class must be synthetic_scenario exactly when "
                "data_flags.involves_real_entities is false"
            )
        if flags.involves_real_entities:
            return
        # A dataset or an id prefix of a non-synthetic dataset means a real entity is involved.
        # Prefixes of no dataset (`nr`, canonical ids from Phase 2) prove nothing either way.
        real_datasets = [dataset for dataset in load_registry().datasets if not dataset.synthetic]
        slugs = {dataset.slug for dataset in real_datasets}
        prefixes = {dataset.id_prefix for dataset in real_datasets}
        ids = [subject.entity_id for subject in self.subjects] + self.evidence.node_ids
        real = [slug for slug in flags.datasets if slug in slugs]
        real += [entity_id for entity_id in ids if entity_id.split("-", 1)[0] in prefixes]
        if real:
            raise ValueError(
                "data_flags.involves_real_entities must be true: the alert names "
                f"non-synthetic data ({', '.join(real)})"
            )
        if not flags.synthetic_activity:
            raise ValueError(
                "data_flags.synthetic_activity must be true when every entity is synthetic"
            )
