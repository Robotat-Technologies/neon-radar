# CI, quality gates and repository protection

Every pull request is checked the same way, mechanically, before anyone spends attention on it. This page says what each check does, how to run it on your machine, what protects `main` today, and what changes when the repository's GitHub plan allows more. It was written in M1.6 ([PHASE-1.md](PHASE-1.md), section 6, M1.6); the repository facts below were checked on 21 October 2026.

## The checks

| Workflow | Check (job id) | Runs on | What it does | Locally |
|---|---|---|---|---|
| `ci` | `python` | every pull request, every push to `main`, manual | Installs ICU headers, uv 0.13 (setup-uv reads `required-version` from `pyproject.toml`, so CI never jumps to 0.14 unannounced) and Python 3.14, then `uv sync --all-packages --locked`; `uv run pre-commit run --all-files` with `SKIP=gitleaks` (ruff check and format, `uv-lock`; the hook environments are cached by the hash of `.pre-commit-config.yaml`); `make lint typecheck test contracts-check` (ruff, mypy strict, the unit tests including the hygiene script tests, the contract suite once M1.7 fills it); `bash scripts/test_hooks.sh` (the agent guard hooks still block what they must); `generate_codeowners.py --check` (`.github/CODEOWNERS` matches `project.yaml`); `neonradar docs typology-index --check` (`docs/typologies/README.md` matches the typology catalog, M1.7c) | `make check`, `uv run pre-commit run --all-files`, `bash scripts/test_hooks.sh`, `uv run neonradar docs typology-index --check` |
| `ci` | `integration` | same | `uv run pytest -m "integration and not network"`: tests marked `integration` and not `network` (guardrail G3), against Neo4j `5.26.32-community` started by Testcontainers. Until M1.7b adds more, this is `graph/tests/test_neo4j_smoke.py` (Neo4j, APOC and GDS answer) | `make test-int` (needs Docker) |
| `ci` | `ui` | same | `npm ci`, lint, type check, unit tests and build of `ui/`. Until `ui/package.json` exists (M1.9d) every step is skipped and the check passes | `make check` runs the UI checks once `ui/` exists |
| `pr-hygiene` | `hygiene` | pull requests: opened, edited, synchronize, reopened, labeled, unlabeled | Standard-library scripts on the runner's Python 3.12: Conventional title (`check_pr_title.py`); size limit (`check_pr_size.py`); frozen contract paths (`check_contract_paths.py`); synthetic fixtures only (`check_fixtures.py`); wording lint (`check_wording.py`); then gitleaks v8.30.1 (a release binary pinned by SHA-256) over the pull request's own commits, failing if there are none to scan | `make hygiene` (gitleaks runs at commit time instead, see below) |
| `claude-review` | `review` | pull requests | Optional review agent. **Off**: `access.claude_review_action` is `off` in `project.yaml`, so the repository variable `CLAUDE_REVIEW` is not set and the job is skipped. It is never a required check. Before anyone sets `CLAUDE_REVIEW` to `on`: pin `anthropics/claude-code-action` to a full commit SHA instead of `@v1`, and reconsider its permission to comment, because the agent reads pull request content that anyone opening a pull request controls (prompt injection) | none |
| Dependabot | none | weekly | Version update pull requests for uv, npm (`ui/`), GitHub Actions, pre-commit hooks and Docker Compose, titled `build(deps): ...` or `ci(deps): ...`. TypeScript majors and the `neo4j` image are upgraded by hand. Until `ui/` exists (M1.9d), the npm entry shows an error in the Dependabot tab; nothing else is affected | none |

`pr-hygiene` is a separate workflow so that it re-runs when the title or the labels change; a re-run job would keep the title and labels it started with.

### What the hygiene scripts check

