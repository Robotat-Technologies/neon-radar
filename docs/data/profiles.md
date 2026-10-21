# Data profiles

| | |
|---|---|
| Owner | Ingest squad, with the data steward for every change to a profile |
| Decision record | [ADR-0013](../decisions/0013-data-profiles-and-sources.md) (proposed) |
| Spec | `docs/build/PHASE-2.md` M2.2 and section 7.8 |
| Files | `ingest/profiles/*.yaml`; the data manager in `ingest/src/neonradar_ingest/data/` |

A profile names the data one NeonRadar installation loads: which sources, which slice of each, and whether the result is real or synthetic. Every loader plugs into the data manager instead of choosing its own folders or checks, so one place decides what a profile loads, whether it may run on this machine, where its files go, how long they stay and how they are deleted.

## The three profiles

| Profile | Data | What it loads |
|---|---|---|
| `demo` | synthetic | The Phase 1 demo-mini fixture (`data/fixtures/demo-mini`); from M2.9 also the entity resolution benchmark. Runs anywhere, including CI |
| `uk-tiny` | real | A small slice for developers: the companies of one large group quoted on the London Stock Exchange, found from two seed company numbers through Companies House PSC records (at most 400 companies), their officers (at most 1,500 requests) and PSCs, their GLEIF records and the sanctions lists. No ICIJ data. A test input for the loaders that implies nothing about these companies |
| `uk-sample` | real | A neutral slice of the UK register: companies registered in eight city-centre postcode districts across the UK (`EC2A`, `M1`, `B3`, `LS1`, `EH3`, `CF10`, `BS1`, `NE1`), at most 5,000 sampled evenly per district and 50,000 in all, with their ownership chains (corporate PSCs up to four levels up), officers (at most 20,000 requests), GLEIF records, the ICIJ records tied to the same districts (`district-linked`, at most 50,000 nodes) and the sanctions lists. The districts were chosen for spread, not for anything about the companies in them |

A source enabled in a profile still runs only if `docs/build/project.yaml` allows its dataset: `access.sanctions_lists` for the four sanctions lists, `access.pep_sources` for UK Parliament members, and `access.opensanctions` (`licensed` or `exempt`) for OpenSanctions. With the current project file (operator decision OD-22) the UN list and the Parliament source stay off. `access.companies_house_key` gates only the officers step, because the bulk files need no key. `uv run neonradar data profiles` shows, for each profile, the datasets it would load here and the ones `project.yaml` does not allow.

## Expected size and resources

Estimates from PHASE-2.md 7.8; M2.13 replaces them with measurements in `docs/data/benchmarks/`.

| Item | `demo` | `uk-tiny` | `uk-sample` |
|---|---|---|---|
| Downloads (shared between real profiles; two versions kept per dataset and product) | none | about 3.5 GB | the same plus ICIJ |
| Companies | about 30 synthetic | at most 400 | at most 50,000 |
| Officer requests and time | none | at most 1,500, about 13 minutes | at most 20,000, about 3 hours at the rate limit |
| ICIJ nodes | none | none | at most 50,000 |
| Graph after resolution | a few hundred nodes | about 45,000 nodes | about 300,000 nodes, 550,000 relationships |
| Disk at peak | under 1 GB | about 10 GB | about 25 GB |
| Memory | the Phase 1 small profile | DuckDB 4 GB plus the real Neo4j instance | a 16 GB laptop |
| Build time without officers | under 2 minutes | about 15 minutes | about 30 minutes, then the officer fetch |

## The real-data gate

Every command and builder step that reads real downloads or real records, or calls a real API, runs the gate first, before any network request or file write. For a profile with `real_data: true` it checks, in this order, and refuses with exit code 3 and the rule that failed:

1. the dataset is allowed by its access rule (for example "us_ofac_sdn is not in access.sanctions_lists"); commands that are not about one dataset (`er`, `graph`, `load`) skip this check;
2. the profile is in `access.real_data_profiles` (empty today, so no real profile runs);
3. `access.data_protection_filed` is true: the data steward has filed the data protection documents in `docs/data/dpia/` ([real-data handling](real-data-handling.md), rule 1);
4. neither `CI` nor `CODESPACES` is set;
5. `NR_REAL_DATA_MACHINE=approved` is set, in the environment or the repository's `.env`, by the owner of a machine the data steward listed in [real-data-machines.md](real-data-machines.md).

A command that addresses the real-data Neo4j instance without a profile checks 3 to 5, and refuses while `access.real_data_profiles` is empty. `neonradar data purge` is not gated: deleting real data is always allowed.

## Where the files go

Real profiles write only under `data/cache/real/` (downloads in `sources/<dataset>/<product>/<version>/`, records in `records/<profile>/<dataset>/`, and so on; PHASE-2.md 4.5), synthetic profiles only under `data/cache/synthetic/`. `neonradar_ingest.data.layout` names every folder, and no other module builds them. Each command that touches a real profile prints a counts-only summary and writes the same summary to `data/cache/reports/<profile>/`. On a real profile an error prints its class, step, dataset, rule and a reference such as `err-3`; the traceback stays in `data/cache/real/logs/`.

## Commands

```bash
uv run neonradar data profiles                     # each profile, each gate condition, its datasets
uv run neonradar data fetch --profile uk-tiny      # the gate, then the downloads (approved machines)
uv run neonradar ingest build --profile demo       # validates the demo fixture; prints a summary
uv run neonradar data status                       # versions, sizes, ages and retention (counts only)
uv run neonradar data purge --expired --yes        # what is past access.real_data_days
uv run neonradar data purge --all-real --graph --yes   # every real file and the real Neo4j volume
```

`data purge` takes one of `--expired`, `--dataset <slug>`, `--profile <name>`, `--labels`, `--decisions`, `--logs` or `--all-real`, optionally with `--graph`, or `--graph` alone, and always `--yes`.

## Adding or changing a profile

Open a pull request that adds or edits `ingest/profiles/<name>.yaml`; the data steward reviews it (`.github/CODEOWNERS`). The file has `profile` (its own name), `description`, `real_data`, `sources` (one entry per dataset slug, each with `enabled` and the block its loader defines) and `resolution` (`enabled`, `config`). Unknown keys fail. Choose a slice for spread or for a documented test purpose, never because its companies look unusual, and never put a company or person name next to a seed. A real profile runs only after the operator adds it to `access.real_data_profiles`.

## Adding a source

A loader module registers, at import time, a `SourceSpec` (its `discover(client)` lists the files of the current version of each product), a `Builder` (its `build(profile, context)` turns the downloads into C1 records and manifests in `context.out_dir`, which is validated in strict mode before it replaces the old records), and a pydantic model for its profile block (`register_source_model`). Then it adds itself to `PLUGINS` in `neonradar_ingest.data.sources`. Downloads, resumption, checksums, rotation, the gate, the summary and the swap of record folders come from the data manager.
