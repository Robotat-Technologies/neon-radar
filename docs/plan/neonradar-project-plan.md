> Exported on 16 October 2026 from the project plan document (revision 36) for `docs/plan/`. Where Phase 1 deliberately differs from this plan, `docs/build/PHASE-1.md` section 0.5 says so, including the corrected UNODC figure.

# NeonRadar: Open Source Project Plan

Oct 13, 2026 · @Alaaddin

## Why this project

Money laundering is a network problem, and most production systems still examine one transaction at a time. That gap is our opening.

The United Nations Office on Drugs and Crime estimates that as much as 5% of global GDP is laundered each year, around $2 trillion ([Quantexa](https://www.quantexa.com/resources/holistic-view-of-financial-crime/)). Rules-based transaction monitoring catches very little of it and buries analysts in false positives, because a transaction viewed alone carries no context. The actual signal lives in relationships: shared addresses, recycled directors, shell company chains, circular payments, mule rings. Those are graph structures, and graph queries find them in ways that row-by-row scoring cannot.

The approach is commercially proven. Quantexa was ranked #7 in the Chartis Financial Crime and Compliance 50 for 2026, with entity resolution and network analytics named as its key differentiators ([Quantexa press release](https://www.quantexa.com/press/quantexa-ranked-7-in-chartis-fcc50-2026-and-named-category-leader-in-enterprise-fraud-solutions/)). The timing is also good: the EU Anti-Money Laundering Regulation applies directly in all 27 member states from 10 July 2027, forcing a wave of customer due diligence, beneficial ownership and entity identification work ([compliance guide](https://rapidlei.com/eu-aml-package-readiness/)).

Every serious implementation of this is closed source and costs millions. The open source pieces exist in isolation (OpenSanctions, FollowTheMoney, Splink, Neo4j GDS), but nobody has wired them into one runnable system that goes from raw public data through entity resolution to a graph, typology detection and an explainable investigation. That is the gap, and it is the right size for 15 people over 28 working days.

**What "reference project" means here.** Not "we built an AML tool." It means three things we can measure:

1. **It runs.** A stranger clones the repo and has a populated Neo4j graph with working detections in under 10 minutes, one command.
2. **It teaches.** The documentation explains the money laundering typologies and the graph patterns that catch them, so the repo is readable as a course, not just a codebase.
3. **It is honest.** Synthetic data for anything resembling an accusation, clear limitations, and no claim to be a certified compliance system.

## Mission

**Graph-based financial crime investigation should not be something only rich institutions can afford.**

The tools that trace hidden ownership through shell company chains cost millions of dollars a year. The countries losing the most to corruption are the least able to buy them. That asymmetry is the whole problem: money launderers operate across borders with professional help, while the people investigating them are funded nationally, often poorly, and sometimes not at all.

We are building this for the people on the wrong side of that asymmetry:

- **Anti-corruption agencies and financial intelligence units** in countries without a software budget
- **Investigative journalists** working on cross-border ownership and asset tracing
- **Civil society and asset recovery organisations** following stolen public money
- **Academics and students** who currently have no realistic way to learn this field hands on
- **Small fintechs and regulated firms** who need to start somewhere

**The mission has design consequences, which is what makes it real rather than a slogan:**

1. **It runs on a laptop.** No cloud account, no bill, no vendor. If it needs infrastructure someone has to pay for, it has failed the people it is for.
2. **It works offline and phones home to nobody.** No telemetry, no analytics, no outbound calls. A journalist investigating their own government cannot use a tool that reports back, and neither can an agency handling live case data.
3. **Your data stays yours.** Everything runs locally. We never see it, and the architecture makes that structurally true rather than a promise in a privacy policy.
4. **Names across scripts and languages are a first-class problem, not an afterthought.** Matching the same person written in Arabic, Cyrillic and Latin transliteration is the single hardest and most important part of real corruption investigation, and most tooling built for Western markets handles it badly. This is where a team in our region has an advantage that a Silicon Valley project does not, and it should become one of the things the project is known for.
5. **The documentation teaches the subject, not just the software.** Someone who has never heard of layering should be able to learn what it is from our docs.
6. **Apache 2.0, permanently.** No open core, no paid tier of the real features, no rug pull.

**What we are explicitly not claiming.** This is not a regulated compliance system and it does not make anyone compliant with anything. It does not accuse people. It surfaces structures and patterns for a human investigator to judge, and the documentation says so in plain words on every page where it matters.

There is a practical argument for the mission too, not only a moral one. People contribute their weekends to missions. Nobody contributes their weekend to a technology demonstration. If we want outside contributors after 20 November, this section is the reason they will show up.

## What we are building

One repository, four layers, built in dependency order so that each layer is demonstrable on its own even if the next one never ships.

The product is a graph-native AML investigation platform. You search for a company or a person, you see the network around them (owners, directors, shared addresses, counterparties, payments), the system flags the patterns that match known laundering typologies, and you can ask it a question in plain English and get an answer with the graph path that justifies it.

| Layer | What it delivers | Priority |
| --- | --- | --- |
| 1. Ownership graph | Companies, people, addresses, beneficial ownership chains, sanctions and PEP matches, loaded from real public registries. Entity resolution so one person appearing in four sources becomes one node. | Must ship |
| 2. Transaction layer | Accounts and payments over synthetic data, attached to the entities from layer 1. Detections for structuring, layering, circular flows, mule rings and rapid pass-through. | Must ship |
| 3. Investigation copilot | Natural language question in, Cypher out, answer plus the subgraph that supports it. Grounded in the graph so it cannot invent relationships. | Showcase |
| 4. Explorer UI | Vue 3 app: entity search, interactive network canvas, alert queue, one-click "explain this alert". | Showcase |

**Why this order matters.** Layer 2 is where the eye-catching detections live, but layer 2 without layer 1 is just a toy transaction simulator, which already exists. The thing nobody has open sourced is the combination: a payment that is boring on its own becomes interesting when the graph knows that the sender and the receiver share a director with a sanctioned entity. That join is the whole argument of the project.

**Explicitly out of scope.** Real customer or bank data of any kind. Machine learning model training (graph algorithms and rules only, which keeps it explainable). Any claim of regulatory compliance or certification. Real-time streaming ingestion. A hosted public demo instance that holds user data.

## What exists on 20 November

The full inventory, so nobody has to guess what "done" looks like and so the launch post writes itself.

**What a person can actually do with it**

1. Search any company or person and see their whole network on one canvas: owners, directors, addresses, counterparties, payments
2. Trace beneficial ownership through multiple layers of shell companies to whoever is really behind an entity
3. See sanctions and politically exposed person exposure through indirect connections, not just direct name matches
4. Find the same person across four data sources and three spellings, resolved into one node
5. Run 10 laundering typology detections and get a ranked alert queue
6. Open any alert and see the exact subgraph that triggered it, so the finding can be checked rather than trusted
7. **Ask a question in plain English and get an answer with its evidence attached**, for example "who connects these two companies" or "show me circular payments involving this address"
8. Load their own country's registry data with their own API key
9. Run all of it on a laptop, offline, with nothing reported back to us

**What the team will have produced**

| Thing | Count |
| --- | --- |
| Public data source loaders, plus a synthetic transaction generator | 4 plus 1 |
| Graph schema, documented and frozen, with an entity resolution pipeline and a published precision figure | 1 |
| Laundering typology detections, each with a test fixture | 10 |
| Evaluation harness reporting precision and recall per typology | 1 |
| Natural language investigation copilot over the graph | 1 |
| Vue 3 explorer: search, network canvas, alert queue, explain panel | 1 |
| One-command Docker setup plus a devcontainer | 1 |
| Plain-language typology explainers, each with a citation | 10 |
| Architecture document, quickstart, contributing guide, data source register | 4 |
| Architecture decision records | 8 or more |
| Open issues labelled for newcomers | 15 or more |
| Learning logs, exit posts, and credited contributors | 15 each |
| Teach-back sessions recorded | 6 |
| Demo video and launch post | 1 each |

**The three things that make it notable**, and worth leading the launch post with: the ownership and transaction layers joined in one graph, which nobody has open sourced; published precision and recall numbers, which almost no project in this space publishes; and a natural language investigation experience that returns the evidence subgraph rather than a paragraph you have to trust.

## Assumptions to confirm

These drive the plan. If any is wrong, the timeline changes before anyone writes code.

1. **People.** 15 interns build, 3 to 4 senior engineers act as squad mentors and PR reviewers. Interns are available roughly full time on this; mentors are not, so mentor time is the scarcest resource in the plan and reviews are the likeliest bottleneck.
2. **Dates.** Kickoff Wednesday 14 October 2026, public and working Friday 20 November 2026. That is 28 working days.
3. **Stack.** Python 3.11+ for ingestion, resolution and detection. Neo4j 5.x as the graph store, with the Graph Data Science library. Vue 3 and Vite with Cytoscape.js for the explorer. Docker Compose so the whole thing starts with one command.
4. **Skill level.** The team has had an introduction to knowledge graphs and basic Cypher. Nobody is assumed to know AML. The analysis phase closes that gap deliberately.
5. **AI assistance.** Claude or similar is used openly throughout. The plan assumes AI writes most first-draft code, which is why the schedule is aggressive and why review capacity, not typing speed, is the constraint.
6. **Licence and ownership.** Apache 2.0, published under the company GitHub organization, with every contributor credited.

**Open questions for you before kickoff:** Which GitHub organization? Who are the named mentors? Is there a budget for a Neo4j AuraDB instance, or is everything local Docker? Do interns have a daily time block reserved, or are they fitting this around other work?

## Team structure

Six squads of two or three people, each owning one directory in the repo and one line in the demo. Small squads because 15 people on a shared codebase for 28 working days will deadlock otherwise.

| Squad | People | Owns in repo | Must deliver by 20 Nov |
| --- | --- | --- | --- |
| Data Ingestion | 3 | `/ingest` | Working loaders for 4 public sources plus a synthetic transaction generator, all producing the same intermediate format |
| Graph and Entity Resolution | 3 | `/graph` | The Neo4j schema, constraints and indexes, the loader, and entity matching that collapses duplicates across sources |
| Typologies and Detection | 3 | `/detect` | A documented catalog of 8 to 10 laundering typologies, each with a Cypher or GDS query that finds it, each with a test |
| Investigation Copilot | 2 | `/copilot` | Plain-English question to Cypher to grounded answer, with the supporting subgraph returned alongside |
| Explorer UI | 2 | `/ui` | Vue 3 app: entity search, network canvas, alert queue, explain panel |
| Docs, DX and Launch | 2 | `/docs`, root, CI | One-command setup, the README that sells the project, tests in CI, demo video, launch post |

**Cross-cutting roles**, held alongside squad membership:

- **Project lead (you).** Owns scope, kills work when the schedule slips, runs the daily standup.
- **Tech lead (senior engineer).** Owns the graph schema decision and the repo structure. Final say on architecture so six squads do not negotiate it six times.
- **Squad mentor (senior engineer, one per two squads).** Reviews PRs, unblocks, does not write the squad's code.
- **Release manager (one intern, rotates weekly).** Owns `main` staying green, cuts the demo build, runs the Friday demo.

**Where non-developers fit.** These are real roles with real deliverables, not consolation prizes, and the project visibly fails without them:

- **Typology researcher** (in Detection). Reads FATF and Europol typology literature, writes the plain-language description of each laundering pattern, defines what the detection must catch and what a false positive looks like. The developers cannot write the query until this person has written the definition.
- **Technical writer** (in Docs). Owns the README, the quickstart, the typology explainers. On a reference project the documentation is most of the product.
- **Data steward** (in Ingestion). Owns licence checking on every data source, the attribution file, and the synthetic data guarantees. This is the role that keeps us out of trouble.
- **Demo producer** (in Docs). Owns the story the demo tells, the scripted walkthrough, and the recorded video. Decides what the world sees first.
- **Community manager** (in Docs). Writes `CONTRIBUTING.md`, labels good first issues, sets up the issue and PR templates. Determines whether outside contributors ever show up.

Everyone, developer or not, is expected to open pull requests. Prose, documentation, typology definitions, test fixtures and data licence notes all go through the same PR flow as code.

## Timeline

&#91;embedded content: project timeline · 4 sprints, 4 gates\]

Every sprint ends on a gate. A gate that is missed triggers the next cut on the kill list that same day. The extension from 6 to 20 November buys quality and slack, not more scope: the extra two weeks go to the evaluation harness, the documentation, UI polish and the learning track. The kill list still stands.

**Sprint exit criteria**

- **Sprint 0, 14 to 23 October.** Graph schema frozen and merged. Repo scaffolded with CI, branch protection and a devcontainer. All four data sources fetched end to end in a spike. Every one of the 15 has a merged pull request and a learning log started.
- **Sprint 1, 26 October to 4 November.** Ownership graph loads from two or more sources. Entity resolution running with a published precision number. Synthetic transactions generated and attached to real entities. First three detections correct on a known fixture.
- **Sprint 2, 5 to 13 November.** Eight or more typologies detected, each with a test. The evaluation harness reports precision and recall per typology against labelled synthetic data. Copilot answers the benchmark questions.
- **Sprint 3, 16 to 20 November.** UI complete, feature freeze on 17 November, definition of done fully ticked, demo video recorded, repository public and launch post published on 20 November.

## Data strategy

Real public data for the entity layer, fully synthetic data for anything that looks like an accusation. The repository ships loaders, never bulk copies of the data itself.

| Source | What it gives us | Licence check |
| --- | --- | --- |
| [OpenSanctions](https://www.opensanctions.org/) | Sanctions lists, politically exposed persons, criminal watchlists, already modelled in the FollowTheMoney ontology | Non-commercial terms apply to the dataset. Data steward confirms before launch and records it in `DATA_SOURCES.md` |
| [UK Companies House API](https://developer.company-information.service.gov.uk/) | Companies, officers, persons with significant control, registered addresses. The cleanest free beneficial ownership source in the world | Open Government Licence, free API key |
| [GLEIF](https://www.gleif.org/en/lei-data/gleif-concatenated-file) | Legal Entity Identifiers and direct or ultimate parent relationships, global coverage | Public domain, no restriction |
| [ICIJ Offshore Leaks](https://offshoreleaks.icij.org/) | Offshore entities, intermediaries, officers and addresses from the Panama and Pandora Papers. Already a graph | ODbL, attribution required |
| [IBM AMLSim](https://github.com/IBM/AMLSim) | Multi-agent simulator that generates synthetic banking transactions with known laundering patterns and labels | Apache 2.0, so we generate our own data and avoid redistribution questions entirely |
| [IBM AMLworld on Kaggle](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml) | Six large labelled synthetic datasets, up to 180 million transactions, useful as a scale benchmark | CDLA-Sharing-1.0, a share-alike licence. Reference only, do not vendor into the repo |

**The piece that does not exist yet, and that we must build.** Every synthetic AML generator produces transactions between anonymous account numbers. Every public registry gives entities with no transactions. Nobody joins the two. Our generator creates synthetic accounts and payments that are **owned by the real entities already in our graph**, so a laundering chain can run through a genuine shell company structure from Companies House. That join is the project's actual contribution, and it belongs to the Ingestion squad as their highest priority deliverable.

**Guardrails, non-negotiable:**

1. **No real entity is ever labelled suspicious.** Detections run against the synthetic transaction overlay. Where a pattern touches a real company, the output says "structural pattern present" and never "money laundering", and the UI shows a standing disclaimer.
2. **The public demo uses synthetic entities only.** Real registry data is for people who run the loaders themselves.
3. **Ship loaders, not data.** Public registry records about real people remain personal data under GDPR. The repo contains fetch code and small test fixtures, never a bulk dump.
4. **Every source is logged.** `DATA_SOURCES.md` records source, licence, retrieval date and attribution text. The data steward owns this file and it gates the launch.
5. **One honest limitations section** in the README: synthetic transactions are not real laundering, detection rates here say nothing about real-world performance, and this is not a certified compliance system.

## Architecture

&#91;embedded content: system architecture · sources to graph to investigation\]

Each box is one squad's directory, and the arrows are the contracts between them. The contracts are agreed during the analysis phase precisely so that six squads can build in parallel without waiting on each other.

**Why Neo4j and not a relational store.** The queries we need are variable-depth traversals: find every company within four ownership hops of a sanctioned entity, find payment cycles of length three to six, find the shortest path between two people through any relationship. Those are one line of Cypher and an ugly recursive mess in SQL. The Graph Data Science library then gives us community detection and centrality for free, which is how mule rings surface.

**The repository**

```markdown
/ingest      loaders per source, plus the synthetic generator
/graph       schema, constraints, entity resolution, Neo4j loader
/detect      typology queries, each with a fixture and a test
/copilot     question templates, Cypher generation, grounding
/ui          Vue 3 explorer
/docs        typology explainers, architecture, quickstart
/data        small fixtures only, never bulk data
CLAUDE.md    shared context for AI sessions
docker-compose.yml
```

**Contracts to freeze in the analysis phase:** the intermediate record format that every loader emits, the full Neo4j schema, the REST API shape between detection and the UI, and the alert object that the copilot explains. Four agreements, and everything else can move.

## How people contribute, and why it will feel real

The risk you named is the right one: when AI writes the first draft of everything, people can finish a sprint feeling like they typed nothing that mattered. The fix is not to ban AI or to hand-write code for ceremony. It is to move ownership from *who typed it* to *who decided it and who can defend it*, and then to make that ownership visible in the repository forever.

**The rules of the repo:**

1. **`main` is protected.** No direct pushes, including from you and the tech lead. Every change arrives as a pull request.
2. **Every PR has one named author and one named human reviewer.** The reviewer is from a different squad, so people read each other's work and learn the whole system.
3. **`CODEOWNERS` names a person for every directory.** GitHub then auto-requests that person on any PR touching their area. Being automatically consulted about your module is the thing that actually feels like ownership.
4. **Issue first, then PR.** Each squad writes its own issues during the analysis phase and assigns them by name. People pick up work they helped define, which is very different from being handed a ticket.
5. **The author must be able to explain every line.** This is the rule that makes AI-assisted work feel earned. The reviewer's job is to ask "why this and not that", and "the AI wrote it" is not an answer. If the author cannot defend a decision, the PR goes back and they go learn it. This is also how they actually learn Neo4j and AML rather than watching it happen.
6. **Documentation is a contribution.** The person who writes the typology explainer for smurfing has contributed as much as the person who wrote the Cypher that detects it, and their PR count says so.

**Visible credit, by design:**

- **`CONTRIBUTORS.md` is a ledger, not a list of usernames.** One line per person naming what they owned: "Sara: entity resolution pipeline, Splink configuration, 12 PRs." That file is what people send to recruiters.
- **Every module's README section is written by its owner, in their own words.** This is the single cheapest way to produce the feeling of authorship, and it also makes the documentation good.
- **Conventional commits and a generated changelog**, so the release notes read as a narrative of who built what.
- **Friday demo, every week, run by the squads.** Each squad shows its own piece working, to the whole company. Six demos across the project. People remember demos; they do not remember merged PRs.
- **Launch post names everyone**, with links to their GitHub profiles.

**For outside contributors**, which is the test of whether this is really a reference project: `CONTRIBUTING.md` on day 3, not on the last day. Issue and PR templates. At least 15 issues labelled `good first issue` that we deliberately leave unclaimed, so an outsider arriving on 21 November finds somewhere to start.

**A note on AI use.** We use it openly and say so publicly in the README. The honest framing is that this team of 15 shipped in 28 working days what would have taken months, because AI removed the typing and left the thinking. That is a more interesting story than pretending otherwise, and it is also what people want to read about in 2026.

## Working method: AI writes the modules, humans own them

AI generates most of the modules. That is the explicit plan, not a fallback, and it means the bottleneck is review and comprehension rather than typing. Everything below follows from that one fact.

**Set the shared context once, on day 1.** A `CLAUDE.md` at the repo root holding the graph schema, naming conventions, directory layout and code style. Everyone's AI session then reads the same context and produces code that fits together, instead of six squads generating six incompatible styles. Updating this file when the schema changes is the tech lead's job and it is the highest-leverage 20 minutes in the project.

**Spec before generation.** Each module gets a one-page spec (inputs, outputs, failure cases) written by a human and merged as a PR before any implementation is generated. This is why the analysis phase exists. Generating code against a vague intention produces something that looks finished and is wrong, and you lose more time reviewing it than you saved.

**Tests are the contract.** The human writes or approves the test, AI writes the implementation. A test the AI wrote to match code the AI wrote proves nothing.

**Four things AI does not decide:**

1. The graph schema. One human decision, made once, by the tech lead, because everything else depends on it.
2. AML typology definitions. These come from reading FATF, Europol and Wolfsberg material. Every factual AML claim in our documentation must carry a citation to a real source. Models produce confident and wrong laundering typologies, and a reference project that teaches wrong AML is worse than no project.
3. Data licensing. Human reads the licence.
4. Anything in the guardrails section of the data strategy.

**Watch for these failure modes specifically.** Cypher that runs and returns plausible rows but encodes the wrong traversal, which is invisible without a test fixture where you know the right answer. Invented Neo4j GDS function signatures. Confident but fictional AML regulations or typology names. All three are caught by review and by fixtures, neither of which is optional.

**Pair on hard things.** Two interns, one driving the AI session, one reading output in real time. Slower per hour, much faster per correct line, and it is how the less experienced half of the team learns.

## Where AI agents fit

Agents appear in this project in three distinct places, and conflating them causes confusion, so they are separated here.

**1. Agents that write the code.** Beyond chat assistance, an agent can work directly in the repository, read the codebase, run tests and open its own pull requests. This is where most of the 28 day schedule is bought back.

Good work to hand an agent is work that is well specified and cheaply verifiable:

- Writing a data loader from an API specification, where the test is whether the records come out in the agreed format
- Generating test fixtures and synthetic edge cases
- Propagating a schema change across every query and test in the repo, which is tedious, error prone and exactly what people hate doing
- Keeping `CLAUDE.md`, docstrings and the architecture document in sync with the code
- First drafts of typology explainers, which a human then fact-checks against the FATF source

Work to keep away from agents is work where being wrong is cheap to produce and expensive to notice: detection logic before the fixture exists, the schema itself, data licence calls, and anything in the mission guardrails.

**The rule that keeps credit honest:** an agent-opened PR is labelled `agent` and still has a named human owner who reviews it, defends it and is accountable for it. No agent PR is ever merged without that owner. The repository history then shows plainly what the agent drafted and who stood behind it, which is more interesting and more honest than hiding it.

**2. An agent in CI, which protects the real bottleneck.** The plan's scarcest resource is mentor review time. A review agent running on every pull request can check the mechanical things before a human looks: is it under the size limit, are there tests, is the documentation updated, does it touch the frozen schema, are there secrets in the diff. Mentors then spend their attention on judgment rather than on hygiene. Set this up in sprint 0 and it pays for itself by week two.

**3. The agent that is the product.** The investigation copilot is itself an agent, and it is a particularly defensible kind: it writes Cypher against a graph it can execute and verify, and it returns the subgraph as evidence. An agent grounded in a queryable graph is a fundamentally safer pattern than an agent generating prose, because the graph can contradict it. That argument is worth making explicitly in the documentation, because it is the intellectual case for the whole project.

**Measure it and publish it.** Record what share of merged pull requests were agent-drafted, and put that number in the README with a short note on what worked and what did not. Almost nobody publishes this honestly. A team of 15 interns shipping a working system in 28 days, with the agent contribution measured rather than claimed, is a story people will actually read.

**After launch**, an agent triaging and labelling incoming issues is what makes a three-month maintenance commitment from two people realistic rather than aspirational.

## Learning track

When AI generates the modules, learning does not happen by osmosis. It has to be installed deliberately, and it is the thing the 15 interns actually keep after 20 November. This track is as much a deliverable as the code, and it lives in the repository rather than in someone's notebook.

**Three mechanisms do the real work**, because each one forces the person to produce an explanation rather than accept one:

1. **Defending your pull request in review.** Already in the contribution rules. This is where "I generated it" turns into "I understand it."
2. **Writing the decision record.** Every non-obvious choice becomes a one-page file in `/docs/decisions/`, written by whoever made it: the context, the options considered, the decision, the consequences. Nobody writes a coherent one without actually understanding the trade-off. It doubles as project governance, which is why it is cheap.
3. **Teaching it back.** Thirty minutes every Thursday, two or three people present something they learned to the rest, so across six weeks everyone presents at least once. Recorded, and the good ones become documentation.

**The learning log.** Each person keeps `/docs/learning/<name>.md` and appends to it weekly: what they read, what they built, what they got wrong, what still confuses them. Three to five lines, submitted as a PR with their other work. Honest confusion is the most valuable content in these files, so it should be visibly welcomed rather than tidied away.

**Reading list by sprint**, short and mandatory, because an unbounded list gets ignored:

| Sprint | Everyone reads | The relevant squad also reads |
| --- | --- | --- |
| 0 | Neo4j graph data modelling guide, one FATF typology report, FollowTheMoney documentation | Companies House and OpenSanctions API docs |
| 1 | Cypher query tuning basics, how indexes and constraints work in Neo4j | Splink documentation and the Fellegi-Sunter record linkage model |
| 2 | Graph Data Science library overview: community detection, centrality, weakly connected components | Text to Cypher and GraphRAG patterns, and their failure modes |
| 3 | What makes an open source project usable by strangers | Technical writing for READMEs, Vue 3 composition API |

**Skills self-assessment, at the start and at the end.** A short matrix: graph modelling, Cypher, entity resolution, AML domain knowledge, Vue, Docker, code review, working effectively with AI. People score themselves 1 to 5 on day one and again on the last day. It gives each intern a visible delta, and it gives you evidence about what the internship actually taught, which is useful well beyond this project.

**Exit artifact.** In the final week each person writes a short post: what I built, what I learned, what I would do differently. These go into `/docs/learning/`, the best lines go into the launch post, and each person keeps something concrete to show for six weeks of work.

## Definition of done

The repository is not launched until every box below is ticked. The release manager owns this checklist and has the authority to delay the announcement.

**It runs**

- [ ] `docker compose up` brings up Neo4j, the API and the UI on a clean machine
- [ ] One command loads the full synthetic demo dataset in under 10 minutes
- [ ] A documented path exists for loading real public registry data with your own API key
- [ ] Tested on macOS and Linux by someone who did not build it

**It works**

- [ ] 8 or more typologies detected, each with a test fixture where the expected answer is known
- [ ] Evaluation harness publishes precision and recall per typology against labelled synthetic data, and the table is in the README
- [ ] Scale benchmark met and published: the target node and relationship counts, load time, and query latency, with the hardware stated
- [ ] CI green on `main`, running tests on every PR
- [ ] Copilot answers the 10 benchmark questions in `/docs/benchmark-questions.md` correctly
- [ ] UI loads an entity, renders its network, and opens an alert with its explanation

**It teaches**

- [ ] README explains what, why and how, with a screenshot or GIF above the fold
- [ ] Every typology has a plain-language explainer with a citation to a real AML source
- [ ] Architecture document explains the graph schema and the reasoning behind it
- [ ] `CONTRIBUTING.md`, issue and PR templates, and 15 or more open `good first issue` items

**It is honest**

- [ ] `DATA_SOURCES.md` lists every source with its licence, retrieval date and attribution
- [ ] Limitations section in the README, written plainly
- [ ] No real person or company labelled suspicious anywhere in the repo, the demo or the screenshots
- [ ] Apache 2.0 licence file, and `CONTRIBUTORS.md` naming all 15 people and what they owned

**It can be found**

- [ ] Two to three minute demo video in the README
- [ ] Launch post drafted and reviewed
- [ ] GitHub topics, description and social preview image set

**It taught**

- [ ] 15 learning logs in `/docs/learning/`, each with entries from every sprint
- [ ] Decision records in `/docs/decisions/` covering the schema, the resolution approach and the detection design at minimum
- [ ] Six teach-back sessions held, with everyone having presented at least once
- [ ] Skills self-assessment completed at both ends, deltas recorded
- [ ] 15 exit posts written

## Risks and the kill list

The single largest risk is that we ship four half-finished layers instead of two finished ones. The defence is deciding the cut order now, while nobody is emotionally attached to anything.

| Risk | Why it bites | What we do about it |
| --- | --- | --- |
| Entity resolution becomes a rabbit hole | Matching "J. Smith, London" across four sources is an unbounded research problem and it is genuinely interesting, which makes it worse | Timebox to 4 days. Fix on Splink with one agreed configuration. Accept roughly 80% precision and publish the number honestly. Freeze at the end of sprint 1 |
| Review capacity runs out | 15 people producing PRs against 3 or 4 part-time mentors. Everything stalls behind review | Interns cross-review by default, mentors only review PRs touching the schema, the API contract or security. Hard limit of 400 changed lines per PR |
| Schema churn late in the project | A schema change late in the project invalidates every query and every test at once | Schema frozen at the end of the analysis phase. Changes after that need tech lead sign-off and a migration note |
| A data source blocks us | Rate limits, a bulk file far larger than expected, or a licence that forbids what we planned | Day 2 spike: every source fetched end to end before any squad commits to it. A source that fails the spike is dropped that day, not weeks later |
| The copilot is unreliable | Natural language to Cypher is hard, and an impressive demo that fails live is worse than no demo | Constrain it to a library of parameterized question templates rather than open-ended generation. It refuses rather than guesses. It is showcase tier and it is on the kill list |
| People disappear | Exams, other assignments, holidays | Two or three per squad, never one. Every module has a named backup in `CODEOWNERS` |

**The kill list, in order.** At the end of each sprint, if the exit criteria were not met, the next item on this list is cut that day. No debate, because we agreed in advance:

1. UI polish. The explorer drops to a basic functional view, and the demo uses Neo4j Bloom screenshots for the pretty pictures.
2. The copilot becomes a fixed menu of parameterized queries with natural language labels, which still demos well and always works.
3. Typologies drop from 10 to 5, choosing the five that are most visually striking in a graph.
4. Data sources drop from 4 to 2: Companies House and OpenSanctions, which together already tell the whole story.
5. The explorer UI is cut entirely and the project ships as a library plus notebooks.

**Never cut, at any point:** one-command setup, the documentation, the honesty guardrails, the learning track, and crediting everyone. Those five are what make it a reference project and an internship rather than a demo. Everything else is a feature.

## Gaps the first draft missed

Nine things that were not in the plan and should be, now that there are 28 days rather than 18. The first three are the ones that decide whether this is credible or just impressive.

1. **An evaluation harness with published numbers.** This is the single largest gap. Our synthetic data is labelled, which means we can report precision and recall per typology and put that table in the README. Almost no open source AML project does this, and it is the difference between "look at our graph" and "here is how well it works, measured." One script, one table, run in CI. Assign it to the Detection squad in sprint 2.
2. **A stated scale target.** Without a number, "it works" cannot be falsified. Propose: 500,000 nodes and 2 million relationships, loading in under 10 minutes on a 16GB laptop, with every demo query returning in under 2 seconds. Publish the benchmark and the hardware it ran on.
3. **Security basics, from day one.** No API keys in the repository, `.env.example` only, GitHub secret scanning and Dependabot both on, and the default Neo4j password changed in `docker-compose.yml`. A security hole in a financial crime project is the kind of thing people write about, and not the way you want.
4. **A developer environment floor.** Neo4j plus Docker needs real memory, and some interns will have laptops that cannot run the full dataset. Ship a devcontainer and a GitHub Codespaces config, plus a small dataset mode of about 10,000 nodes. Nobody should lose a week to their hardware.
5. **The project is called NeonRadar**, on `neonradar.com`, which we already own. Radar is the right metaphor for an alert queue and it gives the project an obvious visual identity from day one. Because the name says nothing about graphs, the one-line description has to carry that weight wherever it appears. Proposed: *open source graph investigation for the people fighting corruption*. Still to settle in sprint 0, since everything written afterwards depends on them: the GitHub organization and repository name, a social preview image, repository topics, and pointing the domain at the documentation site.
6. **Internal sign-off before publishing.** Publishing under the company organization needs whoever owns legal and communications to look at it first. Start that conversation in sprint 1, not on 19 November.
7. **Post-launch maintenance, committed in writing.** A reference project that stops answering issues in December stops being a reference. Name two maintainers and a three-month commitment to respond to issues within a week, and say so in the README.
8. **What "people talk about it" means in numbers.** Decide the target now so you can judge it later. A reasonable first set: 500 GitHub stars in 90 days, 10 contributors from outside the company, 3 external write-ups or newsletter mentions, and one university or bootcamp using it as teaching material.
9. **Two budgets nobody has set.** AI usage across 15 people for six weeks is a real cost, and so is a hosted Neo4j instance if you choose one over local Docker. Set both before kickoff rather than discovering them in week four.

**Launch mechanics**, which are worth more planning than they usually get: aim for a Tuesday to Thursday morning, US Eastern time. The Neo4j developer community actively features community projects and is the most receptive audience you have. Have the demo video, the README screenshot and the evaluation table all ready before the post goes anywhere, because a first visitor who sees a wall of text does not come back.

## Next steps

**Before kickoff, owned by you:**

- [ ] Confirm or correct the six assumptions above
- [ ] Create the GitHub organization and the empty repository, Apache 2.0, branch protection on day one
- [ ] Name the 3 or 4 mentors and tell them the review commitment is real
- [ ] Decide local Docker versus a hosted Neo4j AuraDB instance
- [ ] Register for a Companies House API key, since approval is not instant

**Kickoff, Wednesday 14 October, 90 minutes:**

1. Present this plan. Fifteen minutes, not an hour.
2. Announce squads and cross-cutting roles by name.
3. Walk through one real laundering case as a graph, on screen. This is what makes people care, and nothing else in the kickoff matters as much.
4. Everyone runs `docker compose up` before they leave the room. The person whose machine fails gets help there and then, not on Friday.

**Assignment 1, due Friday 16 October. Everyone, no exceptions.** Load a 20-row CSV into your local Neo4j, write one Cypher query that traverses at least two hops, and open a PR adding your name and your query to `/docs/team/first-queries.md`. The point is not the query. The point is that all 15 people have one merged pull request with their name on it by day 3, before the project gets hard.

**Assignment 2, due Monday 19 October.** Each person is assigned one money laundering typology, reads the FATF or Europol source material on it, and opens a PR with a one-page plain-language explainer including the citation. Fifteen people, fifteen typologies, and the team has collectively built the domain knowledge base that the Detection squad will work from. Nobody can write a detection query for a pattern they cannot describe in a paragraph.

**Then the analysis phase.** The next document we produce together is the analysis deliverable, and it is the one that decides whether the build weeks go smoothly. It should contain the graph schema with every node label, relationship type and property, the typology catalog with the graph pattern each one makes, the entity resolution approach, the data source specifications with field mappings, the API contract between the backend and the UI, and the module specs each squad builds against.

That document is what you hand the team to read before building starts, and it is where their assignment 2 explainers get folded in. Tell me when you want to start it.
