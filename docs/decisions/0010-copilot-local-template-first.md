# 0010. Copilot: local and template first

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead, copilot mentor)

To be decided in Phase 4, when the copilot is built (`docs/build/PHASE-1.md` section 7.6). This draft records the design the spec and the plan describe, so that the API contract and the Phase 4 spec can rely on it; the deciders edit it until it says what they think.

## Context

The investigation copilot is the third layer of the [project plan](../plan/neonradar-project-plan.md): a plain-English question goes in, and an answer comes out "plus the subgraph that supports it", grounded in the graph "so it cannot invent relationships". The plan ranks it as showcase tier and names the risk directly: "Natural language to Cypher is hard, and an impressive demo that fails live is worse than no demo". Its answer to that risk is to "constrain it to a library of parameterized question templates rather than open-ended generation" so that "it refuses rather than guesses"; the second cut on the plan's kill list turns the copilot into "a fixed menu of parameterized queries with natural language labels". The plan's definition of done asks the copilot to answer 10 benchmark questions correctly.

Several constraints already hold:

- **Nothing phones home (guardrail G3).** NeonRadar makes no outbound calls at runtime. A hosted language model would send the user's questions and parts of the graph to a third party.
- **Patterns, not accusations (G5).** From Phase 4 the copilot's answers are entity-facing text, so they follow the vocabulary in [docs/wording.md](../wording.md) and must pass the wording lint, like alert text (PHASE-1.md 7.1).
- **No read-only database user.** NeonRadar runs Neo4j 5.26 Community Edition, which has no role-based access control, so a read-only database user cannot be created; the research note recommends relying on the `EXPLAIN` query-type check, read transactions, procedure allowlists and the template-first design (`docs/research/2026-10-16/stack.md` section 6; `synthetic-docs-mcp.md` part C).
- **The API contract already has a shape for answers.** C3, in review in pull request #24 (PHASE-1.md 5.3 until it merges), defines `POST /api/v1/copilot/ask` answering `501` until Phase 4, and a `CopilotAnswer` with `status` (`answered`, `refused` or `unsupported`), `answer_text`, `template_id`, `cypher`, `parameters`, `subgraph` and `refusal_reason`. An answered question must carry its query, its parameters and its subgraph; a refusal must carry a reason.

What the tools offered on 16 October 2026 (`docs/research/2026-10-16/neo4j.md` section 8 and `stack.md` section 6):

- **Ollama** (v0.40.5, MIT) runs open-weight models locally, and its Python client is on PyPI.
- **neo4j-graphrag** (1.22.0, Apache-2.0) has an `OllamaLLM` adapter that defaults to `127.0.0.1:11434`, and a `Text2CypherRetriever`. Since 1.16.0 the retriever "runs `EXPLAIN` on the LLM-generated Cypher and refuses to execute anything that is not read-only", and in 1.22.0 it executes with `RoutingControl.READ`. Its schema helpers need APOC, which the local stack has.
- **Model choice is open.** No benchmark of 8-billion-parameter or smaller models for text-to-Cypher could be verified. An 8B model in 4-bit quantisation needs roughly 5 to 6 GB of memory, which competes with Neo4j on an 8 GB laptop (unverified for any specific model).
- **Read-only checks have limits.** The Neo4j MCP server's README warns that procedures or functions "incorrectly classified as read-only by Neo4j may bypass" its `EXPLAIN`-based check (`synthetic-docs-mcp.md` part C).

## Options considered

1. **Local model, templates first, guarded free text-to-Cypher as a fallback, refusal otherwise (proposed).** A library of parameterised Cypher question templates answers most questions; the model's job is to pick a template and fill its parameters. Free text-to-Cypher runs only when no template fits and only behind read-only checks. Advantages: every template is written, reviewed and tested against fixtures in advance; the benchmark questions become tests; answers stay grounded and reproducible. Drawbacks: templates take work to write and cover a fixed set of questions; the fallback still needs careful guarding.
2. **Local model, free text-to-Cypher only.** Most flexible. It is the failure the plan warns about: generated Cypher can be plausible and wrong (risk R7 in PHASE-1.md section 9), small local models are unproven at it, and every answer would need checking.
3. **A hosted model through a provider's API.** Stronger models and less local memory, but it breaks G3, sends questions and graph data to a third party, and needs keys and a budget.
4. **A fixed menu of templates, no language model.** Always works and needs no model, but it is not a copilot. It is the plan's kill-list fallback, and option 1 degrades to it when no model is available.

## Decision

We will build the copilot as option 1:

- **Offline only.** The model runs locally through Ollama on `127.0.0.1`. No hosted model, no telemetry and no outbound call at runtime (G3). Which model is a Phase 4 experiment: try two or three Ollama models in the 3B to 8B range against the 10 benchmark questions, with the real schema in the prompt, and record the result.
- **Templates first.** A versioned library of parameterised Cypher templates, each with a natural-language label, the C2 labels and relationships it reads, parameter types and limits, and a test on a synthetic fixture. The model chooses a template and extracts parameters; parameters are validated before the query runs; `template_id` names the template.
- **Free text-to-Cypher only behind read-only checks.** When no template fits, generated Cypher must pass `EXPLAIN` as a read-only query, run in a READ transaction, call only procedures on an allowlist, and follow the Cypher rules (parameters only, bounded hops, a `LIMIT`). Anything that fails a check is not run.
- **Refusal rather than guessing.** When no template fits and no generated query passes the checks, or the result cannot ground an answer, the copilot answers `refused` or `unsupported` with a `refusal_reason` instead of an answer.
- **Every answer returns its evidence.** An `answered` response carries the Cypher, its parameters and the subgraph it returned, so the reader can check the answer against the graph, as every C4 alert carries its evidence.
- **Wording.** Answer text uses the entity-facing vocabulary and passes the wording lint before it is returned.

## Consequences

- The copilot can only answer what a template or a checked query can express. That is narrower than open text-to-Cypher, and deliberately so.
- Templates become a reviewed asset, owned by the Copilot squad with the same review as detectors, and the 10 benchmark questions become tests.
- Laptops without the memory for a local model run the copilot as a menu of templates (option 4) with the same API shape.
- The read-only checks reduce the risk of a harmful query but do not remove it: a procedure misclassified as read-only could still write. The allowlist and the template-first design are the main defence, and the API's READ transactions are the backstop.
- The facts about tools and models above date from 16 October 2026; the deciders re-check them when Phase 4 starts.

## Sources

- `docs/plan/neonradar-project-plan.md`: "What we are building" (layer 3), the risk table ("The copilot is unreliable"), the kill list (item 2), the definition of done (10 benchmark questions) and "The agent that is the product".
- `docs/build/PHASE-1.md`: sections 2.1 (G3, G5), 5.3 (C3, `CopilotRequest` and `CopilotAnswer`), 7.1 (wording), 7.6 (ADR numbers) and 9 (risk R7).
- `contracts/C3-api.md` in pull request #24 (in review): "Copilot (Phase 4)".
- `docs/research/2026-10-16/stack.md` section 6 (local LLM for the copilot) and `docs/research/2026-10-16/neo4j.md` section 8 (neo4j-graphrag).
- `docs/research/2026-10-16/synthetic-docs-mcp.md` part C (read-only mode of the Neo4j MCP servers and its limits).
- neo4j-graphrag changelog, entry 1.16.0, checked on 2026-10-21: <https://github.com/neo4j/neo4j-graphrag-python/blob/main/CHANGELOG.md>
- Neo4j GraphRAG for Python, User Guide: RAG (Text2Cypher retriever; using a local model via Ollama), checked on 2026-10-21: <https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html>
