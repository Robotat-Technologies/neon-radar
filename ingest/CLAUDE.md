# ingest: neonradar_ingest

- Purpose: source loaders and spikes (Companies House, GLEIF, ICIJ, OpenSanctions) and the
  seeded synthetic generator; all of them emit C1 records with a manifest.
- Owner: ingest squad (nr-ingest).
- Depends on: C1 records and `contracts/datasets.yaml` (licences, id prefixes).
- Commands: `uv run pytest ingest/tests`; spikes and loaders through `uv run neonradar`.
- Traps:
  - The only package that may use the network: httpx with timeouts,
    `follow_redirects=True`, retries with backoff and a rate limiter.
  - Output goes to `data/cache/` (gitignored); never commit real data or API responses.
  - OpenSanctions use follows `access.opensanctions` in `docs/build/project.yaml`.
  - Synthetic ids start with `syn-`; synthetic accounts are `NRSYN` plus 10 digits.
  - Companies House (`sources/companies_house/`): the key is `CH_API_KEY` (basic auth
    username, empty password); 600 requests per 5 minutes, limiter at 2 per second. Map ids
    with `make_id` and keep raw ids in `nr.source_ref`; count `identity_verification_details`,
    never map it. Tests use synthetic bodies in `tests/fixtures/companies_house/` and compare
    with `*.expected.json`, never a committed `.ftm.jsonl` with `gbch-` ids.
