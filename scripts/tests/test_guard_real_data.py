"""Tests for .claude/hooks/guard_real_data.py (PHASE-2.md M2.0, PHASE-3.md M3.0,
PHASE-4.md M4.0)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_real_data.py"
SLS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/"
EU = "https://webgate.ec.europa.eu/fsd/fsf/public/"
CH = "https://find-and-update.company-information.service.gov.uk/"
GLEIF = "https://goldencopy.gleif.org/"

ALLOW = [
    "ls data/cache/real/sources",
    "du -sh data/cache/real",
    "du -sh data/cache/*",
    "ls data/fixtures/*/x",
    "cat data/fixtures/er-bench/*.csv",
    "uv run neonradar data status --profile uk-tiny",
    "uv run --no-sync neonradar er run --profile uk-tiny",
    "make load PROFILE=uk-tiny",
    "rm -rf data/cache/real/records/uk-tiny",
    "cat data/cache/reports/uk-tiny/er-run-20261102T091500.json",
    "cat data/cache/synthetic/resolution/demo/er-20261102T091500-3b7e/canonical.csv",
    "find data/cache/real -name '*.json' | wc -l",
    "wc -l data/cache/real/records/uk-tiny/*/*.ftm.jsonl",
    'git commit -m "docs: explain the data/cache/real layout"',
    "git commit -m \"$(cat <<'EOF'\nfeat(ingest): write records\n\n"
    'Records go to data/cache/real/records.\nEOF\n)"',
    "cat > docs/data/real-data-handling.md <<'EOF'\nReal data lives in data/cache/real/ only.\nEOF",
    'grep -rn "def load" graph/src',
    'rg "def load"',
    'git grep -n "data/cache/real"',
    "git check-ignore -v data/cache/real/x.json",
    "git log --oneline -3 && git diff --stat",
    'gh pr create --title "x" --body "outputs stay in data/cache/real"',
    "python3 -c 'print(1)'",
    "uv run pytest -m integration graph/tests/",
    "tar czf /tmp/docs.tgz docs/",
    "ls -la data/cache/",
    "stat data/cache/real/decisions.jsonl && echo ok",
    "cd docs && ls",
    "cd data/fixtures && ls",
    "cd graph && ls ../docs",
    "pushd docs && ls && popd",
    "make up-real",
    "docker compose --profile real up -d --wait neo4j-real",
    "docker compose --profile real stop neo4j-real",
    "docker compose ps neo4j-real",
    "uv run neonradar graph verify --real",
    "NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688 uv run neonradar graph load --profile uk-tiny",
    'git commit -m "feat(dev): add the neo4j-real service on port 7688"',
    'git commit -m "feat(resolve): add neonradar er label and er review"',
    'gh pr create --title "M2.10c" --body "er label refuses without a terminal"',
    "curl -s http://127.0.0.1:8000/api/v1/health",
    'docker compose exec neo4j cypher-shell -u neo4j -p x "MATCH (p:Person) RETURN p.names"',
    "curl -sO https://assets.publishing.service.gov.uk/media/x/SanctionsListSchema-4.33.3.xsd",
    "curl -fsSL https://raw.githubusercontent.com/opensanctions/rigour/v2.5.0/README.md",
    "git grep -n neo4j-real",
    "docker compose --profile real config --services",
    "uv run neonradar er sample --profile demo --run latest --seed 7",
    # PHASE-3.md M3.0: development evaluations stay allowed
    "uv run neonradar eval run --split dev",
    "uv run neonradar eval check",
    "uv run neonradar eval run --split dev --seeds 1-5",
    # the holdout folder's name in text and read-only git is fine; contents never are
    'git grep -n "data/cache/holdout"',
    'git commit -m "docs: the holdout run writes to data/cache/holdout"',
    'gh pr create --title "M3.6" --body "the holdout run writes to data/cache/holdout"',
    "ls data/cache/hold*",  # a glob lists names, never contents, as for data/cache/real
    # PHASE-4.md M4.0: the committed sets, the empty digest and the router's tests stay allowed
    "uv run neonradar copilot bench",
    "uv run neonradar copilot bench --set refusals",
    'uv run neonradar copilot model-check --digest ""',
    "uv run pytest copilot/tests/test_llm.py",
    # text about the model and the profile, a router switched off, and other Compose services
    'git commit -m "docs(copilot): explain ollama serve and --profile llm"',
    'grep -rn "ollama" docs/copilot',
    "uv run neonradar copilot ask --no-model-router 'Who owns Calvane Holdings Ltd?'",
    "NR_COPILOT_MODEL_ROUTER=false uv run neonradar api serve",
    "docker compose --profile app up -d api",
    "docker compose stop ollama",
    'uv run neonradar copilot model-check --digest=""',
]

BLOCK = [
    "cat data/cache/real/records/uk-tiny/gb_companies_house/x.ftm.jsonl",
    "head -n 5 data/cache/spikes/companies_house/out.ftm.jsonl",
    "zcat data/cache/real/sources/gb_companies_house/companies/2026-10-01/BasicCompanyData.zip",
    "python3 -c \"import json; print(open('data/cache/real/x.json').read())\"",
    "uv run python -c \"print(open('data/cache/real/x').read())\"",
    "jq . data/cache/real/resolution/uk-sample/er-x/candidates.jsonl",
    "duckdb -c \"select * from 'data/cache/real/x.parquet'\"",
    "strings data/cache/real/duckdb-tmp/er-x/duckdb_temp_storage-0.tmp",
    "cp data/cache/real/labels/er-x/a.jsonl /tmp/",
    "tar czf /tmp/x.tgz data/cache/real",
    "tar czf /tmp/repo.tgz .",
    'grep -r "SMITH" .',
    "grep -rn SMITH data/",
    "grep -r SMITH",
    "rg --no-ignore SMITH",
    "cd data/cache/real && ls",
    "cd data/cache && cat real/x",
    "cd data && ls",
    r"find data/cache/real -name '*.jsonl' -exec cat {} \;",
    "find data/cache/real -type f | xargs head",
    'ls data/cache/real | while read f; do cat "data/cache/real/$f"; done',
    "less data/cache/spikes/x",
    "python3 - <<'EOF'\nprint(open('data/cache/real/x').read())\nEOF",
    "cat data/cache/*/records/x",
    "cat data/*/real/x",
    "cat data/cache/**/x.json",
    "head data/cache/re*/records/a",
    "cat ./data/cache/real/x",
    "cat ../../../data/cache/real/x",
    "cat ~/neonradar-worktree/data/cache/real/x",
    "cat /home/dev/neonradar-wt2/data/cache/spikes/x",
    "git add -f data/cache/real/x.json",
    "gh gist create data/cache/real/x",
    "gh issue create --title t --body-file data/cache/real/x",
    "sort data/cache/real/x | head",
    "cp -r . /tmp/repo",
    "git grep --no-index SMITH data/cache/real",
    "git grep --no-index SMITH",
    "git grep --untracked SMITH",
    "git grep --no-exclude-standard --untracked SMITH",
    "git diff --no-index /dev/null data/cache/real/x",
    "git commit -F data/cache/real/x",
    "git grep -f data/cache/real/names.txt",
    'rm -rf data/cache/real/x && git commit -m "purge"',
    "cd data/fixtures && cat ../cache/real/x.jsonl",
    "cd scripts && head ../data/cache/re*/records/a",
    "pushd scripts && cat ../data/cache/sp*/x && popd",
    'docker compose exec neo4j-real cypher-shell "MATCH (n) RETURN n LIMIT 1"',
    "docker compose --profile real logs neo4j-real",
    "docker volume rm neonradar_neo4j-real-data",
    "curl -s 'http://127.0.0.1:8001/api/v1/search?q=smith'",
    "curl -s http://localhost:7475/browser/",
    'cypher-shell -a bolt://127.0.0.1:7688 "MATCH (n) RETURN count(n)"',
    'echo "MATCH (p:Person) RETURN p.names" | cypher-shell -a neo4j://localhost:7688',
    "bash -c \"cypher-shell -a bolt://localhost:7688 'MATCH (n) RETURN n'\"",
    'cypher-shell -d realdata "MATCH (n) RETURN n LIMIT 1"',
    "NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688 python3 scripts/peek.py",
    "printenv NEO4J_REAL_PASSWORD",
    "uv run python -c \"from neo4j import GraphDatabase; GraphDatabase.driver('bolt://x:7688')\"",
    "python3 - <<'EOF'\nfrom neo4j import GraphDatabase\n"
    'GraphDatabase.driver("bolt://localhost:7688")\nEOF',
    "uv run neonradar er label --profile uk-sample",
    "uv run neonradar er review --profile demo",
    "uv run neonradar api serve --real",
    "neonradar er label --profile demo --run latest",
    "uv run python -m neonradar_cli er review --profile demo",
    'bash -c "uv run neonradar er label --profile uk-sample"',
    'script -qc "uv run neonradar er label" /dev/null',
    "unbuffer uv run neonradar er review --profile demo",
    "expect -c 'spawn uv run neonradar er label'",
    "faketty uv run neonradar er review",
    "curl -s https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml | head -50",
    "wget -qO- https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile.zip | zcat | head",
    "curl -s https://api.company-information.service.gov.uk/company/01800000/officers",
    "curl -s sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
    "docker compose --profile real config",
    "docker inspect $(docker ps -q)",
    # PHASE-3.md M3.0: the holdout run is human-only and its folder is closed (G11)
    "uv run neonradar eval run --split test",
    "neonradar eval run --split=test --engine neo4j",
    "uv run neonradar eval run --seeds 3 --split test",
    "ls data/cache/holdout",
    "cat data/cache/holdout/eval-test-x/report.md",
    "cd data/cache/holdout && ls",
    "uv run neonradar eval report data/cache/holdout/eval-test-x",
    "rm -rf data/cache/holdout/eval-test-x",
    "cat data/cache/hold*/x",
    "python3 - <<'EOF'\nprint(open('data/cache/holdout/x').read())\nEOF",
    "NR_X=1 uv run neonradar --verbose eval run --split  test",
    'bash -c "uv run neonradar eval run --split test"',
    "uv run python -m neonradar_cli eval run --split='test'",
    # file systems that ignore case (macOS, Windows): the folders in any letter case
    "cat data/cache/REAL/x.json",
    "head -n 5 data/cache/Real/records/x.ftm.jsonl",
    "less data/cache/SPIKES/companies_house/out.json",
    "cat Data/Cache/Real/x",
    "cat data/cache/HOLDOUT/eval-test-x/report.md",
    "ls data/cache/HoldOut",
    "cd DATA/cache && ls",
    "grep -rn SMITH DATA/",
    "python3 - <<'EOF'\nprint(open('data/cache/Real/x').read())\nEOF",
    "uv run NeonRadar er label --profile demo",
    # PHASE-4.md M4.0: the held-out questions and the model are human-only (G15, G16)
    "uv run neonradar copilot bench --file h1.yaml",
    "neonradar copilot bench --engine neo4j --file=/tmp/h1.yaml",
    "ls data/cache/heldout",
    'uv run neonradar copilot ask --model-router "help"',
    "uv run neonradar copilot model-check",
    "uv run neonradar copilot model-check --digest 0f3c",
    "ollama pull qwen3:4b-instruct-2507-q4_K_M",
    "ollama serve",
    "docker compose --profile llm up -d",
    # the same, written another way
    "cat data/cache/heldout/h1.yaml",
    "cat data/cache/HeldOut/h1.yaml",
    'uv run neonradar copilot model-check --digest "" --digest 0f3c',
    "OLLAMA_NO_CLOUD=1 nohup ollama serve",
    "/usr/local/bin/ollama run qwen3:4b-instruct-2507-q4_K_M",
    "uv run ollama serve",
    "uv run -- ollama pull qwen3:4b-instruct-2507-q4_K_M",
    'bash -c "ollama pull qwen3:8b-q4_K_M"',
    "docker compose --profile=llm up -d",
    "COMPOSE_PROFILES=llm docker compose up -d",
    "docker compose up -d ollama",
    "NR_COPILOT_MODEL_ROUTER=true uv run neonradar api serve",
    "uv run NeonRadar copilot bench --FILE h1.yaml",
    "python3 - <<'EOF'\nimport os\nos.system('ollama serve')\nEOF",
]

TOOL_ALLOW = [
    ("Read", {"file_path": "{project}/docs/data/real-data-handling.md"}),
    ("Read", {"file_path": "{project}/data/cache/reports/uk-tiny/er-run-20261102T091500.json"}),
    ("Read", {"file_path": "{project}/data/cache/synthetic/resolution/demo/er-1/canonical.csv"}),
    ("Grep", {"pattern": "def load", "path": "graph/src"}),
    ("Grep", {"pattern": "data/cache/real"}),
    ("Grep", {"pattern": "SMITH", "path": "{project}"}),
    ("Glob", {"pattern": "**/*.py"}),
    ("Glob", {"pattern": "data/fixtures/**/*.jsonl"}),
    ("WebFetch", {"url": "https://assets.publishing.service.gov.uk/media/x/SanctionsList.xsd"}),
    ("WebFetch", {"url": SLS + "XML.xsd"}),
    ("WebFetch", {"url": "https://members-api.parliament.uk/swagger/v1/swagger.json"}),
    ("WebFetch", {"url": "https://download.companieshouse.gov.uk/en_output.html"}),
    ("WebFetch", {"url": GLEIF + "api/v2/golden-copies/publishes/latest"}),
    ("WebFetch", {"url": "https://ofac.treasury.gov/faqs/topic/1521"}),
    ("WebFetch", {"url": "https://offshoreleaks.icij.org/pages/database"}),
    ("WebFetch", {"url": "https://www.opensanctions.org/datasets/gb_fcdo_sanctions/"}),
    ("WebFetch", {"url": EU + "rss"}),
    ("mcp__neo4j__read-cypher", {"query": "MATCH (p:Person) RETURN p.names LIMIT 3"}),
    ("mcp__neo4j__get-schema", {}),
    ("Read", {"file_path": "{project}/data/cache/synthetic/eval/eval-dev-x/report.md"}),
    ("Grep", {"pattern": "data/cache/holdout", "path": "docs"}),
    ("Read", {"file_path": "{project}/copilot/bench/refusals.yaml"}),
]

TOOL_BLOCK = [
    ("Read", {"file_path": "{project}/data/cache/real/records/uk-tiny/x.ftm.jsonl"}),
    ("Read", {"file_path": "{project}/data/cache/spikes/companies_house/out.json"}),
    ("Read", {"file_path": "/home/dev/neonradar-wt2/data/cache/real/x.jsonl"}),
    ("Read", {"file_path": "{project}/data/fixtures/../cache/real/x.jsonl"}),
    ("Grep", {"pattern": "SMITH", "path": "data/cache/real"}),
    ("Grep", {"pattern": "SMITH", "path": "{project}/data/cache/spikes"}),
    ("Grep", {"pattern": "SMITH", "path": "data/cache"}),
    ("Grep", {"pattern": "SMITH", "path": "data"}),
    ("Grep", {"pattern": "SMITH", "glob": "data/cache/real/**"}),
    ("Glob", {"pattern": "data/cache/real/**/*.jsonl"}),
    ("Glob", {"pattern": "data/cache/*/records/*"}),
    ("Glob", {"pattern": "**/*.jsonl", "path": "{project}/data/cache"}),
    ("Glob", {"pattern": "*", "path": "{project}/data/cache/spikes"}),
    ("WebFetch", {"url": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"}),
    ("WebFetch", {"url": SLS + "SDN_ADVANCED.XML"}),
    ("WebFetch", {"url": "https://www.treasury.gov/ofac/downloads/sdn.xml"}),
    ("WebFetch", {"url": "https://scsanctions.un.org/resources/xml/en/consolidated.xml"}),
    ("WebFetch", {"url": EU + "files/xmlFullSanctionsList_1_1/content?token=x"}),
    ("WebFetch", {"url": "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile.zip"}),
    ("WebFetch", {"url": CH + "company/01800000/officers"}),
    (
        "WebFetch",
        {"url": "https://api.company-information.service.gov.uk/company/01800000/officers"},
    ),
    ("WebFetch", {"url": GLEIF + "storage/golden-copy-files/2026/10/17/x.csv.zip"}),
    ("WebFetch", {"url": GLEIF + "api/v2/golden-copies/publishes/lei2/latest.csv"}),
    (
        "WebFetch",
        {"url": "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"},
    ),
    ("WebFetch", {"url": "https://offshoreleaks.icij.org/nodes/12000001"}),
    (
        "WebFetch",
        {"url": "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"},
    ),
    ("WebFetch", {"url": "https://members-api.parliament.uk/api/Members/Search?House=Commons"}),
    ("Read", {"file_path": "{project}/data/cache/holdout/eval-test-x/report.md"}),
    ("Grep", {"pattern": "x", "path": "data/cache/holdout"}),
    ("Glob", {"pattern": "data/cache/holdout/**"}),
    ("Glob", {"pattern": "**/*.md", "path": "{project}/data/cache/holdout"}),
    ("Read", {"file_path": "{project}/data/cache/REAL/records/x.jsonl"}),
    ("Read", {"file_path": "{project}/Data/Cache/Holdout/eval-test-x/report.md"}),
    ("Grep", {"pattern": "SMITH", "path": "data/cache/Spikes"}),
    ("Glob", {"pattern": "data/cache/REAL/**/*.jsonl"}),
    ("Glob", {"pattern": "*", "path": "{project}/DATA/cache/holdout"}),
    ("Read", {"file_path": "{project}/data/cache/heldout/h1.yaml"}),
    ("Grep", {"pattern": "x", "path": "data/cache/heldout"}),
    ("Glob", {"pattern": "data/cache/held*/**"}),
]


def run(tmp_path, tool, tool_input, cwd=None, mcp_json=None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    if mcp_json is not None:
        (project / ".mcp.json").write_text(mcp_json)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd or project)}
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result.returncode


def filled(tmp_path, tool_input):
    project = str(tmp_path / "project")
    return {k: v.replace("{project}", project) for k, v in tool_input.items()}


@pytest.mark.parametrize("command", ALLOW)
def test_allowed(tmp_path, command):
    assert run(tmp_path, "Bash", {"command": command}) == 0


@pytest.mark.parametrize("command", BLOCK)
def test_blocked(tmp_path, command):
    assert run(tmp_path, "Bash", {"command": command}) == 2


@pytest.mark.parametrize(("tool", "tool_input"), TOOL_ALLOW)
def test_tools_allowed(tmp_path, tool, tool_input):
    assert run(tmp_path, tool, filled(tmp_path, tool_input)) == 0


@pytest.mark.parametrize(("tool", "tool_input"), TOOL_BLOCK)
def test_tools_blocked(tmp_path, tool, tool_input):
    assert run(tmp_path, tool, filled(tmp_path, tool_input)) == 2


def test_cwd_inside_real_data(tmp_path):
    inside = tmp_path / "project" / "data" / "cache" / "real" / "records"
    assert run(tmp_path, "Bash", {"command": "cat x.json"}, cwd=inside) == 2
    assert run(tmp_path, "Bash", {"command": "ls"}, cwd=inside) == 0


def test_cwd_inside_the_holdout_folder(tmp_path):
    inside = tmp_path / "project" / "data" / "cache" / "holdout" / "eval-test-x"
    assert run(tmp_path, "Bash", {"command": "cat report.md"}, cwd=inside) == 2
    assert run(tmp_path, "Bash", {"command": "ls"}, cwd=inside) == 2
    assert run(tmp_path, "Bash", {"command": "git status"}, cwd=inside) == 0


def test_cwd_inside_the_held_out_folder(tmp_path):
    inside = tmp_path / "project" / "data" / "cache" / "heldout"
    assert run(tmp_path, "Bash", {"command": "cat h1.yaml"}, cwd=inside) == 2
    assert run(tmp_path, "Bash", {"command": "ls"}, cwd=inside) == 2


def test_mcp_server_must_use_the_default_instance(tmp_path):
    query = {"query": "MATCH (p:Person) RETURN p.names LIMIT 3"}
    default = '{"mcpServers": {"neo4j": {"env": {"NEO4J_MCP_URI": "bolt://localhost:7687"}}}}'
    real = '{"mcpServers": {"neo4j": {"env": {"NEO4J_MCP_URI": "bolt://localhost:7688"}}}}'
    assert run(tmp_path, "mcp__neo4j__read-cypher", query, mcp_json=default) == 0
    assert run(tmp_path, "mcp__neo4j__read-cypher", query, mcp_json=real) == 2
