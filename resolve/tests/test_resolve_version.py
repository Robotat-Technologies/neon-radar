from importlib.metadata import version

import neonradar_resolve


def test_version_matches_package_metadata() -> None:
    assert neonradar_resolve.__version__ == version("neonradar-resolve") == "0.1.0"
