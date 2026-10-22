"""The typology catalog: one `detect/typologies/<slug>.yaml` file per typology (PHASE-1.md 5.4).

Not a frozen contract, but alerts refer to it, so its shape is fixed. `TypologyFile` enforces
the shape and the rules under it; `load_catalog` reads the folder (an empty or missing folder
is an empty catalog); `render_index` renders docs/typologies/README.md for
`neonradar docs typology-index`. Only a typology researcher sets `status: approved`.
NeonRadar's own words in a file (wording templates, false positives, the slug, the shape name,
and the name of a typology with a detector) pass the 7.1 wording lint.

Phase 3 (PHASE-3.md M3.2 deliverable 3, 7.5.2) adds `shape_name`, `wording.variants` and
`wording.detail`, list defaults, and the placeholder filters `{name|money}`, `{name|pct}` and
`{name|n:noun[:plural]}`. `load()` validates every file with `TypologyFile` and returns the
frozen `Typology` view the detection runner reads; it also refuses what the Phase 3 renderer
cannot render (a detector typology without a shape name, a format spec or a stray brace), so a
run never emits a summary without its shape or a template with a placeholder left in it, and a
`detector` other than `neonradar_detect.detectors.<slug>`, the only module the runner imports.
`params_for` builds a detector's `Params` from the file's defaults and a profile's overrides.
"""

import dataclasses
import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Annotated, Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from neonradar_contracts.alert import (
    CITATION_KEY_PATTERN,
    MODULE_PATTERN,
    SLUG_PATTERN,
    VERSION_PATTERN,
)
from neonradar_contracts.api import TypologyStatus, TypologyTier
from neonradar_contracts.wording import (
    find_forbidden,
    find_forbidden_in_name,
    says_synthetic_scenario,
)

# The workspace installs members editable, so this is the root of the repository.
REPO_ROOT = Path(__file__).resolve().parents[3]
TYPOLOGY_DIR = REPO_ROOT / "detect" / "typologies"
CATALOG_DIR = TYPOLOGY_DIR  # the name the Phase 3 code book uses
DETECTOR_PACKAGE = "neonradar_detect.detectors"
INDEX_PATH = REPO_ROOT / "docs" / "typologies" / "README.md"
HANDLE_PATTERN = r"^@[A-Za-z0-9][A-Za-z0-9-]*(/[A-Za-z0-9._-]+)?$"

Slug = Annotated[str, Field(pattern=SLUG_PATTERN)]
Text = Annotated[str, Field(min_length=1)]
Handle = Annotated[str, Field(pattern=HANDLE_PATTERN)]
CitationKey = Annotated[str, Field(pattern=CITATION_KEY_PATTERN)]


