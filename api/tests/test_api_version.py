from importlib.metadata import version

import neonradar_api


def test_version_matches_package_metadata() -> None:
    assert neonradar_api.__version__ == version("neonradar-api") == "0.1.0"
