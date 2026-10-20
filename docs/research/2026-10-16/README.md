# NeonRadar research notes, 16 October 2026

These six notes are the evidence behind `docs/build/PHASE-1.md`. Research agents wrote them on 15 and 16 October 2026 by checking official sources (package registries, release tags, documentation sources and publishers' pages). Each fact carries a source tag, and the notes mark anything they could not confirm as UNVERIFIED.

| Note | What it covers | Used by |
|---|---|---|
| `stack.md` | Versions and tooling: Neo4j release lines, Python, uv, FastAPI, Vue, Vite, TypeScript, Playwright, GitHub Actions, memory sizing | sections 3 and 4, M1.3 to M1.6, M1.9d |
| `neo4j.md` | Neo4j Community in Docker, APOC and GDS, constraints, Cypher 5 versus Cypher 25, bulk loading, the Python driver, Testcontainers | M1.4, M1.7b, M1.9a |
| `sources-ch-gleif.md` | Companies House and GLEIF: endpoints, fields, enumerations, rate limits, licences, spikes; notes on OpenCorporates and Open Ownership | M1.8a, M1.8b, ADR-0006 |
| `sources-opensanctions-ftm-icij.md` | OpenSanctions licensing and formats, FollowTheMoney 4.x, the ICIJ Offshore Leaks files and licence | M1.7a, M1.8c, M1.8d, ADR-0003, ADR-0006 |
| `synthetic-docs-mcp.md` | Synthetic AML data generators, Faker findings, documentation site tooling, the Neo4j MCP server, the Claude Code GitHub Action | M1.2, M1.6, M1.8e, ADR-0005, ADR-0012 |
| `aml-domain.md` | Primary AML sources, typology definitions, terminology, disclaimers, real cases | section 7, M1.10, M1.11 |

## Where the build spec decided differently

The spec wins where it differs from a note; the notes keep what was found on the day.

1. **Neo4j version.** `stack.md` recommends `neo4j:2026.09.0-community` and marks the 5.26 support date as unverified; `neo4j.md` recommends `neo4j:5.26.32-community` and cites Neo4j's statement that 5.26 is supported until June 2028. The spec pins 5.26.32 (ADR-0002).
2. **Spike defaults.** `sources-ch-gleif.md` uses HSBC Holdings plc and HSBC Bank plc as worked examples. The spec uses British Telecommunications instead (company 01800000, LEI 549300OWFMSO9NYV4H90, whose direct and ultimate parent is BT GROUP PLC, LEI 213800LRO7NS5CYQMN21), checked against the GLEIF API on 16 October 2026, so that the project's spike reports do not feature a bank.
3. **FollowTheMoney records.** A check with followthemoney 4.11.0, made after the notes were written, found that `model.make_entity()` returns an `EntityProxy` whose output has no `datasets` key. The spec builds records with `ValueEntity` (section 3.2).
4. **ICIJ disclaimer.** `aml-domain.md` section 4 and `sources-opensanctions-ftm-icij.md` C.3 quote it with one word different ("persons" and "individuals"). Re-fetch the FAQ before quoting it.
5. **Scale figure.** The "5 percent of global GDP" figure in the project plan is the IMF's 1998 range as cited by UNODC; UNODC's own estimate is about 2.7 percent of global GDP for 2009 (`aml-domain.md` section 0, item 6).
6. **Sanctions exposure.** The multiplicative ownership pattern in `aml-domain.md` 2(i) is kept as a teaching metric; the spec (7.2) adds that the OFAC rule aggregates all blocked owners and treats an entity owned 50 percent or more by them as blocked.
7. **Python.** Some notes' scope lines say Python 3.12 or later; the spec pins Python 3.14, as `stack.md` recommends.

## Before you rely on a fact

These notes are a snapshot. Versions, rate limits, licences and court outcomes change. Re-check anything time-sensitive against its source before building on it, and record what changed in the pull request (PHASE-1.md 2.7).
