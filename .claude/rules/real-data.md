---
paths:
  - "ingest/**"
  - "keys/**"
  - "resolve/**"
  - "graph/**"
  - "api/**"
  - "cli/**"
  - "data/**"
  - "docs/data/**"
---
# Real-data rules (PHASE-2.md G2, G8, G9, G10 and 7.4)
- Never open, print, grep, WebFetch or query real records: data/cache/real/,
  data/cache/spikes/, the neo4j-real instance (ports 7475 and 7688, database realdata) and
  the real API (port 8001). The default Neo4j instance, the API on port 8000, the UI and the
  Neo4j MCP server hold synthetic data only. Reproduce problems on the demo profile or the
  ER benchmark.
- Fetch (WebFetch, curl, wget) documentation and schemas only: never a list, register or
  leak data file, and never a page about a real person (for example a Companies House
  officer page). The loaders download data; the agent never does.
- A command that runs on a real profile prints counts, timings, rates, versions and
  settings only, and writes the same summary to data/cache/reports/<profile>/. Its errors
  go through the redaction guard; full tracebacks stay in data/cache/real/logs/.
- Library code logs record ids and values only at DEBUG. When the dataset is not
  synthetic, exceptions name the rule and the step, never a value or a person's record id.
- Human-only commands (er label, er review, api serve --real) refuse to run when stdin is
  not a terminal. Never run them, and never wrap them in script, expect or unbuffer.
- Loaders set topics and flags only when the source states them; a probabilistic match
  never adds one; possible-match text always says "not confirmed".
- Tests and fixtures are synthetic. Build non-synthetic look-alikes in test code (ids such
  as gbch-co-T0000001, names such as "Test Holder Ltd"). Hand-written synthetic fixtures in
  a source's own format (for example list XML) may be committed under tests/fixtures/.
