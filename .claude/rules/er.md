---
paths:
  - "resolve/**"
  - "keys/**"
  - "graph/src/neonradar_graph/loader.py"
  - "graph/src/neonradar_graph/mapping.py"
---
# Entity resolution rules (PHASE-2.md 7.1)
- PHASE-2.md 7.1 is the authority: deterministic rules D1 to D7, cannot-link rules X1 to
  X8, policy P1 to P6, thresholds in resolve/config/er.yaml. Use the rule ids in code,
  tests, conflicts.jsonl and candidates.jsonl.
- Splink 5 only (the signatures in PHASE-2.md 7.1.5). Never write Splink 4 code.
- Results are deterministic: sorted inputs, fixed seeds, merges in the order of 7.1.6,
  sorted outputs. Tests compare bytes on the benchmark.
- Never compare or merge synthetic with real records; a POSSIBLY_SAME_AS link never
  carries a property between nodes.
- After the freeze (Thursday 29 October) thresholds, rules and policy change only with the
  tech lead's approval in the pull request, and the change voids the evaluation sample.
- Committed models hold settings only; parameters trained on real data stay in the run folder.
- Every matching change reports benchmark precision and recall before and after.
