from importlib.metadata import version

import neonradar_graph


def test_version_matches_package_metadata() -> None:
    assert neonradar_graph.__version__ == version("neonradar-graph") == "0.1.0"
