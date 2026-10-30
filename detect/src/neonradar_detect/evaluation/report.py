"""The published detection figures: one Markdown table and its JSON twin (PHASE-3.md 7.6.4).

The text below the table is fixed (7.6.4): it says what each column counts and what the figures
do not show. Rates with nothing to count print "n = 0", never 0 or 1
(`evaluation-alerting.md` 1.5). Numbers are rounded for display only; the JSON keeps the counts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from neonradar_detect.evaluation.metrics import Figures, Interval, Rate, macro

READING_NOTES = (
    "How to read this table. Recall counts planted scenarios: a scenario is detected when an "
    "alert of its own typology matches it (PHASE-3.md 7.6.2). Precision counts alerts: true "
    "alerts divided by all alerts of the typology, so duplicates, look-alike hits, partial "
    "overlaps, alerts on other typologies' scenarios and alerts on background activity all count "
    "against it. Each interval is the wider of the pooled Wilson 95 percent interval and a t "
    "interval across seeds. The high and medium column is precision among the alerts the queue "
    "puts first. Look-alikes alerted counts planted benign look-alikes that drew an alert."
)
LIMITATIONS = (
    "What these figures do not show. Every scenario, look-alike and payment is synthetic and was "
    "written by the same team that wrote the detectors, so the figures measure how well the "
    "detectors find NeonRadar's own definitions of each pattern, not how they would perform on "
    "real data. The similar businesses that `cash_commingling` compares a business with were made "
    "by the same generator, so for that typology the comparison is circular. Precision depends on "
    "how many scenarios and look-alikes were planted, so it says nothing about alert volumes in a "
    "bank. A pattern match is not evidence of wrongdoing."
)


@dataclass(frozen=True, slots=True)
class ReportMeta:
    title: str
    split: str  # "dev" or "test"
    seeds: tuple[int, ...]
    engine: str  # "neo4j" or "memory"
    generated_at: str
    profile: str
    generator_version: str
    label_schema: str
    rules_version: str
    params_sha256: str
    detectors: Mapping[str, str]  # slug -> detector version


def _num(value: float) -> str:
    return f"{value:.2f}"


def fmt_rate(rate: Rate) -> str:
    if rate.value is None:
        return "n = 0"
    return f"{_num(rate.value)} ({rate.k}/{rate.n})"


def fmt_interval(interval: Interval | None) -> str:
    if interval is None:
        return ""
    return f"[{_num(interval[0])}, {_num(interval[1])}]"


def fmt_pair(k: int, n: int) -> str:
    return "n = 0" if n == 0 else f"{_num(k / n)} ({k}/{n})"


def high_medium(bands: Mapping[str, tuple[int, int]]) -> tuple[int, int]:
    k = bands["high"][0] + bands["medium"][0]
    n = bands["high"][1] + bands["medium"][1]
    return k, n


def markdown(
    figures: Sequence[Figures], bands: Mapping[str, Mapping[str, tuple[int, int]]], meta: ReportMeta
) -> str:
    seeds = ", ".join(str(s) for s in meta.seeds)
    lines = [
        f"# {meta.title}",
        "",
        f"Split: {meta.split}. Seeds: {seeds}. Profile: `{meta.profile}`. Engine: {meta.engine}. "
        f"Generated {meta.generated_at}.",
        f"Generator {meta.generator_version}, label schema {meta.label_schema}, matching rules "
        f"{meta.rules_version}, parameters `{meta.params_sha256[:12]}`.",
        "",
        "| Typology | Recall | 95% interval | Precision | 95% interval | Precision, high and "
        "medium | True / dup / look-alike / partial / other / background | Look-alikes alerted |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in figures:
        hk, hn = high_medium(bands[f.typology])
        kinds = (
            f"{f.true} / {f.duplicate} / {f.lookalike} / {f.partial} / {f.other} / {f.background}"
        )
        lines.append(
            f"| `{f.typology}` | {fmt_rate(f.recall)} | {fmt_interval(f.recall.headline)} | "
            f"{fmt_rate(f.precision)} | {fmt_interval(f.precision.headline)} | "
            f"{fmt_pair(hk, hn)} | {kinds} | {f.lookalikes_alerted}/{f.lookalikes} |"
        )
    m = macro(figures)
    mr, mp, mf = m["macro_recall"], m["macro_precision"], m["macro_f1"]
    lines += [
        "",
        f"Macro recall {_num(mr) if mr is not None else 'n = 0'}, macro precision "
        f"{_num(mp) if mp is not None else 'n = 0'} over {m['macro_precision_typologies']} "
        f"typologies with alerts, macro F1 {_num(mf) if mf is not None else 'n = 0'} (the mean "
        f"of per-typology F1) over {m['typologies']} typologies.",
        "",
        READING_NOTES,
        "",
        LIMITATIONS,
        "",
    ]
    return "\n".join(lines)


def to_json(
    figures: Sequence[Figures], bands: Mapping[str, Mapping[str, tuple[int, int]]], meta: ReportMeta
) -> dict[str, Any]:
    return {
        "meta": {**asdict(meta), "seeds": list(meta.seeds), "detectors": dict(meta.detectors)},
        "typologies": {
            f.typology: {
                **{k: v for k, v in asdict(f).items() if k not in ("recall", "precision")},
                "recall": asdict(f.recall),
                "precision": asdict(f.precision),
                "bands": {b: list(v) for b, v in bands[f.typology].items()},
            }
            for f in figures
        },
        "macro": macro(figures),
    }
