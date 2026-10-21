# Reading list

Short and mandatory, because an unbounded list gets ignored ([project plan](../plan/neonradar-project-plan.md), "Learning track"). Each sprint has a list for everyone and one for the squad that needs it most. The plan's sprints map onto the build phases as each heading shows. Squad names follow [docs/team/roles.md](../team/roles.md).

Every link below goes to an official page that was opened on 21 October 2026, by this milestone or, where marked, by milestone M1.10a. Where an official page could not be opened by the build, the title is given without a link and marked "link to be added". Write what you read, and what still confuses you, in your [learning log](README.md#your-learning-log).

## Sprint 0 (Phase 1: foundation and contracts)

**Everyone reads:**

- **Neo4j graph data modelling.** Neo4j, [What is graph data modeling?](https://neo4j.com/docs/getting-started/data-modeling/) (Getting Started guide): the modelling process in six steps, with links to the full tutorial and a glossary of nodes, relationships, labels, indexes and constraints. Then compare it with NeonRadar's own model in [C2: Graph schema](../../contracts/C2-graph-schema.md).
- **One FATF typology report**, either of:
  - FATF and Egmont Group, *Concealment of Beneficial Ownership* (2018) [fatf_egmont_concealment_2018]. The full report on fatf-gafi.org: link to be added (the site refuses automated access, so the build could not open it; the bibliography entry has the address the research note used). The Egmont Group hosts official copies of its [executive summary](https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-Executive-summary.pdf) and of [Annex E](https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf), the indicators of concealed beneficial ownership, such as mass registration addresses and nominees (both opened by milestone M1.10a).
  - FATF, *Professional Money Laundering* (2018) [fatf_pml_2018]: link to be added, for the same reason. It covers professional launderers, mule networks and networks of company accounts.
- **FollowTheMoney documentation.** [FollowTheMoney](https://followthemoney.tech/), the data model behind NeonRadar's record format: start with the introduction and the entity schemata explorer, then read [C1: NeonRadar Record](../../contracts/C1-record.md) to see which schemata NeonRadar uses.

**The Data ingestion squad also reads:**

- **Companies House API documentation.** [Companies House API overview](https://developer.company-information.service.gov.uk/) (Developer Hub): the overview, "Get started" and the REST API pages. The spike report [docs/data/spikes/companies-house.md](../data/spikes/companies-house.md) shows what the spike fetched.
- **OpenSanctions API documentation.** [Getting started with the API](https://www.opensanctions.org/docs/api/) (OpenSanctions). Read it, but do not fetch OpenSanctions data: its use is gated by a licence decision (`access.opensanctions` is `none`; [ADR-0006](../decisions/0006-data-licensing.md)).

## Sprint 1 (Phase 2: ownership graph)

**Everyone reads:**

- **Cypher query tuning basics.** Neo4j Cypher Manual, version 5: [Query plans, tuning, and caching](https://neo4j.com/docs/cypher-manual/5/planning-and-tuning/). NeonRadar runs Neo4j 5.26 and writes Cypher 5, so use the version 5 manual, not the newer Cypher 25 pages.
- **How indexes and constraints work in Neo4j.** Neo4j Cypher Manual, version 5: [Indexes](https://neo4j.com/docs/cypher-manual/5/indexes/) and [Constraints](https://neo4j.com/docs/cypher-manual/5/constraints/). The constraints page marks existence, type and key constraints as Enterprise Edition; NeonRadar runs Community Edition, so it uses uniqueness constraints only ([C2](../../contracts/C2-graph-schema.md), "Migrations").

**The Graph and entity resolution squad also reads:**

- **Splink documentation.** The [Splink repository](https://github.com/moj-analytical-services/splink), whose README links the documentation site. NeonRadar uses Splink 5, whose interface changed from Splink 4 (see the known traps in [CLAUDE.md](../../CLAUDE.md)).
- **The Fellegi-Sunter record linkage model.** Splink's topic guide [The Fellegi-Sunter model](https://github.com/moj-analytical-services/splink/blob/master/docs/topic_guides/theory/fellegi_sunter.md) (source on GitHub; the same page is on the Splink documentation site): its parameters, match weights and match probability.

## Sprint 2 (Phases 3 and 4: detection and the copilot)

**Everyone reads:**

- **Graph Data Science overview.** Neo4j Graph Data Science manual, version 2.13 (the version NeonRadar pins): [Community detection](https://neo4j.com/docs/graph-data-science/2.13/algorithms/community/), [Centrality](https://neo4j.com/docs/graph-data-science/2.13/algorithms/centrality/) and [Weakly Connected Components](https://neo4j.com/docs/graph-data-science/2.13/algorithms/wcc/).

**The Investigation copilot squad also reads:**

- **Text-to-Cypher and GraphRAG patterns.** Neo4j, [GraphRAG for Python](https://neo4j.com/docs/neo4j-graphrag-python/current/), and its [User Guide: RAG](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html), which has sections on the Text2Cypher retriever and on using a local model through Ollama.
- **Their failure modes.** The package's [changelog](https://github.com/neo4j/neo4j-graphrag-python/blob/main/CHANGELOG.md), entry 1.16.0: the Text2Cypher retriever now runs `EXPLAIN` on generated Cypher and refuses anything that is not read-only, which guards against prompt-injected writes. Then read the proposed [ADR-0010](../decisions/0010-copilot-local-template-first.md) for why NeonRadar's copilot starts from question templates and refuses rather than guesses.

## Sprint 3 (Phases 5 and 6: explorer UI, hardening and launch)

**Everyone reads:**

- **What makes an open-source project usable by strangers.** GitHub's Open Source Guides, [Starting an Open Source Project](https://github.com/github/opensource.guide/blob/main/_articles/starting-a-project.md) (source of the article on opensource.guide), the section "Launching your own open source project". Then read NeonRadar's own [README](../../README.md) and [CONTRIBUTING](../../CONTRIBUTING.md) as a stranger would.

**The Docs, DX and launch and the Explorer UI squads also read:**

- **Technical writing for READMEs.** The same article, sections "Writing a README" and "Writing your contributing guidelines".
- **Vue 3 Composition API.** The official Vue documentation, [Composition API FAQ](https://github.com/vuejs/docs/blob/main/src/guide/extras/composition-api-faq.md) (source in the vuejs/docs repository, which builds vuejs.org). NeonRadar's frontend uses `<script setup lang="ts">` (see `.claude/rules/frontend.md`).

## Inside this repository

Read these alongside the list, in any sprint:

- [Glossary](../glossary.md) and [wording](../wording.md): the terms and the rules for writing about entities.
- [Case notes](cases/README.md): three real cases drawn as graphs of roles.
- [Architecture overview](../architecture/overview.md): the components, the four contracts and how they connect.
- [Sources and how to cite](../sources/README.md).

## Sources

- [fatf_egmont_concealment_2018] FATF and Egmont Group, *Concealment of Beneficial Ownership*, 2018. Address in the bibliography; link to be added after a person opens it in a browser. Executive summary and Annex E: <https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-Executive-summary.pdf>, <https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf>
- [fatf_pml_2018] FATF, *Professional Money Laundering*, 2018. Address in the bibliography; link to be added after a person opens it in a browser.
