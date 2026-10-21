# NeonRadar developer commands (docs/build/PHASE-1.md M1.3). Recipes are indented with a tab.
# Targets that a later milestone fills print "available after M1.x" and succeed.

.DEFAULT_GOAL := help
.PHONY: help setup fmt lint typecheck test test-int contracts contracts-check cypher-lint check \
	hygiene up down up-real down-real reset plugins smoke logs fixtures onboarding-check demo-mini \
	e2e gate-1

help: ## list the targets
	@grep -E '^[a-z0-9 -]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-26s %s\n", $$1, $$2}'

setup: ## install everything: Python packages, pre-commit hooks, .env and, once ui/ exists, npm
	@bash scripts/ensure_env.sh
	uv sync --all-packages
	uv run pre-commit install
	@if [ -f ui/package.json ]; then npm ci --prefix ui; fi

fmt: ## format and fix Python code
	uv run ruff format .
	uv run ruff check --fix .

lint: ## check Python lint and formatting
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## mypy strict over the package sources
	uv run mypy

test: ## unit tests (no integration, network or e2e tests)
	uv run pytest

test-int: ## integration tests (Neo4j through Testcontainers, with the GDS jar from make plugins)
	@bash scripts/fetch_gds.sh --check
	uv run pytest -m integration

contracts: ## regenerate JSON Schemas and the OpenAPI snapshot
	uv run neonradar contracts export

contracts-check: ## contract tests and drift checks (models against the committed generated files)
	uv run pytest -m contract
	uv run neonradar contracts check

cypher-lint: ## lint every .cypher file under graph/, detect/ and api/ with Cypher 5 rules
	npm ci --prefix scripts/cypher-lint --silent && node scripts/cypher-lint/lint.mjs

check: lint typecheck test contracts-check cypher-lint ## everything a pull request needs
	@if [ -f ui/package.json ]; then \
		npm run --prefix ui lint && npm run --prefix ui type-check && \
		npm run --prefix ui test:unit -- --run; \
	fi

# Labels come from LABELS=a,b, else from the branch's pull request, else none; the title comes
# from TITLE=, else from the pull request, else the title check is skipped.
HYGIENE_PY := uv run --no-project python
hygiene: ## the pull request checks CI runs (title, size, contract paths, fixtures, wording, citations)
	@git fetch --quiet origin main || echo "hygiene: could not fetch origin/main; using the local copy"
	@labels='$(LABELS)'; title='$(TITLE)'; status=0; \
	if [ -z "$$labels" ]; then \
		labels="$$(gh pr view --json labels --jq '[.labels[].name] | join(",")' 2>/dev/null || true)"; \
	fi; \
	if [ -z "$$title" ]; then title="$$(gh pr view --json title --jq .title 2>/dev/null || true)"; fi; \
	echo "hygiene: labels: $${labels:-none}"; \
	if [ -n "$$title" ]; then $(HYGIENE_PY) scripts/check_pr_title.py "$$title" || status=1; \
	else echo "check_pr_title: skipped: no pull request yet (pass TITLE='type(scope): summary')"; fi; \
	$(HYGIENE_PY) scripts/check_pr_size.py --base origin/main --labels "$$labels" || status=1; \
	$(HYGIENE_PY) scripts/check_contract_paths.py --base origin/main --labels "$$labels" || status=1; \
	$(HYGIENE_PY) scripts/check_fixtures.py || status=1; \
	$(HYGIENE_PY) scripts/check_wording.py || status=1; \
	uv run python scripts/check_citations.py docs/ detect/typologies/ README.md || status=1; \
	exit $$status

plugins: ## once, with network: pull the Neo4j image and fetch the pinned GDS jar
	@bash scripts/ensure_env.sh
	docker compose pull neo4j
	bash scripts/fetch_gds.sh

up: ## start Neo4j and wait until it is healthy (offline once make plugins has run)
	@bash scripts/ensure_env.sh
	@bash scripts/fetch_gds.sh --check
	@image="$$(docker compose config --images neo4j)" || exit 1; \
	docker image inspect "$$image" >/dev/null 2>&1 || { \
		echo "The Neo4j image $$image is missing. Run 'make plugins' once, then 'make up'." >&2; \
		exit 1; }
	docker compose up -d --wait --pull never neo4j

down: ## stop Neo4j; the data volume is kept
	docker compose down

# The real-data instance (PHASE-2.md 4.1, M2.0): approved machines only, never for synthetic work.
# Deleting its data is `neonradar data purge --graph` (M2.2), which removes its volume.
up-real: ## start the real-data instance neo4j-real (approved machines only, docs/data/real-data-machines.md)
	@bash scripts/fetch_gds.sh --check
	@if [ -z "$${NEO4J_REAL_PASSWORD:-}" ] && ! grep -q '^NEO4J_REAL_PASSWORD=.\{8,\}' .env 2>/dev/null; then \
		echo "Set NEO4J_REAL_PASSWORD (at least 8 characters) in .env first; see docs/data/real-data-handling.md." >&2; \
		exit 1; fi
	@image="$$(docker compose --profile real config --images neo4j-real)" || exit 1; \
	docker image inspect "$$image" >/dev/null 2>&1 || { \
		echo "The Neo4j image $$image is missing. Run 'make plugins' once, then 'make up-real'." >&2; \
		exit 1; }
	docker compose --profile real up -d --wait --pull never neo4j-real

down-real: ## stop the real-data instance; its volume (the real graph) is kept
	docker compose --profile real stop neo4j-real

reset: ## delete the local Neo4j data and logs volumes (needs CONFIRM=yes)
	@if [ "$(CONFIRM)" != "yes" ]; then \
		echo "reset deletes the local Neo4j database. Run: make reset CONFIRM=yes" >&2; exit 1; \
	fi
	docker compose down -v

smoke: ## print the Neo4j, APOC and GDS versions; exit 1 if any is missing
	uv run neonradar graph smoke

logs: ## follow the Neo4j logs
	docker compose logs --follow --tail=200 neo4j

fixtures: ## regenerate data/fixtures/demo-mini (then check new names against Companies House, OD-12)
	uv run neonradar synth demo-mini --seed 20261023 --out data/fixtures/demo-mini/

onboarding-check: ## Assignment 1: load the onboarding CSV, run docs/team/first-queries.md read-only
	uv run neonradar onboarding check

demo-mini e2e: ## synthetic demo and the end-to-end test
	@echo "available after M1.9"

gate-1: ## Gate 1 evidence, GC-01 to GC-17 (GATE_ARGS=--report-only or --offline)
	uv run neonradar gate check --phase 1 $(GATE_ARGS)
