# NeonRadar developer commands (docs/build/PHASE-1.md M1.3). Recipes are indented with a tab.
# Targets that a later milestone fills print "available after M1.x" and succeed.

.DEFAULT_GOAL := help
.PHONY: help setup fmt lint typecheck test test-int contracts contracts-check cypher-lint check \
	hygiene up down up-real down-real reset plugins smoke logs fixtures onboarding-check demo-data \
	demo-mini demo-dev e2e gate-1 spec-check spec-extract

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
	npm ci --prefix scripts/cypher-lint --ignore-scripts --silent && node scripts/cypher-lint/lint.mjs

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

down: ## stop Neo4j and, if running, the demo's API and UI; the data volume is kept
	docker compose --profile app down

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

# CONFIRM=yes counts only when typed on the command line (make reset CONFIRM=yes), never from the
# environment or .env, so that a stray export cannot delete a database.
CONFIRMED := $(if $(filter command line,$(origin CONFIRM)),$(CONFIRM))

# reset deletes the default instance's volumes by name (Compose project `neonradar`), never with
# `down -v`: the Compose documentation says -v removes the named volumes declared in compose.yaml,
# which include the real-data volume. Only `neonradar data purge --graph` deletes that one
# (PHASE-2.md M2.2); scripts/tests/test_make_reset.py checks that reset never names it.
DEFAULT_VOLUMES := neonradar_neo4j_data neonradar_neo4j_logs

reset: ## delete the default Neo4j instance's data and logs volumes (needs CONFIRM=yes on the command line)
	@if [ "$(CONFIRMED)" != "yes" ]; then \
		echo "reset deletes the local Neo4j database. Run: make reset CONFIRM=yes" >&2; exit 1; \
	fi
	@name="$${COMPOSE_PROJECT_NAME:-$$(sed -n 's/^COMPOSE_PROJECT_NAME=//p' .env 2>/dev/null | tail -n 1)}"; \
	if [ -n "$$name" ] && [ "$$name" != "neonradar" ]; then \
		echo "COMPOSE_PROJECT_NAME names another Compose project; reset knows only neonradar's volumes: unset it" >&2; \
		exit 1; fi
	docker compose --profile app down
	docker volume rm --force $(DEFAULT_VOLUMES)

smoke: ## print the Neo4j, APOC and GDS versions; exit 1 if any is missing
	uv run neonradar graph smoke

logs: ## follow the Neo4j logs
	docker compose logs --follow --tail=200 neo4j

fixtures: ## regenerate data/fixtures/demo-mini and er-bench (then check new names, OD-12)
	uv run neonradar synth demo-mini --seed 20261023 --out data/fixtures/demo-mini/
	uv run neonradar synth er-bench --size small --seed 20261026 --out data/fixtures/er-bench/

onboarding-check: ## Assignment 1: load the onboarding CSV, run docs/team/first-queries.md read-only
	uv run neonradar onboarding check

# The synthetic demo (PHASE-1.md M1.9e, docs/quickstart.md). The graph is always wiped before
# demo-mini is loaded, because a reload over an older demo could keep stale relationships; a
# graph holding anything but synthetic demo data (scripts/demo_guard.py) is refused unless
# CONFIRM=yes is given on the command line.
DEMO_FIXTURE := data/fixtures/demo-mini/
E2E_BASE_URL ?= http://localhost:8080
API_UP_PY := import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)

demo-data: ## into the Neo4j at NEO4J_URI: migrate, wipe, load demo-mini, detect (CONFIRM=yes: real data too)
	uv run neonradar graph migrate
	@if [ "$(CONFIRMED)" = "yes" ]; then echo "CONFIRM=yes: the graph is wiped even if it holds real data"; \
	else uv run python scripts/demo_guard.py; fi
	uv run neonradar graph wipe --yes
	uv run neonradar graph load $(DEMO_FIXTURE) --strict
	uv run neonradar detect run

