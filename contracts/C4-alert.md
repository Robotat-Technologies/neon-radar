# C4: Alert v1.0.0

The object every detector produces, the API serves and the copilot (Phase 4) explains. A detection run writes its alerts to `data/runs/<run_id>/alerts.jsonl` and loads them into Neo4j as `:Alert` nodes linked with `FLAGS` to their subjects (C2). The API reads alerts only from Neo4j and parses the `payload` property, which holds the complete alert as JSON.

- Status: version 1.0.0, **not frozen yet**. The tech lead freezes the four contracts at Gate 1 with the tag `contracts-v1.0.0` (`docs/build/PHASE-1.md` sections 5.0 and 8). After that, changes need an approved contract-change issue.
- Code: `neonradar_contracts.alert` (`Alert`, `compute_alert_id`, `query_sha256`, `default_priority`), `neonradar_contracts.wording` (disclaimers, the wording lint, `SYNTHETIC_PHRASE` and `says_synthetic_scenario`); in the detect package, `neonradar_detect.catalog` (`TypologyFile`, `load_catalog`) and `neonradar_detect.wording` (`render_headline`).
- JSON Schema: `contracts/schemas/alert.v1.json`, generated from the model by `neonradar contracts export` (`make contracts`); `neonradar contracts check` (part of `make contracts-check`) fails when the committed file differs from the model. The JSON Schema checks shapes and formats only; id recomputation, wording class and data flags, the wording lint, step edges, evidence edge endpoints, distinct subjects, registered datasets, window order and finite numbers in `evidence.query.parameters` need `neonradar_contracts.alert.Alert`.
- Validation reads `contracts/datasets.yaml` and `contracts/wording/forbidden-terms.txt` from next to the package (the workspace installs it editable), so the model sees the repository's registry and patterns.
- Example: `contracts/examples/c4/circular_flow.json` (synthetic; validates).
- Wording files: `contracts/wording/` (the three disclaimers and the forbidden patterns, verbatim from `PHASE-1.md` 7.1).
- Source: `docs/build/PHASE-1.md` sections 5.4 and 7.1, with the changes and clarifications listed in [CHANGELOG.md](CHANGELOG.md).

## Fields

Every object is closed: an unknown key fails validation. Values are strict: `"0.79"` is not a number and `1` is not `true`. Numbers are finite: NaN and infinity fail everywhere, `metrics` and `evidence.query.parameters` (at any depth) included. JSON has no such numbers, but pydantic's JSON parser reads the literals `NaN` and `Infinity`, and a non-finite number would be written back as `null`.

Fixed-length fields also carry their length: `alert_id` and `run_id` 24 characters, `created_at` and the `window` times 20, `detector.query_sha256` 64. The jsonschema package checks `pattern` with Python's `re`, where `$` also matches before a final newline; the length makes the JSON Schema reject that newline too (the model rejects it either way).

