from importlib.metadata import version

import neonradar_contracts


def test_version_matches_package_metadata() -> None:
    assert neonradar_contracts.__version__ == version("neonradar-contracts") == "0.1.0"