- **Title**: `^(feat|fix|docs|test|refactor|build|ci|chore)(\([a-z0-9-]+\))?!?: .+$`, for example `ci(ci): add the CI workflows [M1.6]` (PHASE-1.md 2.3).
- **Size**: added plus deleted lines of `git diff --numstat <base>...HEAD`, without the paths that match a glob in [.github/pr-size-exclude.txt](../../.github/pr-size-exclude.txt) (documentation, lock files, generated files, fixtures, examples, research notes). Above 400 lines the check fails; with the `size-exception` label it only warns. Only milestones whose header says `Size: exception` carry that label.
- **Frozen contract paths**: after the tag `contracts-v1.0.0` exists, a change under `contracts/` or `graph/schema/` needs the `contract-change` label (PHASE-1.md 5.0). Before the tag it passes.
- **Synthetic fixtures**: every tracked `*.ftm.jsonl` under `data/fixtures/`, `contracts/examples/` or any `tests/fixtures/` has `syn-` ids, datasets `["nr_synthetic"]` and `nr.synthetic: true` (the deliberately broken examples in `contracts/examples/c1/invalid/` are exempt); every CSV fixture there starts with `# synthetic: true`, or, for `LOAD CSV` files, has `synthetic` as its first column with `true` on every row; nothing else is tracked under `data/` except `README.md` and `.gitkeep` files (guardrail G2).
- **Wording**: the `wording` templates in `detect/typologies/*.yaml` and the string literals in `detect/src/**/wording.py` must not match `contracts/wording/forbidden-terms.txt` (PHASE-1.md 7.1). Until M1.7c creates that file, the script prints a notice and passes. Disclaimers and documentation are out of scope.
- **Secrets**: gitleaks scans every commit between the base branch (`refs/remotes/origin/<base>`, resolved to a commit first) and the pull request's head, and fails if that range holds no commit, so a missing base ref cannot pass as "no leaks". The gitleaks pre-commit hook only scans staged changes: it protects commits on machines where `make setup` installed the hooks, and it would scan nothing in CI, so the `python` job skips it (`SKIP=gitleaks`); this step is what scans pushed commits.

## Running the checks locally

```bash
make check                                   # lint, mypy, unit tests (with scripts/tests), contract checks
make hygiene                                 # the pr-hygiene scripts against origin/main
make hygiene LABELS=size-exception           # before the pull request exists, for a Size: exception milestone
make hygiene TITLE='ci(ci): add the CI workflows [M1.6]'
make test-int                                # integration tests (Docker)
uv run pytest scripts/tests -q               # the hygiene script tests only
```

`make hygiene` fetches `origin/main` first. Labels come from `LABELS=` (comma-separated), else from the branch's pull request (`gh pr view`), else none; the title comes from `TITLE=`, else from the pull request, else the title check is skipped. It runs every check and fails if any failed.

## Required checks

When the plan allows branch protection, the required status checks are `python`, `integration`, `ui` and `hygiene`. GitHub matches a required check by its check name, which is the job's `name:` when one is set, so the jobs have no `name:` and the job id is the check name (PHASE-1.md 3.2). `scripts/tests/test_setup_repo_protection.py` fails if the list in the protection script and the job ids drift apart or a job gains a `name:`.

## The protection script

`scripts/setup_repo_protection.sh` sets:

- branch protection on `main`: a pull request is required, with 1 approving review including a code owner, stale approvals dismissed, the four required checks, `enforce_admins` on, no force pushes and no deletion; linear history is not required, because merges use merge commits (operator decision OD-2), and branches do not have to be up to date with `main` before a merge (`strict` off);
- private vulnerability reporting;
- secret scanning with push protection;
- CodeQL default setup;
- Dependabot alerts and Dependabot security updates.

It prints `CHANGED` or `NOT CHANGED` with GitHub's reason for each, then a summary, and exits 1 if anything was not changed. Options: `--repo OWNER/NAME` (default: the repository `gh` finds from the git remote), `--branch`, `--approvals N`, `--no-code-owner-review`, `--dry-run` (prints the requests and sends nothing).

**Who runs it.** A person with admin rights on the repository, in their own terminal: `bash scripts/setup_repo_protection.sh`. Claude Code never runs it (CLAUDE.md rule 8). The guard hook blocks the agent's own `gh api` calls that change protection or settings, but it cannot see inside a script, so the script itself refuses to run when `CLAUDECODE` is set, except with `--dry-run`.

**While one person holds every role** (OD-6), run it as

```bash
bash scripts/setup_repo_protection.sh --approvals 0 --no-code-owner-review
```

GitHub never lets the author of a pull request approve it, and every pull request is opened from the operator's account, so a required approving review or a required code-owner review would block every merge, including the orchestrating session's `gh pr merge <n> --merge` (OD-2 rules out `--admin`). With these options a pull request and the four green checks are still required. Run it again with the defaults once a second person can review.

**Expected output on the current plan.** Branch protection, private vulnerability reporting, secret scanning and CodeQL report `NOT CHANGED` (the repository answered 403 or 404 to each on 21 October 2026, see below); Dependabot alerts and security updates are expected to report `CHANGED`, because they are available on private repositories too. The orchestrating session decided, under the operator's autopilot instruction (OD-10), that this run does not block merging M1.6; it is recorded as operator decision OD-16.

## Plan limitation and interim controls

