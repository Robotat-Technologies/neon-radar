# Squads and roles

Who owns what. The names come from `people` and `squads` in [project.yaml](../build/project.yaml), which is the source of truth: change it there first, then here. The role descriptions come from the [project plan](../plan/neonradar-project-plan.md), "Team structure".

**For now one person holds every role.** Until the team joins, @robotat-com is project lead, tech lead, mentor of every squad and every cross-cutting role below ([OD-6](../build/operator-decisions.md)). `people.interns` is empty, so no squad has members yet.

## Squads

Six small squads, each owning one directory and one line of the demo. The planned size is two or three people each.

| Squad | Owns | GitHub team | Mentor | Members | Delivers by 20 November (plan) |
|---|---|---|---|---|---|
| Data ingestion | `ingest/` | `@neonradar/nr-ingest` | @robotat-com | to be assigned | Loaders for four public sources plus the synthetic transaction generator, all producing the same record format |
| Graph and entity resolution | `graph/` | `@neonradar/nr-graph` | @robotat-com | to be assigned | The Neo4j schema, constraints and indexes, the loader, and entity matching across sources |
| Typologies and detection | `detect/` | `@neonradar/nr-detect` | @robotat-com | to be assigned | The typology catalog, each typology with a query that finds it and a test |
| Investigation copilot | `copilot/`, `api/` | `@neonradar/nr-copilot` | @robotat-com | to be assigned | Plain-English question to Cypher to grounded answer, with the supporting subgraph |
| Explorer UI | `ui/` | `@neonradar/nr-ui` | @robotat-com | to be assigned | The Vue 3 app: entity search, network canvas, alert queue, explain panel |
| Docs, DX and launch | `docs/`, `cli/`, root files, CI | `@neonradar/nr-docs` | @robotat-com | to be assigned | One-command setup, the README, tests in CI, the demo video and the launch post |

The teams live in the `neonradar` organisation, which is not created yet; until the repository moves there, it is `robotat-com/neon-radar` ([OD-7](../build/operator-decisions.md)). Code owners per path are in [.github/CODEOWNERS](../../.github/CODEOWNERS).

## Cross-cutting roles

Held alongside squad membership.

| Role | Holder | What the role owns |
|---|---|---|
| Project lead | @robotat-com | Scope; cuts work from the kill list when a gate slips; the daily standup |
| Tech lead | @robotat-com | The graph schema decision and the repository structure; approves and freezes the contracts |
| Squad mentors | @robotat-com | Review pull requests and unblock people; do not write the squad's code |
| Release manager | @robotat-com | Keeps `main` green, cuts the demo build, runs the Friday demo. Rotates weekly; `project.yaml` is updated each Monday |
| Data steward | @robotat-com | Licence checks on every data source, `DATA_SOURCES.md`, the synthetic data guarantees |
| Typology researchers | @robotat-com | Read the typology literature, write each definition and what a false positive looks like; the only people who approve a typology |
| Technical writer | @robotat-com | The README, the quickstart, the typology explainers |
| Demo producer | @robotat-com | The story the demo tells, the scripted walkthrough, the recorded video |
| Community manager | @robotat-com | `CONTRIBUTING.md`, good first issues, the issue and pull request templates, the teach-back rota ([teach-back.md](../learning/teach-back.md)) |

## Decisions that stay with people

Freezing a contract, approving a typology, accepting an architecture decision record and confirming a licence decision are always made by the people in these roles, never by an agent. Everyone writes their own learning log, self-assessment, teach-back, exit post and assignment submissions ([OD-5](../build/operator-decisions.md)).

## When people join

1. The project lead adds each GitHub handle to `people.interns` in `project.yaml`, assigns squads and cross-cutting roles there, and updates this file to match.
2. Everyone does [Assignment 1](assignment-1.md) and starts a learning log ([docs/learning/README.md](../learning/README.md)).
3. The community manager fills in the [teach-back rota](../learning/teach-back.md).
