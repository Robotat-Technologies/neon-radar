from importlib.metadata import version

import neonradar_copilot


def test_version_matches_package_metadata() -> None:
    assert neonradar_copilot.__version__ == version("neonradar-copilot") == "0.1.0"
