# Spike report: OpenSanctions

| | |
|---|---|
| Milestone | M1.8d ([PHASE-1.md](../../build/PHASE-1.md), section 6), gated by the licence decision |
| Dataset | `opensanctions_default` (`contracts/datasets.yaml`, prefix `os`, `status: blocked`) |
| Access decision | `access.opensanctions: none` in [docs/build/project.yaml](../../build/project.yaml) |
| Verdict | **Blocked on licence decision** (section 7) |
| For | The data steward (@robotat-com, `people.data_steward`), who decides the route with the project lead |

No OpenSanctions data was fetched for this spike, and none is in the repository. Every count below comes from a synthetic fixture whose names, ids and datasets are placeholders.

## 1. Command run, date, duration, network conditions

<!-- RUN-EVIDENCE -->

## 2. What was fetched

Nothing. With access `none` the command refuses before it creates an HTTP client, so no request reached `data.opensanctions.org` or any other OpenSanctions host: not `index.json`, not `entities.ftm.json`, not any other file. No record counts by schema exist for the real data.

What was exercised instead, offline: the mapping, on `ingest/tests/fixtures/opensanctions/entities.ftm.json`, a synthetic file shaped like the export (one entity per line, `id` first, the legacy `target` key, a list of source datasets, `referents`, a PEP with a `Position` and an `Occupancy`, a `Family` link, a `Sanction`, an `Identification` and one schema FollowTheMoney 4.11 does not know). The mocked tests serve it behind a 307 redirect from `datasets/latest/...` to `artifacts/<collection>/<version>/...`, as OpenSanctions does since 17 August 2026.

| Synthetic fixture | Count |
|---|---|
| Lines read | 12 |
| C1 records written by the mapping | 10: `Person` 3, `Company` 1, `Address` 1, `Position` 1, `Occupancy` 1, `Family` 1, `Sanction` 1, `Ownership` 1 |
| Skipped and counted | `Identification` 1 (not a C1 v1 schema), `SynthFutureSchema` 1 (unknown to FollowTheMoney 4.11) |
| Top-level keys dropped | `target` 10 |
| Properties unknown to FollowTheMoney, dropped | `Person:synthFutureProperty` 1 |
| C2 flag labels from topics | `PEP` 1, `RCA` 1, `Sanctioned` 1 (`sanction.linked` sets none) |
| C1 validation of the 10 records | 0 issues, also in strict mode |

## 3. Measured facts that confirm or correct the research notes

Nothing was measured against OpenSanctions. These points from [sources-opensanctions-ftm-icij.md](../../research/2026-10-16/sources-opensanctions-ftm-icij.md) remain unverified live and are the first things a permitted run should confirm: the 307 redirect of `datasets/latest/...` (A.1), the `index.json` shape, the first-line latency and the time to stream 1,000 lines of `sanctions` (A.5).

Checked again on 21 October 2026 from OpenSanctions documentation pages (no data files):

- `https://www.opensanctions.org/docs/bulk/updates/`: poll `index.json` "every ~30 minutes if you need timely updates", watch "the `version` ID or `last_export` timestamp", and compare "the SHA1 `checksum` values in `dataset.resources`". This matches A.1.
- `https://www.opensanctions.org/docs/metadata/`: the fields of each resource are `name`, `url`, `checksum` ("SHA1 of the resource contents"), `mime_type`, `mime_type_label`, `title` and `size`. The page groups `version`, `last_export`, `resources` and other fields in a "dataset" section but does not say whether `dataset` is a JSON key in the per-dataset `index.json`. The spike client accepts both shapes and falls back to `datasets/latest/<collection>/entities.ftm.json` when no resource is listed.

Verified locally with followthemoney 4.11.0 on synthetic lines (adds detail to A.5 and B.3):

- `ValueEntity.from_dict()` keeps `target` in the entity's context, and `to_dict()` writes it back out, so a loader must drop it explicitly (it fails C1 with `FORMAT`).
- `from_dict()` does not clean values (an invalid date stays) and silently drops property names it does not know; a value that is a string instead of a list is split into characters. The mapping checks the shape first and re-adds every value through FollowTheMoney's cleaning.
- `referents` and `datasets` are sets inside `ValueEntity`, so `to_dict()` lists them in no fixed order; the mapping sorts referents so that the output is deterministic.
- FollowTheMoney's date type accepts `2025-08-22T10:15:20+00:00`, the timestamp form in the documentation example (B.3); the mapping writes `first_seen`, `last_seen` and `last_change` in UTC without an offset, the project's convention.

## 4. Mapping notes

Code: `ingest/src/neonradar_ingest/sources/opensanctions/` (`access.py` the gate, `mapping.py` the mapping to C1, `spike.py` the client). It follows [contracts/C1-record.md](../../../contracts/C1-record.md), "How to write a loader that emits C1".

