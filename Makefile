# NeonRadar developer commands (docs/build/PHASE-1.md M1.3). Recipes are indented with a tab.
# Targets that a later milestone fills print "available after M1.x" and succeed.

.DEFAULT_GOAL := help
.PHONY: help setup fmt lint typecheck test test-int contracts contracts-check check hygiene \
	up down reset plugins smoke logs demo-mini e2e gate-1

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

test-int: ## integration tests (Neo4j through Testcontainers)
	uv run pytest -m integration

contracts: ## regenerate JSON Schemas and the OpenAPI snapshot
	@echo "available after M1.7"

contracts-check: ## contract tests and drift checks (M1.7c and M1.7d add the drift checks)
	uv run pytest -m contract

check: lint typecheck test contracts-check ## everything a pull request needs
	@if [ -f ui/package.json ]; then \
		npm run --prefix ui lint && npm run --prefix ui type-check && \
		npm run --prefix ui test:unit -- --run; \
	fi

hygiene: ## the pull request checks CI runs (size, fixtures, wording)
	@echo "available after M1.6"

plugins: ## download the pinned GDS jar once into data/cache/neo4j-plugins (uses the network)
	bash scripts/fetch_gds.sh

up: ## start Neo4j and wait until it is healthy (offline; run make plugins once before)
	@bash scripts/ensure_env.sh
	@bash scripts/fetch_gds.sh --check
	docker compose up -d --wait neo4j

down: ## stop Neo4j; the data volume is kept
	docker compose down

reset: ## delete the local Neo4j data and logs volumes (needs CONFIRM=yes)
	@if [ "$(CONFIRM)" != "yes" ]; then \
		echo "reset deletes the local Neo4j database. Run: make reset CONFIRM=yes" >&2; exit 1; \
	fi
	docker compose down -v

smoke: ## print the Neo4j, APOC and GDS versions; exit 1 if any is missing
	@echo "available after M1.4-2"

logs: ## follow the Neo4j logs
	docker compose logs --follow --tail=200 neo4j

demo-mini e2e: ## synthetic demo and the end-to-end test
	@echo "available after M1.9"

gate-1: ## Gate 1 check
	@echo "available after M1.12"
