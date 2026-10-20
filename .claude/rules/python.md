---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---
# Python rules
- Python 3.14. Every public function and method has type hints; mypy strict must pass.
- Contract types come from `neonradar_contracts`; never redefine them locally.
- Read configuration from environment variables through one settings object per package
  (pydantic-settings), never at import time.
- Network code lives only in `neonradar_ingest` loaders and spikes; it uses httpx with
  timeouts, explicit `follow_redirects`, retries with backoff and a rate limiter.
- Tests: `tests/test_<module>.py`; integration tests marked `@pytest.mark.integration`;
  anything touching the internet marked `@pytest.mark.network` (never run in CI).
- No test may depend on the order of other tests or on data outside `data/fixtures/` and
  the package's own `tests/fixtures/`.
