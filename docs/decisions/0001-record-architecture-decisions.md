# 0001. Record architecture decisions

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (project lead and tech lead)

## Context

NeonRadar is built by AI agents working milestone by milestone, with several pull requests open in parallel, and reviewed by people who join the project at different times. Decisions such as the Neo4j version, the record format and the graph schema shape everything that follows. If they live only in chat threads or in one person's head, later contributors cannot tell why the project looks the way it does, and an agent may quietly reverse a decision it does not know about.

Two further constraints apply. People must own the decisions, not the agent that typed them up. And parallel pull requests must not collide on ADR numbers.

## Options considered

1. **No formal records.** Rely on pull request descriptions and the build spec. Cheap, but the reasoning is scattered and hard to find once the spec moves to the next phase.
2. **Decisions in a wiki or in issues.** Easy to edit, but outside the repository: not reviewed with the code, not versioned with it and not visible to an agent working in the repository.
3. **Architecture decision records in the repository** (`docs/decisions/`), one short Markdown file per decision in the lightweight format Michael Nygard described, reviewed in pull requests like code.

## Decision

We will record every non-obvious architecture decision as an ADR in `docs/decisions/`, using [the template](_template.md): Title, Status, Date, Deciders, Context, Options considered, Decision, Consequences and Sources.

- An ADR is owned by the people who made the decision, and its "Deciders" line names those people, never an agent.
- An agent may draft an ADR from a decision recorded in the build spec, but always with status `proposed`. The named deciders edit it until it says what they think, and only they set it to `accepted`. No agent sets an ADR to `accepted`, including the orchestrating session (operator decision OD-5).
- ADR numbers for Phase 1 are pre-assigned in `docs/build/PHASE-1.md` section 7.6, so parallel pull requests never collide. Later phase specs assign numbers from 0013 on.
- A decision that changes an accepted ADR gets a new ADR; the old one is set to `superseded` and links to its replacement.
- [The ADR index](README.md) lists every ADR with its status.

## Consequences

- Reviewers and newcomers can find why a choice was made, and what was rejected, next to the code it shaped.
- Writing an ADR adds a small step to significant decisions. Agents do the drafting, so the cost falls mostly on reading and editing.
- Pull requests that implement a decision can link the ADR instead of repeating the reasoning.
- `proposed` ADRs that nobody accepts are visible in the index and get raised at the next gate.

## Sources

- `docs/build/PHASE-1.md` section 7.6 (ADR numbering and deciders) and section 0.5, item 15 (agents draft ADRs as `proposed`; deciders accept them).
- `docs/build/operator-decisions.md`, OD-5 (human sign-offs stay human).
- Michael Nygard, "Documenting Architecture Decisions", 15 November 2011: <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>.
