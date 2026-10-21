from importlib.metadata import version

import neonradar_keys


def test_version_matches_package_metadata() -> None:
    assert neonradar_keys.__version__ == version("neonradar-keys") == "0.1.0"