demo-mini: ## the synthetic demo in Docker: Neo4j, API and UI on 127.0.0.1, then the URLs and the time
	@set -e; start=$$(date +%s); \
	if [ -z "$${NEO4J_PASSWORD:-}" ]; then bash scripts/ensure_env.sh; fi; \
	bash scripts/fetch_gds.sh; \
	docker compose up -d --wait neo4j; \
	NEO4J_URI="bolt://$$(docker compose port neo4j 7687)" $(MAKE) --no-print-directory demo-data; \
	echo "Building and starting the API and the UI (the first build takes a few minutes) ..."; \
	docker compose --profile app up -d --build --wait || { \
		echo "The API or the UI did not become healthy: docker compose --profile app logs api ui" >&2; \
		exit 1; }; \
	url() { echo "http://localhost:$$(docker compose port "$$1" "$$2" | sed 's/.*://')"; }; \
	elapsed=$$(( $$(date +%s) - start )); \
	echo; echo "NeonRadar demo-mini is running on synthetic data:"; \
	echo "  UI             $$(url ui 8080)"; \
	echo "  API docs       $$(url api 8000)/docs"; \
	echo "  Neo4j Browser  $$(url neo4j 7474)"; \
	echo "Elapsed: $$elapsed s ($$((elapsed / 60)) min $$((elapsed % 60)) s). Stop it with 'make down'."

demo-dev: ## the synthetic demo without Docker (devcontainer, Codespaces): API and Vite dev server
	@$(MAKE) --no-print-directory demo-data
	@uv run neonradar api serve & api=$$!; \
	trap 'kill $$api 2>/dev/null' EXIT INT TERM; \
	up=no; for i in $$(seq 60); do \
		kill -0 $$api 2>/dev/null || break; \
		if uv run --no-project python -c "$(API_UP_PY)" 2>/dev/null; then up=yes; break; fi; \
		sleep 1; \
	done; \
	if [ "$$up" != yes ]; then \
		echo "The API did not answer on http://127.0.0.1:8000 (see its output above)" >&2; exit 1; \
	fi; \
	echo; echo "NeonRadar demo-mini (synthetic data), Ctrl-C stops both servers:"; \
	echo "  UI        http://localhost:5173 (if 5173 is taken, the port Vite prints below)"; \
	echo "  API docs  http://localhost:8000/docs"; \
	echo "  Neo4j     $${NEO4J_URI:-bolt://localhost:7687}"; \
	npm run --prefix ui dev

e2e: ## the end-to-end test (Playwright, Chromium) against a running demo; E2E_BASE_URL=<url>
	E2E_BASE_URL='$(E2E_BASE_URL)' npm run --prefix ui test:e2e

# PHASE-4.md 2.10: the code book and the deviations file follow the milestone id (M3.x or M4.x)
spec-book = $(if $(filter M4.%,$(M)),docs/build/PHASE-4-CODE.md,docs/build/PHASE-3-CODE.md)
spec-devs = $(if $(filter M4.%,$(M)),docs/build/phase-4-deviations.json,docs/build/phase-3-deviations.json)

spec-check: ## prove the verbatim files of milestone M (M=M3.x or M4.x; PHASE-4.md 2.10)
	@if [ -z "$(M)" ]; then echo "usage: make spec-check M=M4.x" >&2; exit 2; fi
	uv run python scripts/spec_extract.py check --milestone $(M) --book $(spec-book) --deviations $(spec-devs)

spec-extract: ## copy the verbatim files of milestone M (reference files to REF)
	@if [ -z "$(M)" ]; then echo "usage: make spec-extract M=M4.x [REF=/tmp/m4x-reference]" >&2; exit 2; fi
	uv run python scripts/spec_extract.py extract --milestone $(M) --book $(spec-book) --deviations $(spec-devs) $(if $(REF),--reference $(REF),)

gate-1: ## Gate 1 evidence, GC-01 to GC-17 (GATE_ARGS=--report-only or --offline)
	uv run neonradar gate check --phase 1 $(GATE_ARGS)