class CatalogError(ValueError):
    """A typology file is not valid; the message names the file."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


Scalar = bool | int | float | str


class Parameter(_Strict):
    """A detector parameter: its default and, for numbers, the allowed range. Booleans,
    strings and lists give only a default (PHASE-3.md M3.2 deliverable 3)."""

    default: Scalar | list[Scalar]
    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def _in_range(self) -> Self:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        value = self.default
        if isinstance(value, bool | str | list):
            return self
        if (self.min is not None and value < self.min) or (
            self.max is not None and value > self.max
        ):
            raise ValueError(f"default {value} is outside [{self.min}, {self.max}]")
        return self


class VariantWording(_Strict):
    """A detector variant's headline pair, with the main pair's rules (PHASE-3.md 7.5.2)."""

    headline_structural: Text
    headline_synthetic: Text
    detail: Text | None = None


class Wording(VariantWording):
    """Headline templates: placeholders are metric names in braces, for example `{cycle_length}`;
    from Phase 3 also `variants` (a pair per detector variant) and `detail` (summary text)."""

    variants: dict[Slug, VariantWording] = {}


# `{name|money}`, `{name|pct}`, `{name|n:singular}` and `{name|n:singular:plural}` (7.5.2)
FILTERED = re.compile(r"\{([^{}|]*)\|([^{}]*)\}")
NOUN = r"[^:{}|]+"
FILTER = re.compile(rf"money|pct|n:{NOUN}(?::{NOUN})?")
# What the Phase 3 renderer substitutes (`wording.PLACEHOLDER`, kept equal by a test).
RENDERED = re.compile(r"\{(\w+)(?:\|([a-z]+)(?::([^:}]+))?(?::([^:}]+))?)?\}")


def _fields(template: str) -> list[tuple[str, str | None, str]]:
    """(name, filter, format spec) of every placeholder, in order. A filter is checked here;
    the rest of the text goes through Phase 1's parsing, so its errors stay the same."""
    filters: list[tuple[str, str]] = []

    def plain(found: re.Match[str]) -> str:
        name, spec = found.groups()
        if not name.isidentifier():
            raise ValueError(
                f"placeholder {{{name}|...}} must be a metric name, as in {{cycle_length}}"
            )
        if not FILTER.fullmatch(spec):
            raise ValueError(
                f"placeholder {{{name}|{spec}}}: a filter is money, pct or n:<noun>[:<plural>]"
            )
        filters.append((name, spec))
        return f"{{{name}\x00{len(filters) - 1}}}"

    text = FILTERED.sub(plain, template)
    found: list[tuple[str, str | None, str]] = []
    for _, field, spec, conversion in string.Formatter().parse(text):
        if field is None:
            continue
        if "\x00" in field:
            name, index = field.split("\x00")
            found.append((name, filters[int(index)][1], spec or ""))
            continue
        if not field.isidentifier() or conversion is not None:
            raise ValueError(
                f"placeholder {{{field}}} must be a metric name, as in {{cycle_length}}"
            )
        found.append((field, None, spec or ""))
    return found


def placeholders(template: str) -> list[str]:
    """The metric names a template uses: `{name}`, `{name:<format spec>}` (Phase 1) or
    `{name|filter}` (Phase 3: money, pct, n:<noun>[:<plural>])."""
    return [name for name, _, _ in _fields(template)]


def phase3_problems(template: str) -> list[str]:
    """What the Phase 3 renderer cannot render: a format spec, or a brace left after its
    placeholders are taken out (PHASE-3.md 7.5.2; reconciliation C2)."""
    problems = [
        f"{{{name}:{spec}}} has a format spec" for name, _, spec in _fields(template) if spec
    ]
    if "{" in RENDERED.sub("", template) or "}" in RENDERED.sub("", template):
        problems.append("a brace is not part of a placeholder")
    return problems


class TypologyFile(_Strict):
    """One typology definition (5.4)."""

    slug: Slug
    name: Text
    shape_name: Text | None = None  # Phase 3: required by load() when detector is set
    version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    status: TypologyStatus  # the API serves both (C3), so the values live in the contract
    tier: TypologyTier
    owner: Handle
    approved_by: Handle | None
    summary: Text
    doc: Annotated[str, Field(pattern=r"^docs/typologies/[a-z0-9-]+\.md$")]
    citations: Annotated[list[CitationKey], Field(min_length=1)]
    graph_pattern: Text
    parameters: dict[str, Parameter]
    metrics: list[Slug]
    wording: Wording | None
    false_positives: list[Text]
    synthetic_support: Literal["high", "medium", "low", "none"]
    generator_scenario: Slug | None
    detector: Annotated[str, Field(pattern=MODULE_PATTERN)] | None

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.status == "approved" and self.approved_by is None:
            raise ValueError(
                "status approved needs approved_by (only a typology researcher sets it)"
            )
        if self.approved_by is not None and self.approved_by.casefold() == "@todo":
            raise ValueError("approved_by must name the typology researcher, not @TODO")
        if self.tier == "explainer_only" and self.detector is not None:
            raise ValueError("an explainer_only typology has no detector (detector: null)")
        expected_doc = f"docs/typologies/{self.slug.replace('_', '-')}.md"
        if self.doc != expected_doc:
            raise ValueError(f"doc must be {expected_doc}")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics must not repeat a name")
        if self.detector is not None:
            missing = [
                field for field in ("parameters", "metrics", "wording") if not getattr(self, field)
            ]
            if missing:
                raise ValueError(f"a typology with a detector needs {', '.join(missing)}")
        if self.wording is not None:
            self._check_wording(self.wording)
        self._lint()
        return self

    def _check_wording(self, wording: Wording) -> None:
        for where, pair in _pairs(wording):
            for key, template in _templates(pair):
                fields = _fields(template)
                unknown = sorted({name for name, _, _ in fields} - set(self.metrics))
                if unknown:
                    raise ValueError(f"{where}{key} uses names that are not metrics: {unknown}")
                if "currency" not in self.metrics and any(f == "money" for _, f, _ in fields):
                    raise ValueError(f"{where}{key} uses money, so currency must be a metric")
            # 7.1: "synthetic scenario" only when every entity in the alert is synthetic; the
            # detail goes into every summary, so it never says it either.
            for key in ("headline_structural", "detail"):
                if says_synthetic_scenario(getattr(pair, key) or ""):
                    raise ValueError(f"{where}{key} must not say 'synthetic scenario'")
            if not pair.headline_synthetic.startswith("Synthetic scenario"):
                raise ValueError(f"{where}headline_synthetic must start with 'Synthetic scenario'")

    def _lint(self) -> None:
        texts = {f"false_positives[{i}]": text for i, text in enumerate(self.false_positives)}
        if self.wording is not None:
            for where, pair in _pairs(self.wording):
                for key, template in _templates(pair):
                    texts[f"{where}{key}"] = template
        if self.detector is not None:  # alerts say "matches the graph pattern of <name>"
            texts["name"] = self.name
        if self.shape_name is not None:
            texts["shape_name"] = self.shape_name
        found = {where: find_forbidden(text) for where, text in texts.items()}
        found["slug"] = find_forbidden_in_name(self.slug)
        problems = [f"{where}: {'; '.join(terms)}" for where, terms in found.items() if terms]
        if problems:
            raise ValueError(f"wording lint (7.1) fails: {' | '.join(problems)}")


