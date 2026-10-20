---
name: adr
description: Write an architecture decision record in docs/decisions using the project template and the pre-assigned number from the build spec. Use when a milestone asks for an ADR.
argument-hint: "[number] [title]"
---
Write ADR $ARGUMENTS.
- Use docs/decisions/_template.md. The number is pre-assigned in the phase spec (7.6 in
  PHASE-1.md); never pick a new number yourself.
- Context and options must cite evidence (docs/research/ files or official URLs).
- Status: always "proposed". The deciders named in the spec edit the ADR and set
  "accepted" themselves. Deciders are people, never yourself.
- Add the ADR to docs/decisions/README.md.
