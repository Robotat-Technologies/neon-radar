from importlib.metadata import version

import neonradar_cli


def test_version_matches_package_metadata() -> None:
    assert neonradar_cli.__version__ == version("neonradar-cli") == "0.1.0"
