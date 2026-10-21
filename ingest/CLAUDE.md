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
  - OpenSanctions use follows `access.opensanctions` in `docs/build/project.yaml` through the
    gate in `sources/opensanctions/access.py`: `none` sends no request, and only `licensed`
    writes, to `data/cache/spikes/` only. Its tests use synthetic bodies, never real rows.
  - Synthetic ids start with `syn-`; synthetic accounts are `NRSYN` plus 10 digits.
