"""The live Companies House spike (M1.8a acceptance). Uses the internet: never runs in CI.

    CH_SPIKE_COMPANY=<company number> uv run pytest -m network \
        ingest/tests/test_companies_house_network.py -v -s

Needs `CH_API_KEY` in the environment or `.env` and skips cleanly without it. The output holds
personal data, so it goes to a temporary folder that the test deletes; the summary it prints
has counts and field names only.
"""

import os
import shutil
from pathlib import Path

import pytest

from neonradar_contracts.records import manifest_path, validate_files
from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house.client import CompaniesHouseClient
from neonradar_ingest.sources.companies_house.spike import run_spike

pytestmark = pytest.mark.network


def test_the_live_spike_writes_valid_records(tmp_path: Path) -> None:
    key = IngestSettings().companies_house_key()
    if key is None:
        pytest.skip("CH_API_KEY is not set (project.yaml access.companies_house_key: pending)")
    company = os.environ.get("CH_SPIKE_COMPANY", "").strip()
    if not company:
        pytest.skip("set CH_SPIKE_COMPANY to the company number to fetch")
    try:
        with CompaniesHouseClient(key) as client:
            result = run_spike(client, company, root=tmp_path)
        print("\n".join(result.summary()))
        counts, issues = validate_files([result.records_path], strict=True)
        assert [str(issue) for issue in issues] == []
        assert counts["Company"] >= 1
        assert manifest_path(result.records_path).is_file()
    finally:
        shutil.rmtree(tmp_path / "companies_house", ignore_errors=True)
