"""The typology catalog: one `detect/typologies/<slug>.yaml` file per typology (PHASE-1.md 5.4).

Not a frozen contract, but alerts refer to it, so its shape is fixed. `TypologyFile` enforces
the shape and the rules under it; `load_catalog` reads the folder (an empty or missing folder
is an empty catalog); `render_index` renders docs/typologies/README.md for
`neonradar docs typology-index`. Only a typology researcher sets `status: approved`.
NeonRadar's own words in a file (wording templates, false positives, the slug, and the name of a
typology with a detector) pass the 7.1 wording lint.
"""

import string
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from neonradar_contracts.alert import (
    CITATION_KEY_PATTERN,
    MODULE_PATTERN,
    SLUG_PATTERN,
    VERSION_PATTERN,
)
from neonradar_contracts.wording import (
    find_forbidden,
    find_forbidden_in_name,
    says_synthetic_scenario,
)

# The workspace installs members editable, so this is the root of the repository.
REPO_ROOT = Path(__file__).resolve().parents[3]
TYPOLOGY_DIR = REPO_ROOT / "detect" / "typologies"
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


class Parameter(_Strict):
    """A detector parameter: its default and, for numbers, the allowed range."""

    default: int | float | str | bool
    min: int | float | None = None
    max: int | float | None = None

    @model_validator(mode="after")
    def _in_range(self) -> Self:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        value = self.default
        if isinstance(value, bool | str):
            return self
        if (self.min is not None and value < self.min) or (
            self.max is not None and value > self.max
        ):
            raise ValueError(f"default {value} is outside [{self.min}, {self.max}]")
        return self


class Wording(_Strict):
    """Headline templates: placeholders are metric names in braces, for example `{cycle_length}`."""

    headline_structural: Text
    headline_synthetic: Text


def placeholders(template: str) -> list[str]:
    """The metric names a template uses; plain `{name}` or `{name:<format spec>}` only."""
    names = []
    for _, field, _, conversion in string.Formatter().parse(template):
        if field is None:
            continue
        if not field.isidentifier() or conversion is not None:
            raise ValueError(
                f"placeholder {{{field}}} must be a metric name, as in {{cycle_length}}"
            )
        names.append(field)
    return names


class TypologyFile(_Strict):
    """One typology definition (5.4)."""

    slug: Slug
    name: Text
    version: Annotated[str, Field(pattern=VERSION_PATTERN)]
    status: Literal["draft", "approved", "retired"]
    tier: Literal["core", "extended", "explainer_only"]
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
        for key in ("headline_structural", "headline_synthetic"):
            unknown = sorted(set(placeholders(getattr(wording, key))) - set(self.metrics))
            if unknown:
                raise ValueError(f"wording.{key} uses names that are not metrics: {unknown}")
        # 7.1: "synthetic scenario" only when every entity in the alert is synthetic.
        if says_synthetic_scenario(wording.headline_structural):
            raise ValueError("wording.headline_structural must not say 'synthetic scenario'")
        if not wording.headline_synthetic.startswith("Synthetic scenario"):
            raise ValueError("wording.headline_synthetic must start with 'Synthetic scenario'")

    def _lint(self) -> None:
        texts = {f"false_positives[{i}]": text for i, text in enumerate(self.false_positives)}
        if self.wording is not None:
            texts["wording.headline_structural"] = self.wording.headline_structural
            texts["wording.headline_synthetic"] = self.wording.headline_synthetic
        if self.detector is not None:  # alerts say "matches the graph pattern of <name>"
            texts["name"] = self.name
        found = {where: find_forbidden(text) for where, text in texts.items()}
        found["slug"] = find_forbidden_in_name(self.slug)
        problems = [f"{where}: {'; '.join(terms)}" for where, terms in found.items() if terms]
        if problems:
            raise ValueError(f"wording lint (7.1) fails: {' | '.join(problems)}")


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
