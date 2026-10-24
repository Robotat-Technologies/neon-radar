# Changelog

All notable changes to NeonRadar are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html); before 1.0.0, any minor version may change behaviour.

## [Unreleased]

## [0.1.0] - 2026-10-24

The first tagged pre-release: the Phase 1 foundation and the first part of Phase 2. Release notes, the demo commands, system requirements and the data notice: [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md). The demo holds synthetic data only; never use it to judge a real person or company.

### Added

- `make demo-mini`: the synthetic demo in Docker (Neo4j 5.26 Community with APOC Core and the pinned GDS 2.13.4 jar, the API and the UI on `127.0.0.1`), and `make demo-dev` without Docker.
- The explorer UI (Vue 3): entity search, entity networks, the alert queue and alert pages with evidence, with the standing disclaimer and the synthetic demo notice on every page.
- The read-only API `/api/v1` (contract C3 1.1.0): health, meta, search, entities, networks, alerts and typologies.
- The circular-flow detector and fifteen draft typology definitions in `detect/typologies/`.
- Contracts C1 record 1.1.0, C2 graph schema 1.2.0, C3 API 1.1.0 and C4 alert 1.0.0 (tag `contracts-v1.2.0`), with generated JSON Schemas and the OpenAPI snapshot.
- Registry loaders tested on synthetic data: Companies House (companies, persons with significant control, officers), GLEIF (LEI records and Level 2 consolidation relationships) and the ICIJ Offshore Leaks Database.
- The data manager (`neonradar data profiles`, `fetch`, `status`, `purge`) with its real-data gate, which keeps real data off in this release.
- The matching keys package `neonradar_keys` for entity resolution.
- The `neonradar` command line, `neonradar doctor`, the synthetic generator, graph migrations and loader, the Playwright end-to-end test, CI and pull request hygiene checks.
- Documentation: quickstart, architecture, wording rules, glossary, bibliography, learning cases and onboarding assignments.

### Not yet included

- Real-data loading (needs keys, an approved machine and the operator's approvals), entity resolution, sanctions list loaders, the other detectors, the evaluation harness and the investigation copilot (`POST /api/v1/copilot/ask` answers 501).

[Unreleased]: https://github.com/robotat-com/neon-radar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/robotat-com/neon-radar/releases/tag/v0.1.0
