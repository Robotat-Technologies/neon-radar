---
paths:
  - "copilot/**"
  - "api/**"
  - "docs/benchmark-questions.md"
  - "data/fixtures/copilot-bench/**"
---

# Copilot and API rules (PHASE-4.md 2.1, 7.2 to 7.8)

- G13: Cypher comes only from committed query files. Never build a query string from input;
  `{{max_hops}}` is the only rendered value, chosen in code. No model output is ever run as a
  query or written into an answer, and a question the model routed is answered only after the
  person confirms the reading.
- G14: refusal, clarification and grounding are decided in code. Never pick one of several
  entities, never take a near match for an exact one, never answer a judgement, a risk, a
  prediction, a decision or a personal detail, and never repeat words of a question that did not
  ground as a name. Absence names what was searched ("through ownership, control and
  directorship links, no chain of at most N relationships"), never "no connection exists"; a cut
  list says it was cut.
- G15: a question, a slot value, a name or an entity id from a question never reaches a log, an
  error detail, a metric, a URL, a file or test output. The access log names route templates;
  database errors are logged by code; the driver and HTTP client loggers stay at WARNING.
- G16: never read, write, run or tune against the held-out questions (`data/cache/heldout/` or
  any file a human names as held out).
- Every sentence the copilot writes lives in `copilot/src/neonradar_copilot/texts.py`, with a
  test; the wording lint runs on every answer at run time as well.
- Every Neo4j read goes through `neonradar_graph.readonly.run_read`: READ access mode, a
  transaction timeout, a row cap, never a commit, the summary check.
- The two ports change together: a new port method gets a query file, a `MemPort`
  implementation and a parity case in `test_neo4j_parity.py`, in the same pull request.
- The benchmark (`copilot/bench/*.yaml`, `data/fixtures/copilot-bench/`,
  `docs/benchmark-questions.md`) changes only in a pull request labelled `benchmark-change` that
  the copilot mentor approves.
- Real data: every template keeps its category's policy (`policy.py`), on answers, choices and
  suggestions alike; never weaken it to make a question answerable. An account a real entity
  holds is part of that entity: never shown. People are shown by name, role and source only.
- The model router stays optional and off by default. It sees only the question and the
  template list, and `router.from_proposal` checks every reply.
