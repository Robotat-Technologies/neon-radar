# 0011. AI-built workflow

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (project lead and tech lead)

## Context

NeonRadar is planned over five weeks (16 October to 20 November 2026, `docs/build/PHASE-1.md` section 0.3; under OD-1 these dates are informational). It is built mostly by AI agents (Claude Code), working from a build spec one milestone at a time. Phase 1 alone has about 30 agent pull requests planned for one week (R5), so review capacity is the main constraint (`PHASE-1.md` section 9). Agent output can be plausible and still wrong (R7), and the interns must still learn by doing (R12).

Three further facts shape the workflow:

- **Shared context.** Every session, for every person, needs the same rules, commands and conventions. Rules written only in chat do not carry over.
- **Instructions alone are not enough.** Some mistakes must never happen: pushing to `main`, force-pushing, merging in the wrong way, deleting branches or tags, changing repository settings, and editing frozen contracts. Claude Code's own documentation calls CLAUDE.md "context, not enforced configuration" and points to hooks for actions that must be blocked.
- **One person holds every role for now.** Until the team joins, @robotat-com is project lead, tech lead, every mentor and every other named role (`docs/build/operator-decisions.md`, OD-6). If one person had to review and merge every pull request before the next could start, the build would stall.

## Options considered

1. **People write the code, with AI help in the editor.** Authorship is clear, but the five planned weeks are not enough for the planned scope, and the project would not show what it set out to show about AI-built software.
2. **Agents draft; people review and merge every pull request.** This is the workflow `PHASE-1.md` describes (sections 0.2 and 1.9). Every change gets a human gate before it reaches `main`. With one person in every role, though, merges queue behind that one person, and dependent milestones wait.
3. **Agents draft; an orchestrating session that the operator authorised merges after checks; people review merged work and keep the sign-offs.** The orchestrating session merges only after three things hold: the acceptance commands passed, an independent agent review found nothing left that affects correctness, the requirements or the guardrails, and CI passed. People review merged work afterwards and own every decision that needs human judgement (OD-2 to OD-5).
4. **Agents do everything, including sign-offs.** Agents would also freeze contracts, approve typologies, accept ADRs and decide licences. This is the fastest option, but nobody would be accountable for those decisions, and it breaks guardrail G4 and the learning track.

## Decision

We will use option 3.

- **One milestone, one branch, one pull request.** Each pull request follows the protocol in `PHASE-1.md` section 2.2. Agent pull requests carry the `agent` label and name one accountable human owner. Commits follow Conventional Commits, and the size rule in section 2.3 applies.
- **Builders stop at an open pull request.** A milestone builder never merges, never pushes to `main`, never force-pushes, never deletes remote branches and never changes repository settings (OD-3).
- **Independent review runs as a separate agent.** The orchestrating session starts it after the builder opens the pull request, using `.claude/agents/reviewer.md`, plus `contract-guardian.md` or `aml-claims-checker.md` where section 2.2 step 7 asks for them (OD-4). Fixes go onto the same branch before the merge.
- **Only the orchestrating session merges, and in one way only.** It runs `gh pr merge <number> --merge`, optionally with `--repo`, `--subject` or `--body`. It never squashes, rebases, uses `--admin`, uses `--auto` or deletes the branch (OD-2, OD-9). The merge commits keep each milestone's own commits visible on `main`.
- **People keep the human decisions.** People freeze contracts and create the `contracts-v*` tag, approve typology definitions, accept ADRs, confirm licence decisions, and write learning logs, self-assessments, teach-backs, exit posts and assignment submissions (OD-5). The orchestrating session pauses at each of these and asks the operator. The operator reviews merged work. A change found wrong after a merge is fixed or reverted in a new pull request.
- **The agent kit is the shared context.** It consists of:
  - `CLAUDE.md`;
  - path-scoped rules in `.claude/rules/`;
  - the skills in `.claude/skills/` (`/milestone`, `/open-pr` and four more);
  - the review subagents in `.claude/agents/`;
  - the project settings in `.claude/settings.json`;
  - a read-only Neo4j MCP server in `.mcp.json`.
