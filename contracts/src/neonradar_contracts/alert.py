"""C4 Alert v1.0.0: the object every detector produces and the API serves (PHASE-1.md 5.4).

`Alert` validates the rules of the field table, plus the clarifications listed in
contracts/CHANGELOG.md: the id and the query hash are recomputed, ids have C2 form, steps cite
evidence edges, and an alert says "synthetic scenario" only when its wording class is
synthetic_scenario, a class it never claims while it names an entity or dataset that is not
synthetic (guardrail G1). Validation reads contracts/datasets.yaml and
contracts/wording/forbidden-terms.txt next to the package. See contracts/C4-alert.md.
"""

import hashlib
import json
import math
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated, Any, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue, model_validator

from neonradar_contracts import versions
from neonradar_contracts.datasets import load_registry
from neonradar_contracts.wording import SYNTHETIC_PHRASE, find_forbidden, find_forbidden_in_name

# C1 rule R1 (records.ID_RE, as changed by OD-11) without named groups and anchors, so that it
# also works in JSON Schema. contracts/tests/test_alert.py checks that the two agree.
_ID = r"[a-z][a-z0-9]{1,15}-[A-Za-z0-9.-]{0,99}[A-Za-z0-9]"
ENTITY_ID_PATTERN = rf"^{_ID}$"
# C2 relationship ids: the FtM interval entity id, or `<entity id>|addr|<address id>` for
# HAS_ADDRESS, or `<entity id>|sanction|<sanction id>` for SUBJECT_OF (5.2).
EDGE_ID_PATTERN = rf"^{_ID}(\|(addr|sanction)\|{_ID})?$"
SLUG_PATTERN = r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$"
# Bibliography keys (PHASE-1.md 7.3): lowercase snake case with at least one underscore.
CITATION_KEY_PATTERN = r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$"
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"
# Any 1.x release. A later 1.x model accepts every earlier 1.x value; a major release needs
# detection to be re-run (the same rule as the record contract's `nr.v`).
CONTRACT_VERSION_PATTERN = r"^1\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
MODULE_PATTERN = r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+$"
RUN_ID_PATTERN = r"^run-\d{8}T\d{6}-[0-9a-f]{4}$"
ALERT_ID_PATTERN = r"^alr-[0-9a-f]{20}$"
UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
# Lengths of the fixed-length fields. Python's `re` (which the jsonschema package uses for
# `pattern`) lets `$` match before a final newline; the length bounds reject it there too.
UTC_LENGTH = 20
ALERT_ID_LENGTH = RUN_ID_LENGTH = 24
SHA256_LENGTH = 64
HEADLINE_MAX = 140
STEP_TEXT_MAX = 280

Priority = Literal["high", "medium", "low"]
WordingClass = Literal["structural_pattern", "synthetic_scenario"]


def _is_utc_time(value: str) -> str:
    datetime.fromisoformat(value)  # rejects impossible dates such as month 13
    return value


def _is_finite(value: JsonValue) -> JsonValue:
    """JSON has no NaN or infinity. `allow_inf_nan=False` covers float fields and Python input,
    but pydantic lets `NaN` and `Infinity` in JSON text through a `JsonValue`."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("must be a finite number: JSON has no NaN or infinity")
    if isinstance(value, list | dict):
        for item in value.values() if isinstance(value, dict) else value:
            _is_finite(item)
    return value


def _fixed(pattern: str, length: int) -> Any:
    """A field of fixed length: the pattern, plus the length so that the exported JSON Schema
    rejects a trailing newline under Python's `re` as well."""
    return Field(pattern=pattern, min_length=length, max_length=length)


EntityId = Annotated[str, Field(pattern=ENTITY_ID_PATTERN)]
EdgeId = Annotated[str, Field(pattern=EDGE_ID_PATTERN)]
UtcTime = Annotated[str, _fixed(UTC_PATTERN, UTC_LENGTH), AfterValidator(_is_utc_time)]
Slug = Annotated[str, Field(pattern=SLUG_PATTERN)]
CitationKey = Annotated[str, Field(pattern=CITATION_KEY_PATTERN)]
Text = Annotated[str, Field(min_length=1)]


def compute_alert_id(
    typology: str, detector_version: str, node_ids: Iterable[str], edge_ids: Iterable[str]
) -> str:
    """`alr-` plus the first 20 hex characters of SHA-1 over `typology`, `detector.version`,
    the sorted edge ids and the sorted node ids (5.4).

    The hashed text is the compact JSON array `[typology, version, [edge ids], [node ids]]`
    (separators `,` and `:`, no spaces, UTF-8), so the boundary between the lists is marked and
    a `|` inside a composite C2 edge id cannot collide with a separator. Sorting is by Unicode
    code point (Python's `sorted`), so the same detector on the same graph always yields the
    same id, whatever order the query returned.
    """
    parts = [typology, detector_version, sorted(edge_ids), sorted(node_ids)]
    text = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"alr-{digest[:20]}"


def query_sha256(cypher: str) -> str:
    """`detector.query_sha256`: the SHA-256 (lower-case hex) of `evidence.query.cypher` in UTF-8."""
    return hashlib.sha256(cypher.encode("utf-8")).hexdigest()


