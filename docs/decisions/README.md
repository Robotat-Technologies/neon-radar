# Architecture decision records

Every non-obvious architecture decision is recorded here as an ADR, owned by the people who made it ([ADR-0001](0001-record-architecture-decisions.md)). Start a new one from [the template](_template.md).

- **Status** is `proposed`, `accepted` or `superseded`. Agents draft ADRs only as `proposed`; the named deciders edit them and set `accepted`.
- **Deciders** are people, never an agent.
- **Numbers** for Phase 1 are pre-assigned below (from `docs/build/PHASE-1.md` section 7.6), so parallel pull requests never collide. Later phase specs assign numbers from 0013 on.
- **File names** follow `NNNN-kebab-title.md`.

## Index

| Number | Title | Written in | Status | Deciders |
|---|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | M1.1 | proposed | project lead, tech lead |
| [0002](0002-neo4j-5-26-lts.md) | Neo4j 5.26 LTS | M1.4 | proposed | tech lead |
| [0003](0003-followthemoney-record-format.md) | FollowTheMoney as the record format | M1.7a | proposed | tech lead |
| [0004](0004-graph-schema-v1.md) | Graph schema v1 | M1.7b | proposed | tech lead |
| [0005](0005-synthetic-data-policy.md) | Synthetic data policy | M1.8e | proposed | tech lead, data steward |
| 0006 | Data licensing | M1.10a | not written yet | data steward, project lead |
| [0007](0007-toolchain.md) | Toolchain | M1.3 | proposed | tech lead |
| 0008 | API gateway and OpenAPI snapshot | M1.7d | not written yet | tech lead |
| 0009 | Alert object and wording | M1.7c | not written yet | tech lead, typology researchers |
| 0010 | Copilot: local and template first | M1.10c | not written yet (decided in Phase 4) | tech lead, copilot mentor |
| [0011](0011-ai-built-workflow.md) | AI-built workflow | M1.2 | proposed | project lead, tech lead |
| 0012 | Documentation site | M1.10c | not written yet (decided in Phase 6) | technical writer, tech lead |

The roles resolve to people in `docs/build/project.yaml` (`people`); until the team joins, @robotat-com holds every role.