| Field | Type | Rule |
|---|---|---|
| `alert_id` | string | `alr-` plus the first 20 hex characters of SHA-1 over `typology`, `detector.version`, sorted `evidence.edge_ids` and sorted `evidence.node_ids`, hashed as one compact JSON array (see [The alert id](#the-alert-id)). Re-running the same detector on the same graph yields the same ids. The model recomputes it and rejects a mismatch. |
| `contract_version` | string | The C4 version the alert was written under, `1.<minor>.<patch>`: `"1.0.0"` today. A later 1.x model accepts every earlier 1.x value, and a model rejects a version newer than itself; a major version needs detection to be re-run (the same rule as the record contract's `nr.v`) |
| `typology` | string | A slug from the typology catalog (lowercase snake case; passes the wording lint with `_` read as a space) |
| `typology_version` | string | Version of the typology definition used (`MAJOR.MINOR.PATCH`) |
| `detector` | object | `name` (dotted module path), `version` (`MAJOR.MINOR.PATCH`), `query_sha256` (64 lower-case hex: the SHA-256 of `evidence.query.cypher` in UTF-8; the model recomputes it) |
| `run_id` | string | `run-<UTC yyyymmddThhmmss>-<4 hex>` |
| `created_at` | string | UTC ISO datetime `YYYY-MM-DDTHH:MM:SSZ` |
| `priority` | `"high"`, `"medium"`, `"low"` | Queue ordering. Default rule (`default_priority()`): `pattern_strength` of at least 0.75 is high, at least 0.5 medium, else low; a typology may document its own rule, so the model does not enforce it |
| `pattern_strength` | number in [0, 1] | How closely the evidence matches the typology's graph pattern. Never called a risk or suspicion score. |
| `headline` | string, 1 to 140 characters | Rendered from the typology's wording template; passes the wording lint and says "synthetic scenario" only in a `synthetic_scenario` alert (both checked by the model) |
| `wording_class` | `"structural_pattern"` or `"synthetic_scenario"` | `synthetic_scenario` when every evidence node, every subject and every holder (source of `HOLDS_ACCOUNT`) of an evidence account is synthetic; otherwise `structural_pattern`. So `synthetic_scenario` holds exactly when `data_flags.involves_real_entities` is false |
| `subjects` | list of `{entity_id, role, caption}`, at least one | Roles are typology-defined, lowercase snake case (`origin`, `origin_holder`, `collector`, `intermediary`, `owner`, ...) and pass the wording lint with `_` read as a space (so `mule_account` fails); `entity_id` is a C2 entity id, and no `entity_id` appears twice (C2 `FLAGS` carries one `role` per alert and entity) |
| `evidence` | object | `node_ids` (C2 entity ids, at least one), `edge_ids` (C2 relationship ids), neither repeating an id, and both endpoints of every evidence edge among `node_ids` (the model checks composite ids such as `a\|addr\|b`; for plain interval ids the detector checks it, M1.9b); `query` (`cypher`, `parameters`) so the finding can be reproduced; `window` (`start`, `end`, UTC like `created_at`, start not after end), or `null` when the finding has no time window: the key is always present (the JSON Schema lists it as required, so C3 serves it as `Window \| null`, never as an optional key) |
| `metrics` | object | Typology-specific scalar values documented in the typology file: numbers, and strings that are codes such as a currency. Detectors never put names in metrics (metrics fill headline templates). For circular flow: `cycle_length`, `sent_amount` (first hop), `returned_amount` (last hop), `currency`, `duration_hours`, `duration_days` (hours divided by 24, rounded up), `return_ratio`. A typology with several findings per subject emits one alert per finding, so metrics stay scalar (for example `sanctions_exposure`, Phase 3: one alert per sanctioned owner) |
| `explanation` | object | `summary` (plain language), `steps` (ordered `{order, text, edge_ids}`, numbered 1, 2, 3, ..., each text at most 280 characters, each `edge_ids` drawn from `evidence.edge_ids`), `typology_reference` (`slug` equal to `typology`, `doc_path` under `docs/typologies/`, `citations`: at least one bibliography key), `false_positive_notes` (from the typology file; they pass the wording lint) |
| `data_flags` | object | `involves_real_entities` (true if any evidence node, subject or holder of an evidence account has `synthetic = false`), `synthetic_activity` (true if every evidence relationship is synthetic, so the UI can say that a pattern next to a real entity lies in generated background activity; false whenever an evidence edge id has the id prefix of a non-synthetic dataset), `datasets` (the distinct dataset slugs of the evidence nodes and relationships, the subjects and the evidence-account holders; at least one, each in `contracts/datasets.yaml`) |
| `disclaimer_id` | string | `"standing-v1"`; the API adds the text from `MetaResponse.disclaimers` |

C2 ids: an entity id has the C1 form (rule R1, as changed by OD-11: `<prefix>-<rest>`, letters, digits, dots and hyphens). A relationship id is the FtM interval entity id (for example a `Payment` id), `<entity id>|addr|<address id>` for `HAS_ADDRESS`, or `<entity id>|sanction|<sanction id>` for `SUBJECT_OF`. Neo4j `elementId()` values are not C2 ids and fail. C2 builds composite ids from record ids, which equal node ids in Phase 1, so the endpoint check holds; when Phase 2 entity resolution gives nodes canonical ids (with the record ids in `referents`), the check needs revisiting before it rejects valid alerts (open question for Gate 1).

## The alert id

```python
text = json.dumps([typology, detector_version, sorted(edge_ids), sorted(node_ids)],
                  ensure_ascii=False, separators=(",", ":"))
alert_id = "alr-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
```

For the example, the hashed text starts `["circular_flow","0.1.0",["syn-payment-000101",`. A JSON array rather than text joined with `|`: composite C2 edge ids contain `|`, and the boundary between the edge and node lists would otherwise be unmarked.

Sorting is by Unicode code point (Python's `sorted`), so the order in which a query returns the ids does not matter. The id changes when the typology, the detector version or any evidence id changes; it does not depend on `run_id` or `created_at`, so a re-run finds the same alert again and the loader can `MERGE` on it. Use `neonradar_contracts.alert.compute_alert_id`.

## Wording class and data flags (guardrail G1)

The wording class decides whether an alert may say "synthetic scenario". Detectors compute `involves_real_entities`, `synthetic_activity` and `wording_class` with one helper (M1.9b) from the evidence nodes, the subjects and the holders of every evidence account. The model then checks that the alert does not contradict itself:

1. `wording_class` is `synthetic_scenario` exactly when `involves_real_entities` is false.
2. `involves_real_entities` must be true when `data_flags.datasets` lists a dataset that is not synthetic, or when a subject or evidence node id has the id prefix of a dataset that is not synthetic (`gbch`, `gleif`, `icij`, `os`). An id whose prefix belongs to no dataset (the reserved `nr` prefix of Phase 2 canonical ids) proves nothing either way, so the datasets decide.
3. An alert in which every entity is synthetic has `synthetic_activity: true`: relationships between synthetic entities are synthetic.
4. `synthetic_activity` is false when an evidence relationship comes from non-synthetic data: an evidence edge id with the id prefix of a non-synthetic dataset (`gbch-own-...`), or, for a composite id (`a|addr|b`, `a|sanction|b`), either end with such a prefix. An id prefix of no dataset proves nothing either way, as in rule 2. Under rule 3, an all-synthetic alert cannot name such an edge at all.
5. Only a `synthetic_scenario` alert says "synthetic scenario": in a `structural_pattern` alert the headline, the summary and every step text are checked against `SYNTHETIC_PHRASE` (`\bsynthetic[\s_-]+scenario`, case-insensitive) after NFKC normalisation (`says_synthetic_scenario`), so "Synthetic-Scenario" and a fullwidth "s" fail too. `render_headline` and `TypologyFile` use the same check.

A holder of an evidence account is not always a subject (an intermediate account's holder, for example), so its dataset must appear in `data_flags.datasets`.

## Runs and storage

- The detection run loads each alert as an `:Alert` node merged on `alert_id`, linked with `PRODUCED` from its `:DetectionRun` and with `FLAGS` to its subjects. Because the id does not depend on the run, a re-run finds the same node: the merged `:Alert` keeps the latest run's payload, scalar properties and `run_id`, and every run that found it keeps its `PRODUCED` relationship.
- To list the alerts of one run, the API (M1.9c) filters `run_id` through `PRODUCED` (`(:DetectionRun {run_id: $run_id})-[:PRODUCED]->(a:Alert)`), not through the alert's own `run_id` property, which names only the latest run.
- `data/runs/<run_id>/alerts.jsonl` is each run's audit copy, not an API source.

## Example

`contracts/examples/c4/circular_flow.json`, the walking skeleton's synthetic circular-flow alert. The ids and the query hash are computed (the query text is abbreviated with `...`, as in the spec, and `query_sha256` is the SHA-256 of that text). `pattern_strength` 0.79 follows the M1.9b formula: 0.5 x 0.96 + 0.3 x (1 minus 151.7 / 336) + 0.2 x 0.75.

```json
{
  "alert_id": "alr-f82a84574538090f0624",
  "contract_version": "1.0.0",
  "typology": "circular_flow",
  "typology_version": "0.1.0",
  "detector": {"name": "neonradar_detect.detectors.circular_flow", "version": "0.1.0", "query_sha256": "a4e70cdb45dc30e9fb9745b29c6a506e1f3ebeeb6f944d7ef70137b16c3b2759"},
  "run_id": "run-20261021T101500-7f3a",
  "created_at": "2026-10-21T10:15:02Z",
  "priority": "high",
  "pattern_strength": 0.79,
  "headline": "Synthetic scenario: funds returned to the originating account through 4 transfers within 7 days",
  "wording_class": "synthetic_scenario",
  "subjects": [
    {"entity_id": "syn-acct-0007", "role": "origin", "caption": "NRSYN0000000007"},
    {"entity_id": "syn-co-0003", "role": "origin_holder", "caption": "Fenwhistle Holdings Ltd"}
  ],
  "evidence": {
    "node_ids": ["syn-acct-0007", "syn-acct-0012", "syn-acct-0015", "syn-acct-0021"],
    "edge_ids": ["syn-payment-000101", "syn-payment-000102", "syn-payment-000103", "syn-payment-000104"],
    "query": {"cypher": "MATCH p = (a:Account {id: $origin})-[t:PAID]->{2,6}(a) ...", "parameters": {"origin": "syn-acct-0007", "max_window_days": 14}},
    "window": {"start": "2026-03-02T09:00:00Z", "end": "2026-03-08T16:40:00Z"}
  },
  "metrics": {"cycle_length": 4, "sent_amount": 120000.0, "returned_amount": 115200.0, "currency": "EUR", "duration_hours": 151.7, "duration_days": 7, "return_ratio": 0.96},
  "explanation": {
    "summary": "EUR 120,000 left account NRSYN0000000007 and EUR 115,200 came back to it after passing through three other accounts in just over six days.",
    "steps": [
      {"order": 1, "text": "NRSYN0000000007 sent EUR 120,000 to NRSYN0000000012 on 2 March.", "edge_ids": ["syn-payment-000101"]},
      {"order": 2, "text": "NRSYN0000000012 sent EUR 118,800 to NRSYN0000000015 on 4 March.", "edge_ids": ["syn-payment-000102"]},
      {"order": 3, "text": "NRSYN0000000015 sent EUR 117,000 to NRSYN0000000021 on 6 March.", "edge_ids": ["syn-payment-000103"]},
      {"order": 4, "text": "NRSYN0000000021 sent EUR 115,200 to NRSYN0000000007 on 8 March.", "edge_ids": ["syn-payment-000104"]}
    ],
    "typology_reference": {"slug": "circular_flow", "doc_path": "docs/typologies/circular-flow.md", "citations": ["fatf_egmont_tbml_indicators_2021", "fatf_egmont_concealment_2018", "ffiec_appendix_f", "fatf_pml_2018"]},
    "false_positive_notes": ["Refunds, loan drawdown and repayment, and intra-group cash pooling also form cycles."]
  },
  "data_flags": {"involves_real_entities": false, "synthetic_activity": true, "datasets": ["nr_synthetic"]},
  "disclaimer_id": "standing-v1"
}
```

## The typology catalog file

`detect/typologies/<slug>.yaml` is not a frozen contract, but alerts refer to it, so its shape is fixed here (5.4). `neonradar_detect.catalog.TypologyFile` validates it and `load_catalog()` reads the folder; an empty folder is an empty catalog. Follow-up for M1.9c: the API serves `GET /api/v1/typologies` from `load_catalog()`, so the api package needs `neonradar-detect` as a dependency; `api/pyproject.toml` lists only `neonradar-contracts` today. `uv run neonradar docs typology-index` renders the catalog index `docs/typologies/README.md` from it, and `--check` fails when that file is out of date.

```yaml
slug: circular_flow
name: Round-tripping or circular flows
version: 0.1.0
status: draft                 # draft | approved | retired  (only a typology researcher sets approved)
tier: core                    # core | extended | explainer_only
owner: "@TODO"                # typology researcher
approved_by: null
summary: >
  Funds leave an account, pass through other accounts and return to the originator
  or to a party under the same control.
doc: docs/typologies/circular-flow.md
citations: [fatf_egmont_tbml_indicators_2021, fatf_egmont_concealment_2018, ffiec_appendix_f, fatf_pml_2018]
graph_pattern: >
  A directed cycle of PAID relationships starting and ending at the same Account
  (or at two Accounts held by the same LegalEntity), with time-ordered hops,
  near-equal amounts and a short total duration.
parameters:
  min_hops: { default: 2, min: 2, max: 8 }
  max_hops: { default: 6, min: 2, max: 8 }
  max_window_days: { default: 14, min: 1, max: 90 }
  min_return_ratio: { default: 0.8, min: 0.0, max: 1.0 }
metrics: [cycle_length, sent_amount, returned_amount, currency, duration_hours, duration_days, return_ratio]
wording:
  headline_structural: "Funds returned to the originating account through {cycle_length} transfers within {duration_days} days"
  headline_synthetic: "Synthetic scenario: funds returned to the originating account through {cycle_length} transfers within {duration_days} days"
false_positives:
  - Refunds and payment reversals
  - Loan drawdown followed by repayment
  - Intra-group cash pooling and treasury sweeps
synthetic_support: high       # high | medium | low | none
generator_scenario: round_trip
detector: neonradar_detect.detectors.circular_flow   # null until implemented
```

Rules:

- A typology without a detector yet (most of them in Phase 1, and every `explainer_only` one) sets `detector: null` and may leave `parameters: {}`, `metrics: []`, `wording: null` and `generator_scenario: null`.
- Once `detector` is set, `parameters`, `metrics` and both `wording` templates are required.
- Every placeholder in a template is a listed metric: `{cycle_length}`, or with a Python format spec such as `{duration_hours:.0f}`. Positional (`{}`, `{0}`), attribute, index and conversion (`{x!r}`) placeholders fail.
- `headline_structural` never says "synthetic scenario" (7.1: only `synthetic_scenario` alerts may).
- `citations` holds at least one bibliography key (`scripts/check_citations.py`, M1.10a, checks that each exists in `docs/sources/bibliography.yaml`).
- `status` is `approved` only when `approved_by` is set. Only a typology researcher sets either.
- The file name is `<slug>.yaml`; `doc` is `docs/typologies/<slug with hyphens>.md`; `metrics` does not repeat a name; a numeric parameter's `default` lies within its `min` and `max`; `owner` and `approved_by` are GitHub handles, and `approved_by` is never `@TODO`.
- An `explainer_only` typology has `detector: null`.
- `headline_synthetic` starts with "Synthetic scenario"; `headline_structural` never says it (`SYNTHETIC_PHRASE`).
- NeonRadar's own words pass the wording lint: both templates, every `false_positives` entry, the slug (with `_` read as a space) and, for a typology with a detector, the name ("matches the graph pattern of <name>"). Names of typologies without a detector are explainer titles and may name the subject.
- Metrics are scalar: numbers, or strings that are codes such as a currency. Detectors never put names in metrics. A typology with several findings per subject emits one alert per finding (for example `sanctions_exposure`, Phase 3: one alert per sanctioned owner).

`neonradar_detect.wording.render_headline(typology, wording_class, metrics)` picks `headline_synthetic` for a `synthetic_scenario` alert and `headline_structural` otherwise, fills in the metrics (without a format spec: thousands separators and at most two decimals, so `120000.0` gives `120,000`), and refuses a result that is longer than 140 characters, matches a forbidden pattern, or says "synthetic scenario" for a `structural_pattern` alert; a format spec that does not fit the value (such as `.0f` on a currency) is a `WordingError` too.

## Wording rules (PHASE-1.md 7.1)

Entity-facing text describes structures and patterns. It never says that an entity laundered money, committed a crime, is a launderer, criminal, fraudster or guilty (guardrail G5).

### Disclaimers

The texts are verbatim from 7.1, one paragraph per file in `contracts/wording/`; `neonradar_contracts.wording.load_disclaimer(<id>)` returns them. The API serves all three in `MetaResponse.disclaimers`; an alert names `standing-v1`.

**Standing disclaimer** (`standing-v1.txt`). Shown near the top of the README, on every UI page that shows entities or alerts, and served by `GET /api/v1/meta`.

```text
NeonRadar is an educational, open-source tool that finds structural patterns in synthetic or public data. A pattern match is not evidence of money laundering, corruption or any other wrongdoing. There are legitimate reasons for almost every structure shown here, including holding companies, shared registered agents, professional directors, payment intermediaries and cash businesses. Where public data is used, many people and entities share the same or similar names, and source registers contain errors. Nothing here suggests or implies that any identifiable person or entity has broken the law. NeonRadar is not a certified compliance system and does not make anyone compliant with anything. If you find an error in NeonRadar, tell us and we will correct it; errors in source data can only be corrected by the source, and we will tell you where to report them.
```

**Synthetic demo notice** (`synthetic-demo-v1.txt`). Shown when every loaded dataset is synthetic, and in every screenshot and recording of the demo.

```text
Synthetic data. Every company, person, address, account and payment in this demonstration was generated by NeonRadar, and none of them exists. Patterns that resemble money laundering were planted on purpose to show how such structures look in a graph, next to ordinary activity that only looks similar. Detection results on synthetic data say nothing about how NeonRadar would perform on real data.
```

**Real data notice** (`real-data-v1.txt`). Shown whenever any loaded dataset has `synthetic: false`.

```text
This view includes records from public sources (company registers, the GLEIF index, the ICIJ Offshore Leaks Database, which is built from leaked files, and, where licensed, sanctions and PEP lists), listed with their licences on the Data sources page. Records about real people and companies are shown as their source published them and may be out of date. NeonRadar adds no allegations: any payment activity shown next to a real entity is synthetic background activity, and a pattern that touches a real entity is a structural observation only. Names can match the wrong person or company, so confirm identities with addresses, dates or official identifiers before drawing any conclusion. These records can include personal data, and whoever loads them is responsible for handling it lawfully.
```

### Vocabulary for entity-facing text

Alert headlines, summaries and steps, UI labels, and from Phase 4 the copilot's answers:

| Write | Never write |
|---|---|
| "structural pattern present", "matches the graph pattern of <typology name>" | "money laundering", "suspicious activity" |
| "funds returned to the originating account", "transfers", "payments" | "laundered funds", "dirty money" |
| "listed in <dataset> as sanctioned", "as a politically exposed person", "as a relative or close associate of a politically exposed person" (flags come from source data; no other source topics are shown next to entities) | "sanctioned criminal", "corrupt official" |
| "shares a registered address with 14 other companies" | "shell company", "front company" (about a specific entity) |
| "pattern strength" | "risk score", "suspicion score", "likelihood of laundering" |
| "synthetic scenario" (only when the alert's `wording_class` is `synthetic_scenario`: every evidence node, subject and evidence-account holder is synthetic) | "laundering case", "the launderer" |
| "linked to", "holds an account that received" | "accomplice", "mule", "fraudster" |

Explainers may use domain terms such as "shell company chains", because they describe a pattern, not an entity. The display name of any typology that has a detector must pass the lint, because alert and UI text say "matches the graph pattern of <name>".

### Forbidden patterns

`contracts/wording/forbidden-terms.txt`: one regular expression per line, matched case-insensitively after NFKC normalisation (so fullwidth or mathematical letters, such as a fullwidth "m" in "mule", cannot hide a term); lines starting with `#` are comments.

```text
# NeonRadar wording lint v1: entity-facing templates must not match any line below
\blaunder\w*
\blaundromat\w*
\bcriminal\w*
\bcrimes?\b
\bguilty\b
\bfraud\w*
\bsuspic\w*
\bsuspect\w*
\billicit\w*
\billegal\w*
\bdirty\s+money\b
\bcorrupt\w*
\bbrib\w*
\bterroris\w*
\bmules?\b
\bshell\s+compan\w*
\bfront\s+compan\w*
\bconceal\w*
\bevad\w*
\bevasion\b
\brisk[\s-]+scor\w*
\baccomplice\w*
\bwrongdo\w*
```

The lint applies to NeonRadar's own entity-facing wording: typology `wording` templates, string literals in `detect/src/**/wording.py`, rendered alert text (headline, summary and steps, with entity captions and account numbers masked out, because names are source data, not NeonRadar's wording), and from Phase 4 the copilot's answer templates. It does not apply to the disclaimers, typology names and explainers, the glossary, case notes or other documentation, which discuss money laundering as a subject. Phase 5 adds Arabic equivalents when the UI is translated.

Where it runs:

- `Alert` rejects a headline, a false-positive note, a typology slug or a subject role that matches a pattern; `render_headline` refuses to produce such a headline; `TypologyFile` rejects such templates, false positives, slugs and detector typology names.
- `neonradar_contracts.wording.find_forbidden(text, mask=[...])` checks rendered text such as summaries and steps: it NFKC-normalises the text and the masked source values, then blanks out each masked value only as a whole token, never inside a longer word (the detection runner, M1.9b).
- `scripts/check_wording.py` (in `make hygiene` and CI's `hygiene` job) lints the typology templates and the string literals of `detect/src/**/wording.py`.
- `contracts/tests/test_wording.py` checks every catalog template, every "Never write" phrase above against the patterns, every "Write" phrase as allowed, "matches the graph pattern of <name>" for every typology with a detector, and that the wording files are unchanged.

Changing a disclaimer or the forbidden patterns is a contract change: record it in [CHANGELOG.md](CHANGELOG.md), and after the freeze open a contract-change issue first.