def _pairs(wording: Wording) -> list[tuple[str, VariantWording]]:
    """The main pair and each variant's pair, with the prefix their errors use."""
    return [
        ("wording.", wording),
        *((f"wording.variants.{name}.", pair) for name, pair in sorted(wording.variants.items())),
    ]


def _templates(pair: VariantWording) -> list[tuple[str, str]]:
    keys = ("headline_structural", "headline_synthetic", "detail")
    return [(key, value) for key in keys if (value := getattr(pair, key)) is not None]


def load_typology(path: Path) -> TypologyFile:
    """Read and validate one typology file."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return TypologyFile.model_validate(data)
    except (yaml.YAMLError, ValidationError) as exc:
        raise CatalogError(f"{path.name}: {exc}") from exc


def load_catalog(directory: Path = TYPOLOGY_DIR) -> dict[str, TypologyFile]:
    """Every `<slug>.yaml` in `directory`, by slug, sorted; an empty catalog if there are none."""
    catalog = {}
    for path in sorted(directory.glob("*.yaml")):
        typology = load_typology(path)
        if typology.slug != path.stem:
            raise CatalogError(f"{path.name}: slug {typology.slug!r} must match the file name")
        catalog[typology.slug] = typology
    return catalog


@dataclass(frozen=True, slots=True)
class Typology:
    """The frozen view of a validated typology file that the Phase 3 detection code reads
    (`runner`, `wording`, `alerts`): the code book's interface (PHASE-3.md 2.10, Catalog)."""

    slug: str
    name: str
    shape_name: str
    tier: str
    version: str
    doc: str
    citations: tuple[str, ...]
    parameters: Mapping[str, Mapping[str, Any]]
    metrics: tuple[str, ...]
    wording: Mapping[str, Any]
    false_positives: tuple[str, ...]
    detector: str


def _view(item: TypologyFile) -> Typology:
    wording = item.wording.model_dump(exclude_none=True) if item.wording else {}
    if not wording.get("variants"):
        wording.pop("variants", None)
    return Typology(
        item.slug,
        item.name,
        item.shape_name or "",
        item.tier,
        item.version,
        item.doc,
        tuple(item.citations),
        MappingProxyType(
            {name: p.model_dump(exclude_none=True) for name, p in item.parameters.items()}
        ),
        tuple(item.metrics),
        MappingProxyType(wording),
        tuple(item.false_positives),
        item.detector or "",
    )


