from importlib.metadata import version

import neonradar_detect


def test_version_matches_package_metadata() -> None:
    assert neonradar_detect.__version__ == version("neonradar-detect") == "0.1.0"
