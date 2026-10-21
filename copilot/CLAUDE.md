# copilot: neonradar_copilot

- Purpose: the local, template-first investigation copilot. A placeholder until Phase 4.
- Owner: copilot squad (nr-copilot).
- Depends on: C3 (`CopilotRequest`, `CopilotAnswer`) and the C2 graph schema, in Phase 4.
- Commands: `uv run pytest copilot/tests`.
- Traps:
  - Nothing phones home: the copilot runs locally and sends nothing out.
  - Answers describe patterns, never accusations (PHASE-1.md 7.1).
