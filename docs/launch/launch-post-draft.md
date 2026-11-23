# Launch post: draft

**Status: draft, not for publication.** The [project plan](../plan/neonradar-project-plan.md) asks for a launch post that leads with three things that make NeonRadar notable. As of `dev` at `2cbd71c` (23 November 2026), only the first one runs, and only on synthetic data. The article below is written for launch day:

- Every part that depends on work that has not merged yet is marked **[DO NOT PUBLISH UNTIL ...]**, and every number or name not known yet is a **[placeholder]**.
- Remove a marker only when its condition is true. **If a condition is still false on launch day, delete everything that marker covers, including its section heading where the marker opens a section.**

## Before publishing

| Claim in the post | True today? | What must be true before it is published |
|---|---|---|
| Ownership and money in one graph | On the synthetic demo only. The Companies House, GLEIF and ICIJ loaders are merged but have not run on real data ([OD-22](../build/operator-decisions.md)) | Say "synthetic" wherever it is still true |
| Published precision and recall | No. The detector evaluation (on synthetic worlds) and the entity-resolution precision (on human-labelled real pairs) are planned, not run | The evaluation reports are published; copy their figures, intervals and counts exactly, with links |
| Questions answered with the evidence | No. The copilot is a placeholder on `dev` | The copilot milestones have merged; describe only what they ship |
| Alerts about real people are withheld | A rule in the build spec ([PHASE-3.md](../build/PHASE-3.md) G12); no withholding code on `dev` yet | The withholding has merged |
| Pattern count | One pattern runs today (circular flow); 15 explainers are drafts | Use the number of detectors merged on launch day, and say "draft" if the explainers are still drafts |
| Repository address | Public at `Robotat-Technologies/neon-radar`; the final organisation name is still pending ([OD-7](../build/operator-decisions.md)) | Use the address the repository has on launch day |
| "Nobody has open sourced this" (plan wording) | Not checked | Leave it out unless someone checks it and records the sources |
| Who built it | `CONTRIBUTORS.md` is empty | Fill it from `CONTRIBUTORS.md`, with each person's agreement to be named and linked |

The one sentence of the standing disclaimer quoted below is word for word, as [wording.md](../wording.md) requires; the full text is in `contracts/wording/standing-v1.txt`. The post makes no claim about money laundering itself, so it needs no bibliography keys. If an editor adds one, cite it.

---

# NeonRadar: follow the money on your own laptop

**An open-source graph investigation toolkit for anti-money-laundering and anti-corruption work, built with AI agents in a public repository and released under Apache 2.0.**

NeonRadar is a reference project that wires open data and open-source tools into one system you can run yourself. It puts companies, people, addresses, accounts and payments in one graph, finds structures that match documented money-laundering patterns, and explains every match with its evidence and its sources. After the first setup, which downloads its components, it runs offline and sends nothing anywhere.

It is for people who follow money without a software budget: non-profits and civil society, newsrooms, universities, financial intelligence units and anti-corruption agencies, and small firms that need somewhere to start.

## 1. Ownership and money in one graph

Who owns a company and where its money goes are usually two separate investigations. In NeonRadar they are one graph: companies, directors and registered addresses sit next to accounts and payments, so a single query can follow a payment to an account, to the company that holds it, to the people who direct it.

On launch day you can see this on a synthetic world, where every company, person, account and payment is invented. **[DO NOT PUBLISH UNTIL real registers have run. Then add which ones (for example "UK Companies House, the GLEIF index and the ICIJ Offshore Leaks Database"), and keep "payments are always synthetic".]**

**[DO NOT PUBLISH UNTIL the evaluation reports are published.]**

## 2. Numbers you can check

A detection tool is only as good as its error rates, so we publish ours. For each pattern: how many planted scenarios it found (recall) and how many of its alerts were right (precision), measured the same way every time on synthetic worlds: **[figures and intervals from the report]**. Those numbers describe synthetic data and say nothing about how NeonRadar would perform on real data.

For matching the same company or person across public registers, precision was measured on **[number]** real pairs that people labelled: **[figure, its Wilson 95 percent interval and the number of pairs labelled "unsure"]** ([PHASE-2.md](../build/PHASE-2.md) 7.3).

**[DO NOT PUBLISH UNTIL the copilot milestones have merged; describe only what shipped.]**

## 3. Ask a question, get the evidence

Type a question such as "Who owns this company?" and NeonRadar answers from the graph, with the evidence subgraph and the exact queries attached, so you can check the answer instead of trusting a paragraph. It answers a fixed set of question types from reviewed templates. No language model writes a query or an answer. It asks which entity you mean rather than guessing, and refuses questions about guilt, risk, predictions, decisions or personal details ([PHASE-4.md](../build/PHASE-4.md), G13 and G14).

## Honest by design

NeonRadar describes patterns and never makes accusations. Every page that shows alerts or entities carries the standing disclaimer, which says: "A pattern match is not evidence of money laundering, corruption or any other wrongdoing." Planted scenarios run only among synthetic entities. NeonRadar is not a compliance system and makes no one compliant with anything.

**[DO NOT PUBLISH UNTIL the withholding has merged:]** Every payment in NeonRadar is synthetic. So an alert that rests on payments and involves a real entity is withheld and only counted, and so is any alert whose subject or evidence is a real person.

**[DO NOT PUBLISH UNTIL `docs/faq.md` has merged:]** More in the FAQ, with a link.

## Try it

On macOS, Linux or WSL 2, with Docker, uv, Node.js 24 and the ICU headers, `make setup` and then `make demo-mini` start the synthetic demo and print where to open it. The [quickstart](../quickstart.md) has the full list. The code is at **[repository address on launch day; today github.com/Robotat-Technologies/neon-radar]**, and issues labelled `good first issue` are a place to start.

## How we built it

Most of the code was written by AI agents, openly labelled, working from the build spec in the repository. Every agent pull request names an accountable human, humans review merged work, and decisions that need judgement (approving a pattern definition, freezing a contract, confirming a licence) stay with people ([README](../../README.md), "How we build").

NeonRadar stands on open-source work, including FollowTheMoney, Neo4j, Splink, DuckDB, FastAPI, Vue and Cytoscape.js. Each data source keeps its own licence ([DATA_SOURCES.md](../../DATA_SOURCES.md)).

## Who built it

**[placeholder: one line per person from CONTRIBUTORS.md, with what they owned and a link to their GitHub profile, only for people who agreed to be named.]**
