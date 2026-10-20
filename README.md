# NeonRadar

Open-source, local-first graph investigation for anti-money-laundering and anti-corruption work.

**Status:** Pre-release. Under construction until 20 November 2026.

> NeonRadar is an educational, open-source tool that finds structural patterns in synthetic or public data. A pattern match is not evidence of money laundering, corruption or any other wrongdoing. There are legitimate reasons for almost every structure shown here, including holding companies, shared registered agents, professional directors, payment intermediaries and cash businesses. Where public data is used, many people and entities share the same or similar names, and source registers contain errors. Nothing here suggests or implies that any identifiable person or entity has broken the law. NeonRadar is not a certified compliance system and does not make anyone compliant with anything. If you find an error in NeonRadar, tell us and we will correct it; errors in source data can only be corrected by the source, and we will tell you where to report them.

## What it is

Graph-based financial crime investigation should not be something only rich institutions can afford. NeonRadar is a reference project that wires open data and open-source tools into one runnable system, for anti-corruption agencies and financial intelligence units without a software budget, investigative journalists, civil society and asset recovery organisations, academics and students, and small fintechs and regulated firms that need to start somewhere.

- **An ownership graph** built from public registers (company registers, the GLEIF index, the ICIJ Offshore Leaks Database and, where licensed, sanctions lists), with entity resolution so that one person or company appearing in several sources becomes one node. Each source and its licence is listed in [DATA_SOURCES.md](DATA_SOURCES.md).
- **A transaction layer** of synthetic accounts and payments, and detections that show which structures in the graph match the graph patterns of documented money-laundering typologies, each with the evidence and an explanation.
- **An investigation copilot** that turns a plain-language question into a graph query and answers with the subgraph that supports the answer.
- **An explorer UI** for entity search, an interactive network view, an alert queue and an explanation of each alert.
- **Documentation that teaches the subject**, not only the software: what each typology is, where the definition comes from and which graph pattern finds it.

It runs on a laptop, with no cloud account and no bill. It works offline and phones home to nobody: no telemetry, no analytics, no outbound calls except the data loaders you run yourself. Your data stays on your machine. Names written in different scripts (Arabic, Cyrillic, Latin) are treated as a first-class matching problem. It is licensed under Apache 2.0, permanently: no open core and no paid tier.

## What it is not

- **Not a compliance system.** It is not regulated or certified, and it does not make anyone compliant with any law or regulation.
- **Not an accusation engine.** It surfaces structures and patterns for a human investigator to judge. It never says that a person or company did anything wrong.
- **Not a home for real customer or bank data.** It uses public registers and synthetic transactions only.
- **Not machine learning.** No model training: graph algorithms and rules only, so every result can be explained.
- **Not real-time.** There is no streaming ingestion.
- **Not a hosted service.** There is no public demo instance that holds user data.

## Limitations

Synthetic transactions are not real money laundering: every planted scenario is invented, and so is every payment in the demo. Detection rates measured on synthetic data say nothing about how NeonRadar would perform on real data. NeonRadar is not a certified compliance system and makes no one compliant with any law or regulation.

## Quickstart

Coming in Phase 1.

## How we build

NeonRadar is built mostly by AI agents (Claude Code), openly labelled as such, working from the build spec in [docs/build/](docs/build/), one milestone per pull request. Every agent pull request is labelled `agent` and names a human owner who is accountable for it. During the initial build, the operator has authorised the orchestrating agent session to merge a pull request after its acceptance checks pass, an independent review finds nothing left that affects correctness, the stated requirements or the project's guardrails, and CI passes (CI checks start partway through Phase 1). Humans review merged work afterwards. Humans own the decisions that need human judgement: freezing a contract, approving a typology definition, accepting an architecture decision record and confirming a licence decision, and people write their own learning logs, self-assessments, teach-backs, exit posts and assignment submissions. The operator decisions behind this are in [docs/build/operator-decisions.md](docs/build/operator-decisions.md). See [CONTRIBUTING.md](CONTRIBUTING.md) to take part.

## Licence

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Data loaded from public sources keeps its own licence; see [DATA_SOURCES.md](DATA_SOURCES.md).

To report a security issue, see [SECURITY.md](SECURITY.md). Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