The repository is `robotat-com/neon-radar`, a **private** repository on a personal account on **GitHub Free** (it moves to the `neonradar` organisation later, OD-7). On 21 October 2026 GitHub answered:

| Feature | Answer for this repository |
|---|---|
| Branch protection (`GET .../branches/main/protection`) | 403: "Upgrade to GitHub Pro or make this repository public to enable this feature." |
| Rulesets (`GET .../rulesets`) | 403, same message |
| Private vulnerability reporting | 404 (public repositories only) |
| CodeQL default setup | 403: "Code scanning is not enabled for this repository." |
| Secret scanning and push protection | not offered (`security_and_analysis` is empty) |
| Dependabot alerts | off, and available: the script turns them on |
| GitHub Actions | enabled |

So, while the repository is private on a free plan: branch protection, rulesets and required code-owner reviews are not available (they need GitHub Pro for a personal account, or GitHub Team for an organisation), and secret scanning push protection and CodeQL are free only for public repositories. Nothing on GitHub's side stops a push to `main` or a merge of a red pull request.

Until the repository becomes public (at launch, Gate 5) or moves to a plan that allows protection, these are the controls, and what each one really covers:

| Control | What it covers | What it does not cover |
|---|---|---|
| `.claude/hooks/guard_git.py` and the deny rules in `.claude/settings.json` | Claude Code sessions in this repository: no push to `main`, no force-push, no remote branch deletion, no settings change, no merge other than `gh pr merge <number> --merge` in the orchestrating session (OD-9) | People, other tools, and anything run inside a script |
| CI on every pull request and on `main` | Every pull request shows the result of the same checks. The orchestrating session merges only after `gh pr checks <n>` is green, the acceptance commands passed and an independent review found nothing left that affects correctness, the requirements or the guardrails (OD-2); humans review merged work afterwards | GitHub does not block a merge when a check is red or missing |
| gitleaks | The `hygiene` job scans each pull request's commits; the pre-commit hook scans each commit on machines where `make setup` ran | A secret pushed straight to a branch without a pull request is only caught when a pull request is opened |
| CODEOWNERS review requests | Nothing yet: the `@neonradar/nr-*` teams do not exist until the organisation does, and the only person listed is the account that opens every pull request, so GitHub requests no review | |
| Team discipline | Changes reach `main` only through pull requests, as [CONTRIBUTING.md](../../CONTRIBUTING.md) describes, and nobody merges a pull request whose checks are red | Mistakes: nothing technical stops a direct push by a person with write access |

Run the protection script again on launch day, after the repository becomes public, and after the move to the `neonradar` organisation; the script finds the repository from the git remote, and no workflow names the owner. If protection is wanted earlier, GitHub Pro for the owning account (or GitHub Team for the organisation) makes branch protection available on a private repository (Phase 1 risk R8); that is the project lead's decision.

## Actions minutes

A private repository on GitHub Free has 2,000 GitHub Actions minutes a month; each job is billed in whole minutes. Public repositories use standard runners without a minute limit. Measured on the M1.6 pull request (#10): `python` took 1 minute 26 seconds, `integration` 1 minute 4 seconds (the smoke test itself 44 seconds, including the GDS download), `ui` 6 seconds and `hygiene` 6 seconds, so one push costs about 6 billed minutes (2 + 2 + 1 + 1). Each title, label or description change re-runs only `hygiene` (1 minute), and the merge commit runs `ci` once more on `main` (about 5 minutes). A pull request with two or three pushes therefore costs about 15 to 25 minutes, so the quota covers roughly 80 to 130 pull requests a month; the times grow as tests and the UI build are added, and a slow GDS download can add minutes. To keep this down: `concurrency` cancels a superseded run of the same workflow on the same pull request (or on `main`), uv's cache and the pre-commit hook environments are kept between runs, and the integration job runs only `pytest -m "integration and not network"`. If the monthly minutes run out, CI cannot report green and merges stop until the next month or until the repository is public.

## Known gaps

- `graph/tests/test_neo4j_smoke.py` starts Neo4j with `NEO4J_PLUGINS`, which downloads the GDS jar from `graphdatascience.ninja` each time; the startup wait is 300 seconds for that reason. Operator decision OD-13 says Testcontainers and CI should mount the GDS jar that `scripts/fetch_gds.sh` (M1.4, `make plugins`) fetches and checks by SHA-256 instead. That switch belongs to M1.7b, which adds an `actions/cache` and `fetch_gds.sh` step to the `integration` job and moves the smoke test onto the shared fixture.
- `make hygiene` does not run gitleaks; the pre-commit hook covers local commits.
