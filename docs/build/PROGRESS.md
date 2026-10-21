# Build progress

One row per milestone pull request. Status values: `todo`, `in-progress`, `pr-open`, `changes-requested`, `merged`, `blocked`. Each pull request edits only its own row; the format and rules are in [PHASE-1.md](PHASE-1.md) section 2.8.

| Milestone | Status | Branch | PR | Updated | Evidence | Notes and deviations |
|---|---|---|---|---|---|---|
| M1.0 | merged | p1/m1-0-operator-decisions | #1 | 2026-10-20 | gh pr view 1: MERGED | Operator decisions OD-1 to OD-9 recorded; project.yaml roles filled |
| M1.1 | merged | p1/m1-1-bootstrap | #2 | 2026-10-21 | acceptance: 6 of 6 commands pass; gh pr view 2: MERGED | .gitignore also ignores .DS_Store (operator request); review by the orchestrator after the PR opens (OD-4); no CI yet; security and conduct contacts still TODO; other deviations listed in PR #2 (Deviations from spec) |
| M1.2 | merged | p1/m1-2-agent-kit | #3 | 2026-10-21 | acceptance: 7 of 7 commands pass; test_hooks.sh: 172 passed, 0 failed; gh pr view 3: MERGED | Merge guard per OD-9 (one merge form; no merge inside a subagent); CLAUDE.md rule 8 per OD-8 plus two approved lines; ask rule on gh api dropped; guard gaps closed; built in a worktree; review by the orchestrator after the PR opens (OD-4), findings B1 and M1 to M5 fixed; no CI yet; size exception (905 counted lines); other deviations listed in PR #3 (Deviations from spec) |
| M1.3-1 | pr-open | p1/m1-3-workspace | #4 | 2026-10-21 | acceptance: uv lock and sync, make check, pre-commit run --all-files pass; test_hooks.sh: 172 passed, 0 failed | Split under 2.3 (771 counted lines as one PR): workspace, tooling, the carry-overs from PRs #2 and #3, ADR-0007 (proposed); ruff excludes Markdown; built in a worktree; review by the orchestrator after the PR opens (OD-4); no CI yet; other deviations listed in the PR |
| M1.3-2 | pr-open | p1/m1-3-2-cli | - | 2026-10-21 | acceptance: all 5 M1.3 commands pass (neonradar --version prints 0.1.0; doctor exits 0 with 3 WARN: .env, port 5173, ICU); test_hooks.sh: 172 passed, 0 failed | Second of two M1.3 pull requests (2.3): the neonradar command (--version, doctor); depends on M1.3-1 (#4); built in a worktree; review by the orchestrator after the PR opens (OD-4); no CI yet; other deviations listed in the PR |
| M1.4 | todo | - | - | 2026-10-21 | - | - |
| M1.5 | todo | - | - | 2026-10-21 | - | - |
| M1.6 | todo | - | - | 2026-10-21 | - | - |
| M1.7a | todo | - | - | 2026-10-21 | - | - |
| M1.7b | todo | - | - | 2026-10-21 | - | - |
| M1.7c | todo | - | - | 2026-10-21 | - | - |
| M1.7d | todo | - | - | 2026-10-21 | - | - |
| M1.8a | todo | - | - | 2026-10-21 | - | - |
| M1.8b | todo | - | - | 2026-10-21 | - | - |
| M1.8c | todo | - | - | 2026-10-21 | - | - |
| M1.8d | todo | - | - | 2026-10-21 | - | Gated by the OpenSanctions licence decision (access.opensanctions) |
| M1.8e | todo | - | - | 2026-10-21 | - | - |
| M1.9a | todo | - | - | 2026-10-21 | - | - |
| M1.9b | todo | - | - | 2026-10-21 | - | - |
| M1.9c | todo | - | - | 2026-10-21 | - | - |
| M1.9d | todo | - | - | 2026-10-21 | - | - |
| M1.9e | todo | - | - | 2026-10-21 | - | - |
| M1.10a | todo | - | - | 2026-10-21 | - | - |
| M1.10b-1 | todo | - | - | 2026-10-21 | - | - |
| M1.10b-2 | todo | - | - | 2026-10-21 | - | - |
| M1.10b-3 | todo | - | - | 2026-10-21 | - | - |
| M1.10c | todo | - | - | 2026-10-21 | - | - |
| M1.11a | todo | - | - | 2026-10-21 | - | - |
| M1.11b | todo | - | - | 2026-10-21 | - | - |
| M1.12 | todo | - | - | 2026-10-21 | - | - |
