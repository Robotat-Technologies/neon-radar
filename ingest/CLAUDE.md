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
    retries 429, 5xx and transport errors with backoff (`Retry-After`, or a source's own
    `retry_hint`), and redacts URLs in logs. Never log headers, keys or whole responses, and
    never call `raise_for_status()` (its message has the unredacted URL): use `get_json` or
    check the status and raise `HttpError` with `redact(url)`.
  - Source code goes in `sources/<source>/` (client, mapping to C1). Tests use
    `httpx.MockTransport` with synthetic bodies; the one real run is `@pytest.mark.network`.
  - Output goes to `data/cache/` (gitignored); never commit real data or API responses.
    Spikes write through `spikes.write_output` (records plus manifest in
    `data/cache/spikes/<source>/`) and build records with `spikes.entity_record`
    (`ValueEntity`, NFC); `neonradar spike clean` deletes output older than
    `access.spike_cache_days`.
  - OpenSanctions use follows `access.opensanctions` in `docs/build/project.yaml`.
  - Synthetic ids start with `syn-`; synthetic accounts are `NRSYN` plus 10 digits.
