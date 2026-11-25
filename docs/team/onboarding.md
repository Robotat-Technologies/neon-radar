# Onboarding checklist

Access, tools and first-week steps for each new collaborator, and how the team list stays current. Each step names who does it. Roles resolve to people in `people` in [project.yaml](../build/project.yaml); until the team joins, @robotat-com holds every role ([OD-6](../build/operator-decisions.md), [roles.md](roles.md)).

Copy the list into your first pull request description or a comment on your task card, and tick it as you go. If a step is wrong or missing, fix this page in a pull request: that is a good first contribution.

## 1. Access (before day one)

- [ ] **Project lead:** add the newcomer's GitHub handle to every list in `people` in [project.yaml](../build/project.yaml) that applies: `interns`, any cross-cutting role, and the lists filled as people join (`er_labellers`, which covers every intern; `freeze_deciders` and `heldout_owner` when they take those roles). Record their squad in the Members column of [roles.md](roles.md), and update the role holders there to match ([roles.md](roles.md), "When people join"). See section 4.
- [ ] **Project lead:** give them access to the GitHub repository so they can push branches and open pull requests. Once the `neonradar` organisation exists, also add them to their squad's GitHub team (`@neonradar/nr-<squad>`), which [CODEOWNERS](../../.github/CODEOWNERS) uses to route reviews ([OD-7](../build/operator-decisions.md)). Without write access, a contributor works from a fork and a maintainer approves the workflow runs on their pull requests.
- [ ] **Whoever runs the team's task board** (kept outside this repository): add them to it.
- [ ] **Mentor:** introduce themselves, point to this page, and be the person who reviews and unblocks ([roles.md](roles.md)).

## 2. Tools (day one)

- [ ] **Newcomer:** install the requirements in the [quickstart](../quickstart.md): macOS or Linux, or WSL 2 on Windows; Docker; uv 0.13; ICU and `pkg-config`; Node.js 24.12 or later. Run `uv run neonradar doctor` to check the machine.
- [ ] **Newcomer:** clone the repository, run `make setup` and then `make demo-mini`, and open the UI at http://localhost:8080. Every company, person and payment in the demo is synthetic.
- [ ] **Newcomer:** run `make check` once, so you know what a green build looks like before you change anything.
- [ ] **Newcomer:** keep secrets in `.env` only. `make setup` creates it with a generated Neo4j password; never commit it, paste it or print it. A Companies House API key, if your work needs one, is your own and lives there too ([DATA_SOURCES.md](../../DATA_SOURCES.md)).

## 3. First week

**Read**, in this order:

- [ ] [README](../../README.md), including "What it is not" and the standing disclaimer.
- [ ] [CONTRIBUTING.md](../../CONTRIBUTING.md) and the [Code of Conduct](../../CODE_OF_CONDUCT.md).
- [ ] [wording.md](../wording.md): NeonRadar describes patterns and never makes accusations.
- [ ] The [screenshot and video policy](../screenshot-policy.md), before you share any image of the demo.
- [ ] [roles.md](roles.md): who owns what, and the decisions that stay with people.

**Do:**

- [ ] **Newcomer:** [Assignment 1](assignment-1.md): load the onboarding CSV, write a two-hop query and open your first pull request.
- [ ] **Newcomer:** start your learning log from the [template](../learning/_template.md), score yourself in the "Start" column and write your first entry ([learning/README.md](../learning/README.md)). Only you write in it.
- [ ] **Project lead:** assign a typology for [Assignment 2](assignment-2.md) in its Assignee column.
- [ ] **Community manager:** put the newcomer on the [teach-back rota](../learning/teach-back.md).
- [ ] **Newcomer:** work through the starter tasks on the task board, and mark only the ones you have done yourself.

**Rules to know from the first pull request** ([CONTRIBUTING.md](../../CONTRIBUTING.md)):

- [ ] Open an issue first, with one of the issue forms, so the work is agreed before anyone writes it.
- [ ] Fill in every section of the [pull request template](../../.github/pull_request_template.md), and ask a member of another squad to review.
- [ ] You must be able to explain every line of your pull request. Say honestly whether and how you used AI.
- [ ] Commit messages follow Conventional Commits: `type(scope): summary`.
- [ ] Keep a pull request to at most 400 changed lines of code, tests and configuration.
- [ ] Update a branch by merging, never by rebasing a pushed branch or force-pushing.
- [ ] Use synthetic data only (ids starting `syn-`). Never commit real personal data, and never label a real person or company. Real data is loaded only on approved machines ([real-data handling](../data/real-data-handling.md)).
- [ ] Ask your mentor which branch to target. `CONTRIBUTING.md` says `main`; most recent pull requests target `dev`.

## 4. Keeping the team list current

The team list lives in two files in the repository, and they must agree. **The project lead** keeps them current whenever someone joins, leaves or changes role:

1. [project.yaml](../build/project.yaml), `people`: the source of truth for who holds which role. Gate checks read it, for example `people.interns` for the learning-log and first pull request checks.
2. [roles.md](roles.md): the readable copy of the same names, plus each squad's members. It is updated after `project.yaml`, never instead of it.

The task board outside the repository should list the same people; whoever runs it keeps it in step.

The release manager role rotates weekly, and `project.yaml` is updated each Monday ([roles.md](roles.md)). [CONTRIBUTORS.md](../../CONTRIBUTORS.md) is filled in by people, not agents, with what each person owned.

## 5. Leaving

- [ ] **Leaver:** write your exit post in the final week ([learning/README.md](../learning/README.md), "Exit post"). It is yours.
- [ ] **Leaver, if your machine is on the [approved real-data machines](../data/real-data-machines.md) list:** follow that page's steps to purge real data and remove the machine's approval. The data steward then deletes its row.
- [ ] **Project lead:** update `project.yaml` and `roles.md` (section 4), and reassign any role the person held. Whoever runs the task board removes them from it.
