# NeonRadar

Open-source, local-first graph investigation toolkit for anti-money-laundering and
anti-corruption work. Python 3.14 (uv workspace), Neo4j 5.26 LTS Community with APOC and
GDS, FastAPI, Vue 3. Licence Apache-2.0. The build specs for the current phases are
docs/build/PHASE-2.md and docs/build/PHASE-3.md (PHASE-1.md section 5 still defines the
frozen contracts); project facts are in docs/build/project.yaml.
Operator decisions in docs/build/operator-decisions.md override the spec.

## Non-negotiable rules
1. Never label a real person or company as suspicious. Synthetic laundering scenarios run
   only among synthetic entities (ids start with `syn-`). Real registry entities may only
   receive synthetic background activity. Exceptions need an approved ADR (PHASE-1.md G1).
2. Commit code and synthetic fixtures only. Never commit bulk data, real personal data,
   API responses about real people, or any row derived from OpenSanctions.
3. Nothing phones home. No telemetry, analytics or outbound calls at runtime. Only explicit
   loader and spike commands use the network. Tests never use the network.
4. Every AML fact in docs cites a key from docs/sources/bibliography.yaml. You may draft
   typology definitions; never set `status: approved`.
5. Describe patterns, never accusations. Never write that an entity laundered money or is
   a launderer, criminal, fraudster or guilty. Use the wording templates (PHASE-1.md 7.1).
