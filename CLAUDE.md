# NeonRadar

Open-source, local-first graph investigation toolkit for anti-money-laundering and
anti-corruption work. Python 3.14 (uv workspace), Neo4j 5.26 LTS Community with APOC and
GDS, FastAPI, Vue 3. Licence Apache-2.0. The build spec for the current phase is
docs/build/PHASE-<n>.md; project facts are in docs/build/project.yaml.
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
  [slug]})`; `model.make_entity` output has no `datasets`; CompositeEntity is gone; Payment
  dates lose their timezone, so write UTC without an offset.
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