def _renderable(item: TypologyFile) -> list[str]:
    """Why the Phase 3 renderer cannot run this typology (empty when it can)."""
    problems = []
    # The runner imports the module a file names (PHASE-3.md 7.5.3): only the package's own
    # module for this slug, so a file never makes it import anything else.
    if item.detector is not None and item.detector != f"{DETECTOR_PACKAGE}.{item.slug}":
        problems.append(f"detector must be {DETECTOR_PACKAGE}.{item.slug} or null")
    if item.detector is not None and item.shape_name is None:
        problems.append("a typology with a detector needs shape_name")
    if item.wording is not None:
        for where, pair in _pairs(item.wording):
            for key, template in _templates(pair):
                problems += [f"{where}{key}: {p}" for p in phase3_problems(template)]
    return problems


def load(directory: Path = CATALOG_DIR) -> dict[str, Typology]:
    """Every typology file, validated with `TypologyFile`, as the frozen `Typology` view; a
    `CatalogError` when one cannot be run by the Phase 3 code (a detector outside the package,
    no shape name for a detector, a format spec, a stray brace)."""
    out = {}
    for slug, item in load_catalog(directory).items():
        problems = _renderable(item)
        if problems:
            raise CatalogError(f"{slug}.yaml: {'; '.join(problems)}")
        out[slug] = _view(item)
    return out


def _fits(value: Any, default: Any) -> bool:
    """An override has the type of the parameter's default (a whole number for a float is fine)."""
    if isinstance(default, bool) or isinstance(value, bool):
        return isinstance(value, bool) and isinstance(default, bool)
    if isinstance(default, float):
        return isinstance(value, int | float)
    if isinstance(default, list):
        return isinstance(value, list | tuple)
    return type(value) is type(default)


def params_for(
    typology: Typology, module: ModuleType, overrides: Mapping[str, Any] | None = None
) -> Any:
    """The detector's `Params`: the catalog's defaults, then the profile's overrides, each of
    the default's type and within the parameter's bounds (KeyError for an unknown name,
    ValueError for a value that does not fit). Lists become tuples."""
    values: dict[str, Any] = {}
    fields = {f.name for f in dataclasses.fields(module.Params)}
    for name, spec in typology.parameters.items():
        if name not in fields:
            raise KeyError(f"{typology.slug}: catalog parameter {name} is not a detector parameter")
        values[name] = spec["default"]
    for name, value in (overrides or {}).items():
        bounds = typology.parameters.get(name)
        if bounds is None:
            raise KeyError(f"{typology.slug}: unknown parameter {name}")
        spec = bounds
        if not _fits(value, spec["default"]):
            raise ValueError(f"{typology.slug}: {name} must have the type of its default")
        low, high = spec.get("min"), spec.get("max")
        if (low is not None and value < low) or (high is not None and value > high):
            raise ValueError(f"{typology.slug}: {name}={value} outside [{low}, {high}]")
        values[name] = value
    for name, value in values.items():
        if isinstance(value, list):
            values[name] = tuple(value)
    return module.Params(**values)


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render_index(catalog: dict[str, TypologyFile]) -> str:
    """The catalog index, docs/typologies/README.md (slug, name, tier, status, owner, detector)."""
    lines = [
        "# Typology catalog",
        "",
        "<!-- Generated by `uv run neonradar docs typology-index` from detect/typologies/*.yaml."
        " Do not edit by hand: change the typology files and run the command again. -->",
        "",
        "One definition file per typology in `detect/typologies/` (the shape is in"
        " `contracts/C4-alert.md`) and a plain-language explainer for each in this folder."
        " Every definition starts as `draft`; only a typology researcher sets it to `approved`.",
        "",
    ]
    if not catalog:
        lines.append("No typology files yet.")
    else:
        lines += [
            "| Slug | Name | Tier | Status | Owner | Detector |",
            "|---|---|---|---|---|---|",
        ]
        for slug, typology in sorted(catalog.items()):
            explainer = Path(typology.doc).name
            lines.append(
                f"| [`{slug}`]({explainer}) | {_cell(typology.name)} | {typology.tier} "
                f"| {typology.status} | {typology.owner} "
                f"| {'yes' if typology.detector else 'no'} |"
            )
    return "\n".join(lines) + "\n"