- **Deterministic controls enforce what must never happen.**
  - `.claude/hooks/guard_git.py` checks every shell command:
    - pushes go only to `p<phase>/` milestone branches, never force-pushed or deleted;
    - the one merge form above is the only merge it lets through, and inside a subagent it blocks every merge, so OD-3 is enforced by code;
    - `gh api` writes that merge, move or delete refs, commit files, post CI results or change protection, releases or settings are blocked.
  - `.claude/hooks/guard-contracts.sh` blocks edits to `contracts/` and `graph/schema/` once the tag `contracts-v1.0.0` exists.
  - The deny rules in `.claude/settings.json` are a second layer for the common forms of the same mistakes.
  - CI (M1.6) and branch protection, where the GitHub plan allows it, add server-side checks.
  - `scripts/test_hooks.sh` is the hooks' self-test; every pull request that changes a hook or `.claude/settings.json` runs it and shows the result (M1.6 or later may add it to CI).
- **We measure the share of agent-drafted work and publish it at launch.** The measure is merged pull requests with the `agent` label against all merged pull requests (`gh pr list --state merged --label agent` against `gh pr list --state merged`), reported in each phase report.

## Consequences

- **Faster and more consistent.** Milestones whose dependencies are merged can proceed without waiting for one person, and every session starts from the same rules.
- **Work reaches `main` before a person reads it.** The controls before the merge (acceptance evidence in the pull request, independent review, CI, the hooks) carry more weight. The operator's review after the merge, and the gates in `PHASE-1.md` section 8, are where people catch what those controls miss.
- **Builders cannot merge, and this is enforced by code, not only by instructions.** The hook input carries `agent_id` whenever a hook fires inside a subagent, and in the orchestrated build, milestone builders and reviewers run as subagents of the orchestrating session. This rests on Claude Code providing that field.
  - A builder started as a Claude Code session of its own is bound by `CLAUDE.md` rule 8 and the review, not by this check.
  - If the orchestrating session itself ever ran as a subagent, its merges would also be blocked, and it would ask the operator.
- **Repository administration stays with the operator, by design.** Agent sessions are blocked from:
  - transferring the repository;
  - creating teams;
  - setting branch protection or rulesets;
  - creating or deleting the `contracts-v*` freeze tag;
  - creating releases;
  - changing repository, organisation, secret or Actions settings.

  The operator runs these actions in their own terminal, outside Claude Code.
- **The hooks guard against mistakes, not against attackers.** They read the command text. A program started some other way, such as a script, a `make` target, a Python subprocess, a git or gh alias defined earlier, or a gh extension, is not checked. Claude Code's documentation says the same of its permission rules: they are not a security boundary around a program. Server-side protection is the backstop, and on a private repository on the free GitHub plan it is limited (R8).
- **Some harmless commands are blocked.** A command whose quoted text mentions a guarded command, such as a commit message containing `git push`, is blocked, because the hook cannot tell the mention from a hidden call. Agents pass such text with `git commit -F <file>` or `--body-file <file>`.
- **Changes to the kit take effect right away.** Claude Code picks up edits to hooks in settings files through its file watcher. A broken hook therefore affects running sessions too, and kit changes go through the same pull request and self-test as code. A new `.claude/agents/` folder needs a session restart before its subagents can be used.
- **Revisit later.** We revisit this decision when the team joins (OD-6), and before launch, when branch protection on the public repository becomes available. Returning to people merging every pull request (option 2) is the expected default once there are enough reviewers.

## Sources

- `docs/build/PHASE-1.md`: section 0.2 (how the build runs), 0.5 items 13 and 15, 1.5 (Claude Code settings), 1.8 (parallel work and merge rhythm), 1.9 (what humans do themselves), 2.1 to 2.6 (operating rules), 9 (risks R5, R7, R8 and R12) and milestone M1.2 (the agent kit).
- `docs/build/operator-decisions.md`: OD-1 (no date targets), OD-2 (the orchestrating session merges), OD-3 (builders never merge), OD-4 (independent review as a separate agent), OD-5 (human sign-offs stay human), OD-6 (one person holds every role), OD-8 (wording about how the project is built) and OD-9 (the merge guard).
- `docs/research/2026-10-16/synthetic-docs-mcp.md`, part C: the Neo4j MCP server (read-only mode, GPL-3.0, run as an external tool) and the Claude Code GitHub Action.
- Claude Code documentation, checked on 2026-10-21:
  - hooks (exit code 2 blocks a tool call; `agent_id` and `agent_type` inside subagents; the file watcher): <https://code.claude.com/docs/en/hooks>;
  - permissions (deny, then ask, then allow; rules match command text and are not a security boundary): <https://code.claude.com/docs/en/permissions>;
  - CLAUDE.md and path-scoped rules: <https://code.claude.com/docs/en/memory>;
  - skills: <https://code.claude.com/docs/en/skills>;
  - subagents: <https://code.claude.com/docs/en/sub-agents>;
  - MCP: <https://code.claude.com/docs/en/mcp>.