6. Secrets live in .env or GitHub secrets. Never print, log, commit or ask for them.
7. contracts/** and graph/schema/** are frozen once tag contracts-v1.0.0 exists. Changes
   need an approved contract-change issue (/contract-change).
8. Milestone builders never merge. During the initial build, only the orchestrating session
   the operator authorised merges, with `gh pr merge <n> --merge`, after the acceptance
   commands, an independent review and CI (from M1.6 on) pass; humans review merged work
   (docs/build/operator-decisions.md OD-2, OD-3, OD-8). Never push to main, force-push,
   delete remote branches or tags, or change repo settings (.claude/hooks/guard_git.py
   blocks these). Freezing contracts, approving typologies, accepting ADRs, licence
   decisions and anything written in a person's name stay with humans (OD-5). Update a
   branch with `git merge origin/main`.

## Commands
- `make setup`            install everything (uv sync, npm ci, pre-commit)
- `make check`            lint, types, unit tests, contract checks: run before every PR
- `make up` / `make down` start or stop Neo4j (Docker Compose); `make smoke` checks it;
  `make plugins` once first (downloads the pinned GDS jar; docs/architecture/local-stack.md)
- `make test-int`         integration tests (Neo4j via Testcontainers)
- `make contracts`        regenerate JSON Schemas and the OpenAPI snapshot
- `make demo-mini`        load the synthetic demo, run detection, start API and UI
- `make hygiene`          the pull request checks CI runs (size, fixtures, wording)
- `uv run neonradar --help`  the project command line

## Layout
contracts/ (C1-C4, frozen) · ingest/ · graph/ (graph/schema frozen) · detect/ · copilot/ ·
api/ · cli/ · ui/ · data/fixtures/ (synthetic only) · docs/ · scripts/ · .claude/
Each Python package: <dir>/src/neonradar_<dir>/, tests in <dir>/tests/, notes in <dir>/CLAUDE.md.

## Workflow
- One milestone per branch and PR: `/milestone <id>` runs the protocol in PHASE-<n>.md 2.2.
- Branch `p<phase>/<milestone>-<slug>`; Conventional Commits `type(scope): summary`.
- PR <= 400 changed lines of code, tests and config (PHASE-<n>.md 2.3; split otherwise).
- Prove it: run the milestone's acceptance commands; paste the evidence into the PR.
- Before opening a PR, ask the `reviewer` subagent to review the diff. During the
  orchestrated build, the orchestrating session runs this review after the PR opens (OD-4).
- If the spec and reality disagree: small and mechanical, adapt and record it under
  "Deviations from spec"; anything that changes behaviour, stop and ask.

## Conventions
- Python: typed (mypy strict), pydantic v2 models, typer CLIs, pytest markers `contract`,
  `integration`, `network`, `e2e`. No print in library code; use logging.
- Cypher: Neo4j 5.26, Cypher 5, forward-compatible subset (PHASE-1.md 5.2): parameters
  only, `CALL (x) { }`, `elementId()`, quantified paths `-[:PAID]->{2,6}`, bounded hops
  and LIMIT, `CALL { } IN TRANSACTIONS` for big writes, no apoc.periodic.iterate.
- Graph properties snake_case; record (FtM) properties camelCase. Ids `<prefix>-<rest>`.
- Frontend: Vue 3.5 `<script setup lang="ts">`, TypeScript ~6.0.3 (never 7), Pinia, Vue
  Router, Cytoscape.js, CSS logical properties (RTL-ready).

## Known traps (verified 16 Oct 2026)
- followthemoney 4.x: build records with `ValueEntity(model[schema], {"id": ..., "datasets":
  [slug]})`; `model.make_entity` output has no `datasets`; CompositeEntity is gone. Payment
  dates: FtM converts an offset to UTC but cuts a trailing `Z` to minutes (fails C1 R5), so
  pass `dt.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%S')`. Ids: `records.make_id`.
- `CALL { } IN TRANSACTIONS` needs an auto-commit `session.run()`, not `execute_query`.
- pydantic-settings reading `.env`: `extra="ignore"`.
- Splink 5, not 4: `db_api.register(df)` then `Linker(sdf, settings)`.
- graphdatascience 2.x is snake_case only; prefer `CALL gds.*` through the driver.
- neo4j driver 6: `execute_read` / `execute_write`; `read_transaction` is gone.
- testcontainers: `from testcontainers.community.neo4j import Neo4jContainer`.
- Community Edition: uniqueness constraints only (no existence, type or key constraints).
- httpx needs `follow_redirects=True` (OpenSanctions answers 307).
- The Neo4j image has wget and cypher-shell, not curl.
- Never add @neo4j-nvl (proprietary) or GPL packages (unidecode, pyarabic).
- Faker ar_SA surnames include real prominent families: use the denylist.

## Non-negotiable rules (Phase 2 additions)
9. No inferred flags. Flags and topics come only from a node's own source records. A
   listed record merges with an unlisted one or one listed for another reason, and a
   leaked (ICIJ) record with another source, only by a deterministic identifier rule whose
   records share an exact name key, or by a human decision that two reviewers or a senior
   reviewer made; otherwise it is a POSSIBLY_SAME_AS link, always described as "not
   confirmed" (PHASE-2.md G8, 7.1.4).
10. Never read real data. Real records live in data/cache/real/, data/cache/spikes/ and the
    neo4j-real instance (ports 7475 and 7688). Never open, print, grep, fetch (WebFetch,
    curl, wget) or query them; the default Neo4j instance, the API on port 8000, the UI and the Neo4j MCP server
    hold synthetic data only. Real-data commands print counts only. Reproduce failures on
    the demo profile or the ER benchmark (G9). guard_real_data.py and the deny rules
    enforce this.
11. Humans label. Never write, edit, pre-fill or infer labels or review decisions, never
    run er label, er review or api serve --real, and never tune thresholds, rules or models
    on evaluation labels (G10).

## Non-negotiable rules (Phase 3 additions)

- G11: never run `neonradar eval run --split test`, never choose holdout seeds, never generate
  or open a holdout world or anything under data/cache/holdout/; never edit a verbatim test,
  `eval/baselines/ci.json` or `eval/freeze.json` to make a check pass.
- G12 (R-REAL): no payment-based alert involves a real entity, and no alert names a real
  person as subject or in evidence; such findings are withheld and counted only.
- Verbatim files come from docs/build/PHASE-3-CODE.md through scripts/spec_extract.py.
- No scenario touches a base entity, and base people never get accounts or payments (G1).

## Commands (Phase 2 additions; each works once the milestone in brackets has merged)
- `make cypher-lint`              lint every .cypher file (Cypher 5 rules) [M2.0]
- `make up-real`, `make down-real` start or stop the real-data instance (approved machines) [M2.0]
- `uv run neonradar data status`  downloads, versions, ages, retention (counts only) [M2.2]
- `uv run neonradar er run --profile demo`   one resolution run (synthetic) [M2.10a]
- `uv run neonradar er bench --size small`   the ER benchmark with precision and recall [M2.10a]
- `uv run neonradar graph verify` graph invariants I1 to I14 [M2.11]
- `make load PROFILE=demo`        synthetic profile end to end: build, resolve, load, verify [M2.13]

## Commands (Phase 3 additions; each works once the milestone in brackets has merged)

- `uv run python scripts/spec_extract.py check --milestone M3.x` and `update --path FILE` (M3.0)
- `uv run neonradar synth world --profile synth-eval --seed 1` and `synth overlay` (M3.3)
- `uv run neonradar graph load --profile synth-eval --overlay latest` (M3.4)
- `uv run neonradar detect run --profile synth-eval` (M3.2; synthetic profiles from M3.3, real ones from M3.4)
- `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration"` (M3.2)
- `uv run neonradar eval check` and `uv run neonradar eval run --split dev --seeds 1-5` (M3.6)
- `make load PROFILE=synth-demo` (M3.7) and `make demo` (M3.8)

## Layout (Phase 2 additions)
keys/ (matching keys, pure functions), resolve/ (entity resolution), ingest/profiles/,
data/cache/real/ (real data: never read), data/cache/synthetic/ (synthetic runs: free to read),
data/cache/reports/ (counts-only summaries)

## Layout (Phase 3 additions)

- detect/src/neonradar_detect/: source.py (candidate steps), memsource.py (the oracle),
  neo4jsource.py and queries/ (one file per step), detectors/, evaluation/
- ingest/src/neonradar_ingest/synth/: generator v1 (world.py, overlay.py, scenarios/)
- eval/: seeds.yaml, baselines/ci.json, freeze.json

## Known traps (Phase 2, verified 18 Oct 2026)
- Splink 5 only: `sdf = db_api.register(table, ...)`, then `Linker(sdf, settings)`; results
  with `as_record_list()`; no `db_api=` on Linker, no `as_record_dict`, no `bf_` columns.
- NameComparison always adds term-frequency adjustment: build name comparisons from levels.
- An empty DuckDB list is not NULL: write NULL for every empty list in feature tables.
- DuckDB memory and threads go on `duckdb.connect(config=...)`; tests use one thread.
- XML: defusedxml only (ruff S314); compare tags without namespaces (OFAC changed its).
- OFAC needs a User-Agent; never store the UN redirect URL or log the EU token.
- Companies House bulk headers start with spaces; PSC bands: (25,50], (50,75), [75,100].
- `person_number` comes only from /company/{n}/officers; D3 uses its first 8 characters.
- GLEIF Level 2 is accounting consolidation: CONSOLIDATES, never OWNS.
- `CALL { } IN TRANSACTIONS` only through `session.run()`; Neo4j 5.26 has no ON ERROR RETRY.
- `from rigour.text.scripts import text_scripts`; never fuzzy country lookups; keys come
  from neonradar_keys only.

## Known traps (Phase 3, verified 18 Oct 2026)

- A Cypher 5 path pattern cannot compare a hop with the previous one: expand one hop per query.
- ORDER BY a C2 id before every LIMIT; durations do not compare; name :Entity in id lookups.
- GDS: stream only, concurrency 4, drop projections in finally; no graphdatascience client.
- Detector queries run as session.run(neo4j.Query(text, timeout)), never in execute_read.
- numpy streams change between numpy minor versions: a numpy bump must pass eval check.
- Generator payments are C1 lines (Ctx.payments); read one with Ctx.record(id).
