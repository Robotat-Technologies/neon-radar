---
paths:
  - "**/*.cypher"
  - "graph/**"
  - "detect/**"
---
# Cypher rules (Neo4j 5.26 Community, Cypher 5)
- Parameters only. Labels and relationship types come from the C2 mapping table, never
  from data.
- Use `CALL (x) { ... }`, `elementId()`, quantified relationships `-[:R]->{1,6}` or
  quantified path patterns; never `[*..]`, never `id()`.
- Bound every traversal (at most 8 hops), every result (LIMIT) and every time window.
- Large writes: `CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS` in auto-commit queries.
- Never `apoc.periodic.iterate`, `SET n = r`, `indexProvider`, or existence/type/key
  constraints (Enterprise only).
- GDS calls pass `concurrency: 4`. Prefer `CALL gds.<algo>.stream(...)` from Cypher.
- Detection queries read only C2 labels, types and properties.
- Every detection query has a fixture test with a known right answer.
