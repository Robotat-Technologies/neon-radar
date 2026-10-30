# ingest: neonradar_ingest

- Purpose: source loaders and spikes (Companies House, GLEIF, ICIJ, OpenSanctions) and the
  seeded synthetic generator; all of them emit C1 records with a manifest.
- Owner: ingest squad (nr-ingest).
- Depends on: C1 records and `contracts/datasets.yaml` (licences, id prefixes).
- Commands: `uv run pytest ingest/tests`; spikes and loaders through `uv run neonradar`.
- Traps:
  - The only package that may use the network, and only through
    `neonradar_ingest.http.HttpClient` (an `httpx.Client`): pass `follow_redirects`
    explicitly and a `RateLimiter` per source (Companies House 2 per second, GLEIF 1 per
    second). It sets the timeouts (connect 10 s, read 60 s) and the NeonRadar User-Agent,
    retries GET, HEAD and OPTIONS after a 429, 500, 502, 503, 504 or transport error with
    backoff (`Retry-After`, or a source's own `retry_hint`; a wait over `max_hint` raises
    `HttpError`), and redacts URLs in logs. Never log headers, keys or whole responses, and
    never call `raise_for_status()` (its message has the unredacted URL): use `get_json` or
    check the status and raise `HttpError` with `redact(url)`.
  - The data manager (`data/`, PHASE-2.md M2.2; docs/data/profiles.md): profiles in
    `ingest/profiles/`, every folder from `data.layout` (never build data/cache/ paths by
    hand), the real-data gate `data.gate.check_real_data` before any request or write,
    downloads through `data.download.fetch`, retention and purge. A production loader
    registers a `SourceSpec`, a `Builder` and its profile-block model, and joins
    `data.sources.PLUGINS`. `ingest build` runs the gate for every dataset and every builder
    step it will run (`Builder.plan`; the officers step meets `access.companies_house_key`
    there, and again in the loader), `data fetch` for every dataset. A synthetic profile may
    enable only `nr_synthetic`; records of every other dataset always go under
    `data/cache/real/`. Its
    tests use the `data_env` fixture (root conftest.py): cache, profiles, project file
    (`NR_PROJECT_FILE`) and `.env` at tmp paths, and real httpx transports refused.
  - Source code goes in `sources/<source>/` (client, mapping to C1). Tests use
    `httpx.MockTransport` with synthetic bodies; the one real run is `@pytest.mark.network`.
  - Output goes to `data/cache/` (gitignored); never commit real data or API responses.
    Spikes write through `spikes.write_output` (records plus manifest in
    `data/cache/spikes/<source>/`) and build records with `spikes.entity_record`
    (`ValueEntity`, NFC); `neonradar spike clean` deletes output older than
    `access.spike_cache_days`.
  - OpenSanctions use follows `access.opensanctions` in `docs/build/project.yaml` through the
    gate in `sources/opensanctions/access.py`: `none` sends no request, and only `licensed`
    writes, to `data/cache/spikes/` only. Its tests use synthetic bodies, never real rows.
  - ICIJ loader (`sources/icij/full.py`, `slice.py`, `links.yaml`; M2.5): reads the zip's CSV
    members by header name, never extracting; selection passes keep node ids only; `note`
    and unmapped columns never reach records; `officer_of` links classify through
    `links.yaml` (unknown values are counted, so extend the table); a relationship type it
    does not map is skipped and counted (fail closed), and one with same, similar, duplicate
    or possibly in it is a hint, written to `*-hints.csv`, never a record. Names are tested
    as FtM cleans them. Tests build the zip in memory from invented rows.
  - Synthetic ids start with `syn-`; synthetic accounts are `NRSYN` plus 10 digits.
  - Companies House (`sources/companies_house/`): the key is `CH_API_KEY` (basic auth
    username, empty password); 600 requests per 5 minutes, limiter at 2 per second. Map ids
    with `make_id` and keep raw ids in `nr.source_ref`; count `identity_verification_details`,
    never map it. Its `Mapper` builds `ValueEntity` records itself (it merges an officer's
    appointments into one record) and writes through `spikes.write_output`. Tests use
    synthetic bodies in `tests/fixtures/companies_house/` and compare with
    `*.expected.json`, never a committed `.ftm.jsonl` with `gbch-` ids.
  - The synthetic generator (`synth/`, ADR-0005) must stay byte-reproducible: draw only
    through `synth.rng` (numpy `integers`, `random`, `choice`, `permutation`; never normal or
    lognormal), never iterate a set, never read the clock or the network, write `\n` line
    ends. `test_synth_determinism.py` regenerates `data/fixtures/demo-mini/` and compares
    bytes; after any change that alters the output, run `make fixtures`, check every new
    company and Latin-script person name against the Companies House search (OD-12), and
    record a matching name's slot in `synth/demo.py` `REDRAW` (the ER benchmark:
    `synth/erbench.py` `REDRAW`, names listed by `scripts/check_names_ch.py`), never the real name.
  - Planted scenarios run only among synthetic entities (G1); ground truth goes only to
    `labels/*.csv`, never into records (R9). Person names come from Faker plus curated lists
    in `synth/words.py` (never Faker `ar_SA` surnames, never mimesis), filtered by
    `synth/denylist.txt`.
  - The synthetic join (`synth/join.py`, ADR-0005 rule 2) gives only live registry
    organisations (`gb_companies_house`, `gleif_lei`; status empty or in `LIVE`; fail closed
    on anything else) background activity with one-way synthetic counterparties. People,
    bare LegalEntity and PublicBody records and ICIJ records get nothing; scenarios, labels,
    topics and every other schema stay off input entities (`touches_input` must report all
    zeros). New ids use `syn-<kind>-j<seed>-`; account numbers a per-seed block.
  - Generator v1 (`synth/` beside v0, PHASE-3.md 7.2, ADR-0023): `world.py` and
    `overlay.py` and the scenario modules are verbatim from the code book (`make spec-check
    M=M3.3`; change them only through `scripts/spec_extract.py update` or a recorded
    deviation). `namesource.py` adapts the Phase 1 name modules; extra company words live
    there, never in `words.py`. `synth world` and `synth overlay` (`synth/commands.py`)
    validate every record with C1 before writing and refuse holdout seeds (G11). On a real
    profile `synth overlay` runs `gate.check_real_overlay` first (the gate, then
    `access.real_overlay_profiles`, exit 3 before any record is read), reads only the profile's
    own folders and prints counts only (M3.4, ADR-0021); its tests use look-alikes in `data_env`.
