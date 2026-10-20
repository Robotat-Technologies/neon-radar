---
name: typology-draft
description: Draft or update a NeonRadar typology definition file and its plain-language explainer from cited primary sources, always as status draft. Use for detect/typologies and docs/typologies work.
argument-hint: "[slug]"
---
Draft typology $ARGUMENTS.
- Sources: docs/research/2026-10-16/aml-domain.md section 2 and the bibliography keys in
  docs/sources/bibliography.yaml. Every factual sentence cites a key. If a claim has no
  source, leave it out and list it under "Open questions".
- Write detect/typologies/$ARGUMENTS.yaml in the shape of PHASE-1.md 5.4 with
  `status: draft`, `approved_by: null`.
- Write docs/typologies/<slug with hyphens>.md: what it is (plain language), how it looks
  in a graph, red flags from the sources, typical false positives, why synthetic data can or
  cannot show it, sources. No accusatory wording (7.1). Reading level: a new intern.
- Never set status approved.