def default_priority(pattern_strength: float) -> Priority:
    """The default queue rule: at least 0.75 is high, at least 0.5 medium, else low (5.4)."""
    if pattern_strength >= 0.75:
        return "high"
    return "medium" if pattern_strength >= 0.5 else "low"


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _unique(values: list[str], what: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{what} must not repeat an id")


def _id_parts(edge_id: str) -> list[str]:
    """The entity ids in a C2 relationship id: both ends of `a|addr|b`, or the interval id."""
    return edge_id.split("|")[::2]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class Detector(_Strict):
    """The detector that produced the alert: module path, version and the evidence query's hash."""

    name: Annotated[str, Field(pattern=MODULE_PATTERN)]
    version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    query_sha256: Annotated[str, _fixed(SHA256_PATTERN, SHA256_LENGTH)]


class Subject(_Strict):
    """An entity the alert is about; the API links it with FLAGS. Roles are typology-defined."""

    entity_id: EntityId
    role: Slug
    caption: Text


class EvidenceQuery(_Strict):
    """The Cypher query and parameters that reproduce the finding."""

    cypher: Text
    parameters: dict[str, Annotated[JsonValue, AfterValidator(_is_finite)]]


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
    # Required but nullable: the key is always present, null when the finding has no time
    # window, so the JSON Schema and C3's OpenAPI list it as required (CHANGELOG, C4).
    window: Window | None

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        _unique(self.node_ids, "evidence.node_ids")
        _unique(self.edge_ids, "evidence.edge_ids")
        # Every evidence edge's endpoints are evidence nodes. A composite id names both
        # (`a|addr|b`, `a|sanction|b`); for plain interval ids the detector checks it (M1.9b).
        nodes = set(self.node_ids)
        for edge in self.edge_ids:
            ends = _id_parts(edge) if "|" in edge else []
            missing = [end for end in ends if end not in nodes]
            if missing:
                raise ValueError(f"evidence edge {edge} needs its endpoints in node_ids: {missing}")
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
    citations: Annotated[list[CitationKey], Field(min_length=1)]


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

    alert_id: Annotated[str, _fixed(ALERT_ID_PATTERN, ALERT_ID_LENGTH)]
    contract_version: Annotated[str, Field(pattern=CONTRACT_VERSION_PATTERN)]
    typology: Slug
    typology_version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    detector: Detector
    run_id: Annotated[str, _fixed(RUN_ID_PATTERN, RUN_ID_LENGTH)]
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
        if _version(self.contract_version) > _version(versions.ALERT):
            raise ValueError(
                f"contract_version {self.contract_version} is newer than this model "
                f"({versions.ALERT}); upgrade neonradar-contracts"
            )
        expected = compute_alert_id(
            self.typology, self.detector.version, self.evidence.node_ids, self.evidence.edge_ids
        )
        if self.alert_id != expected:
            raise ValueError(f"alert_id must be {expected} (compute_alert_id over the evidence)")
        if self.detector.query_sha256 != query_sha256(self.evidence.query.cypher):
            raise ValueError("detector.query_sha256 must be the SHA-256 of evidence.query.cypher")
        if self.explanation.typology_reference.slug != self.typology:
            raise ValueError("explanation.typology_reference.slug must equal typology")
        # C2 FLAGS carries one role per alert and entity, so an entity is a subject only once.
        entity_ids = [subject.entity_id for subject in self.subjects]
        if len(set(entity_ids)) != len(entity_ids):
            raise ValueError("subjects must not repeat an entity_id (FLAGS holds one role each)")
        stray = sorted(
            {edge for step in self.explanation.steps for edge in step.edge_ids}
            - set(self.evidence.edge_ids)
        )
        if stray:
            raise ValueError(f"explanation steps cite edges not in the evidence: {stray}")
        self._check_wording()
        self._check_wording_class()
        return self

    def _check_wording(self) -> None:
        """7.1 lint on NeonRadar's own words: the headline, the false-positive notes, the
        typology slug and the subject roles (`_` read as a space). Summary and step texts hold
        source names, so the detection runner lints them with those names masked (M1.9b)."""
        notes = enumerate(self.explanation.false_positive_notes)
        texts = {"headline": self.headline}
        texts |= {f"explanation.false_positive_notes[{i}]": note for i, note in notes}
        found = {where: find_forbidden(text) for where, text in texts.items()}
        found["typology"] = find_forbidden_in_name(self.typology)
        for subject in self.subjects:
            found[f"role {subject.role}"] = find_forbidden_in_name(subject.role)
        problems = [f"{where}: {'; '.join(terms)}" for where, terms in found.items() if terms]
        if problems:
            raise ValueError(f"wording lint (7.1) fails: {' | '.join(problems)}")
        if self.wording_class == "synthetic_scenario":
            return
        texts = {"headline": self.headline, "explanation.summary": self.explanation.summary}
        texts |= {f"step {step.order}": step.text for step in self.explanation.steps}
        said = [where for where, text in texts.items() if SYNTHETIC_PHRASE.search(text)]
        if said:
            raise ValueError(
                "only a synthetic_scenario alert may say 'synthetic scenario' (7.1): "
                f"{', '.join(said)}"
            )

    def _check_wording_class(self) -> None:
        flags = self.data_flags
        if (self.wording_class == "synthetic_scenario") == flags.involves_real_entities:
            raise ValueError(
                "wording_class must be synthetic_scenario exactly when "
                "data_flags.involves_real_entities is false"
            )
        # An id prefix of a non-synthetic dataset means real data. Prefixes of no dataset (`nr`,
        # canonical ids from Phase 2) prove nothing either way.
        real_datasets = [dataset for dataset in load_registry().datasets if not dataset.synthetic]
        slugs = {dataset.slug for dataset in real_datasets}
        prefixes = {dataset.id_prefix for dataset in real_datasets}
        if flags.synthetic_activity:
            real_edges = [
                edge
                for edge in self.evidence.edge_ids
                if any(part.split("-", 1)[0] in prefixes for part in _id_parts(edge))
            ]
            if real_edges:
                raise ValueError(
                    "data_flags.synthetic_activity must be false: evidence relationships come "
                    f"from non-synthetic data ({', '.join(real_edges)})"
                )
        if flags.involves_real_entities:
            return
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
