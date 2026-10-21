from importlib.metadata import version

import neonradar_ingest


def test_version_matches_package_metadata() -> None:
    assert neonradar_ingest.__version__ == version("neonradar-ingest") == "0.1.0"