| OpenSanctions field | C1 record |
|---|---|
| `id` (for example `NK-...`, or a source id) | `id` = `make_id("os", "ent", id)`, for example `os-ent-NK-...`; `_` becomes `.`, and an id outside the reference alphabet becomes `os-ent-<20 hex of SHA-1>`. One kind, `ent`, for every schema, so that a reference gets the same id as the entity it points to without knowing that entity's schema |
| `id` | `nr.source_ref` (raw, NFC) |
| `schema` | `schema`, if it is a C1 v1 schema and not `Payment`; otherwise skipped and counted in the manifest's `counts.skipped` |
| `properties` | `properties`, every value re-added through FollowTheMoney's cleaning (rejected values dropped and counted), strings in NFC |
| entity-typed properties (`holder`, `post`, `person`, `relative`, `entity`, `owner`, `asset`, `addressEntity`, ...) | each value through the same `make_id` |
| `datasets` (OpenSanctions' source datasets) | replaced by `["opensanctions_default"]`; the source datasets are counted, not kept |
| `referents` | each through `make_id`, sorted, the record's own id removed |
| `caption` | `caption` (NFC) |
| `first_seen`, `last_seen`, `last_change` | the same keys, in UTC without an offset |
| `target` | dropped (legacy; OpenSanctions says to filter on `topics`) |
| any other top-level key | dropped and counted |
| `topics` | kept as the `topics` property; the graph loader sets the C2 flag labels from it: `sanction` to `:Sanctioned`, `role.pep` to `:PEP`, `role.rca` to `:RCA` |

What does not map:

- Schemata outside C1 v1: for example `Identification` and `Passport` (in the fixture), and vessels, aircraft, securities and other schemata OpenSanctions publishes. They are skipped and counted. Which ones appear, and how often, is unknown until a permitted run.
- `Payment`: C1 v1 allows payments only in synthetic data (rule R7), so OpenSanctions payments are skipped.
- Schemata newer than the pinned FollowTheMoney (4.11): skipped and counted; a growing count means the pin needs raising.
- OpenSanctions' list of source datasets per entity: C1 keeps exactly one dataset (R2) and the closed `nr` object has no key for it. If Phase 2 needs per-source provenance (for example to show which official list a sanction comes from), that is a minor contract change after the freeze.
- `nr.address_roles`: OpenSanctions does not say what role an address plays, so the graph loader's default (`unknown`) applies.

## 5. Licence and personal-data notes for the data steward

The licence position, verbatim from [sources-opensanctions-ftm-icij.md](../../research/2026-10-16/sources-opensanctions-ftm-icij.md) (finding 1 in section 0, then section A.2; the bracketed source numbers refer to that note's source list):

> 1. **OpenSanctions data needs a licence for use inside a company.** The data is CC BY-NC 4.0 and OpenSanctions states: "Any use inside a for-profit business requires a data license." [S18]. There is no published exemption for open-source projects; free API keys exist only for journalists, public-interest nonprofits, affiliated academics and public institutions of Ukraine, Georgia and Moldova [S18]. The licensing page does invite businesses to "integrate and evaluate our data before signing a license" [S17], which covers a short evaluation, not ongoing development. A 40-person for-profit company should get written confirmation or a licence before its team downloads and uses the data, and every commercial user of NeonRadar will need their own licence. Fixtures must be synthetic: copying OpenSanctions rows into an Apache-2.0 repository would relicense CC BY-NC material.

> **Answer for NeonRadar's company (40 people, unpaid open-source internship project):** by OpenSanctions' published test ("Any use inside a for-profit business requires a data license") the company's own use of the data for development and testing falls inside a for-profit business, so it needs a data licence, apart from a short evaluation, which the licensing page explicitly invites. That the interns are unpaid and the code is open source does not change the test as OpenSanctions words it. The CC BY-NC definition ("primarily intended for ... commercial advantage") is arguably narrower, but OpenSanctions' exemption page is the interpretation it publishes and points to from COPYRIGHT.md [S48]. Recommended actions:
> 1. Email OpenSanctions (support or sales) describing the project and ask for written confirmation of what is allowed (for example, evaluation-scale downloads for building an open-source loader, no production screening) or for a quote.
> 2. Until then, develop and run CI against synthetic FtM fixtures, and stream at most an evaluation slice (spike A.5).
> 3. Ship the OpenSanctions loader as user-run, with documentation (and a CLI notice) saying commercial users need their own licence and pointing journalists, NGOs and academics to the free-key programme.
> 4. Never commit OpenSanctions-derived rows to the repository.

**The access decision and who made it.** `access.opensanctions: none` has been in `docs/build/project.yaml` since the operator's seed commit (6468466, 20 October 2026); `none` is the default in PHASE-1.md section 1.2 ("synthetic fixtures only"). The operator (@robotat-com) holds the project lead and data steward roles for now (operator decision OD-6). No request to OpenSanctions and no answer is on file: `docs/data/licences/opensanctions.md` does not exist. Choosing another route is a human decision (OD-5); no agent changes this value.

**The four routes and what each one does.** PHASE-1.md section 1.2 defines them; the command enforces them (`ingest/src/neonradar_ingest/sources/opensanctions/access.py`, tested):

| Route | Precondition | `neonradar spike opensanctions` | On disk |
|---|---|---|---|
| `none` (now) | none; the default | exits 3 with "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md" before any request | nothing |
| `evaluation` | OpenSanctions confirms in writing, and the request and the answer are filed in `docs/data/licences/opensanctions.md`; the command refuses while that file is missing | reads `index.json` (logs `version` and the SHA-1 of `entities.ftm.json`), streams the first `--rows` lines (default 1,000) of `--collection` (default `sanctions`), maps them to C1 in memory, prints counts | nothing |
| `licensed` | the organisation holds an OpenSanctions data licence | as `evaluation` | C1 records and a manifest in `data/cache/spikes/opensanctions/` (gitignored) only, deleted after `access.spike_cache_days` (7) |
| `exempt` | the organisation running NeonRadar itself qualifies for OpenSanctions' free programme (public-interest journalists, advocacy groups and nonprofits working on democratic governance or exposing corruption and financial crime, affiliated academics, public institutions of Ukraine, Georgia and Moldova); never a company team | as `evaluation` | nothing (PHASE-1.md M1.8d step 4 lets only `licensed` write) |

A missing file, a missing key or any other value (for example `TODO`) counts as `none`.

Under every route:

- No OpenSanctions row, and nothing derived from one, is committed (guardrail G2). Test fixtures stay synthetic.
- OpenSanctions data is never redistributed (`redistribution: never`); even for licensed customers, OpenSanctions' data licensing terms exclude passing the data to third parties without a reseller licence (research note A.2).
- A database that merges OpenSanctions data with other sources is never published (G7). ICIJ data is loaded from ICIJ, not from OpenSanctions' CC BY-NC copy.
- The data is personal data, including crime-related topics (`personal_data: true` in `contracts/datasets.yaml`). The spike prints counts and field names only, never names or other values; a licensed run's cache holds personal data and is deleted after 7 days.
- Every manifest carries the attribution line in `contracts/datasets.yaml`, which is NeonRadar's proposal (OpenSanctions publishes no wording) and awaits the data steward's approval (GC-17).
- Every commercial user of NeonRadar needs their own OpenSanctions licence; DATA_SOURCES.md says so.

## 6. Gotchas and recommendations for the Phase 2 loader

- Follow redirects explicitly: `datasets/latest/...` answers 307 to `artifacts/<collection>/<version>/...`. The commercial delivery service also redirects large files to a CDN; never send its token to the redirect target (research note A.1).
- Use `version` and the resource `checksum` from `index.json` to decide whether to download again, and download at most every 6 hours (A.1). Never use the `all` collection; the command accepts only the documented collections and rejects `all`.
- Ids change after deduplication and there are no deletion markers: keep `referents` (mapped into the `os-ent-` namespace), and plan full reloads or the delta files (A.1).
- Treat `target` as legacy and filter on `topics` (A.4). Only `sanction`, `role.pep` and `role.rca` set C2 flag labels; every other topic stays a property.
- A slice is not a closed load: references to entities outside it dangle, so validate a slice without `--strict` (the manifest says so in `notes`); validate full loads in strict mode.
- C1 rule R8 needs every `BankAccount` to be the asset of an `Ownership` held by a legal entity in the same load. How OpenSanctions links its bank accounts is not checked yet; check before loading them.
- Watch `counts.skipped` in the manifest: schemata newer than the pinned FollowTheMoney, or outside C1 v1, land there.
- Decide whether C1 should keep OpenSanctions' source datasets (section 4); today they are counted and dropped.
- Never log entity names or values; the spike's output is counts only.

## 7. Verdict

**Blocked on licence decision.** The code path is built and tested offline (gate, mapping to C1, client), but no OpenSanctions data may be fetched while `access.opensanctions` is `none`, so the plan's day-2 rule (fetch end to end before committing to the source) cannot be met. The dataset's `status` stays `blocked` in `contracts/datasets.yaml`.

Options for Phase 2, for the data steward and the project lead:

1. **Obtain a licence or an evaluation agreement.** Ask OpenSanctions in writing what the organisation may do (for example evaluation-scale downloads to build an open-source loader, no production screening) or for a quote; file the request and the answer in `docs/data/licences/opensanctions.md`; set `access.opensanctions` to `evaluation` or `licensed`; then run `uv run neonradar spike opensanctions` and `uv run pytest -m network ingest/tests/test_opensanctions_spike.py`, and update this report with the measured counts.
2. **Evaluate official government sanctions lists as an alternative source**, for example the consolidated lists that governments and the UN publish themselves. Their licences and formats are not checked yet; Phase 2 verifies them before any loader is written.

If the organisation itself qualifies for OpenSanctions' free programme, `exempt` is a third route, but PHASE-1.md section 1.2 rules it out for a company team.
