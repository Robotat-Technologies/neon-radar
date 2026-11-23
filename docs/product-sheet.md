# NeonRadar at a glance

**Open-source graph investigation for anti-money-laundering and anti-corruption work, on your own laptop.**

NeonRadar puts companies, people, addresses, accounts and payments in one graph, finds structures that match documented money-laundering patterns, and explains each match with its evidence and sources. It runs offline, sends nothing anywhere, and is free under the Apache 2.0 licence, with no paid tier.

## Who it is for

- **Non-profits and civil society** following money in anti-corruption or asset-recovery work, without a software budget.
- **Newsrooms** that need to see how companies, directors, addresses and payments connect, and to explain that picture to readers.
- **Universities**, for teaching how financial investigation works in practice, with plain-language pattern explainers, their primary sources and a learning track.

Financial intelligence units, anti-corruption agencies and small regulated firms are welcome too ([README](../README.md), "What it is").

## What you can do today

All of this runs on the synthetic demo: every company, person, account and payment in it is invented. You need macOS, Linux or WSL 2, Docker, uv, Node.js 24 and about 16 GB of memory ([quickstart](quickstart.md)).

- **Start it.** After `make setup`, `make demo-mini` builds the graph, runs detection and serves the explorer at http://localhost:8080.
- **Search and explore.** Find a company or person and open its network one to three steps out.
- **Read an alert.** Each alert shows the evidence graph, one explanation step per payment, its measures and the sources behind the pattern. Today one pattern runs: money that leaves an account and comes back through a chain of transfers.
- **See where data comes from.** The Data sources page lists each dataset with its licence and notice.
- **Use the API.** A read-only API with interactive documentation.
- **Learn the patterns.** Fifteen draft pattern explainers in plain language, each citing primary sources and awaiting review by a typology researcher, and case notes that draw public cases as graphs ([typologies](typologies/README.md), [learning](learning/README.md)).

## Being built

Not ready yet, so do not plan around it:
- public registers in the graph: loaders for UK Companies House, the GLEIF index and the ICIJ Offshore Leaks Database exist and are tested on synthetic data, but real-data runs wait until the data protection documents are filed and approved machines are listed ([OD-22](build/operator-decisions.md));
- official sanctions lists, matching one company or person across sources, and following ownership chains;
- more detection patterns, and answering plain-English questions with the evidence shown.

## What it is not

- **Not an accusation engine.** It shows structures for a person to judge. In the words of its standing disclaimer, "A pattern match is not evidence of money laundering, corruption or any other wrongdoing" ([wording.md](wording.md)).
- **Not a compliance system.** It is not regulated or certified and makes no one compliant with anything.
- **Not a home for real customer or bank data.** It uses public registers and synthetic transactions only.
- **Not machine learning, not real-time and not a hosted service.** No model training, so every result can be explained; no streaming; no public instance that holds user data.

## How it works for you

- **Local-first.** Your data stays on your machine; the only network calls are the data loaders you run yourself.
- **Open.** Apache 2.0, permanently. Each public source keeps its own licence, listed in [DATA_SOURCES.md](../DATA_SOURCES.md).
- **Honest about how it is built.** Mostly by AI agents, openly labelled. Every agent pull request names an accountable human, and humans review merged work ([README](../README.md), "How we build").

## Status and contact

Pre-release. Try it with the [quickstart](quickstart.md); questions and ideas go to the issues of [github.com/Robotat-Technologies/neon-radar](https://github.com/Robotat-Technologies/neon-radar). Security reports follow [SECURITY.md](../SECURITY.md).
