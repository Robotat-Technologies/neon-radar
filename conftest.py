"""Repository-wide pytest setup. The shared Neo4j of the integration tests is a plugin
registered here once, so every suite (graph, detect, api) uses one database per session:
graph/tests/support/nr_test_neo4j.py (on the test path through pyproject.toml)."""

pytest_plugins = ["nr_test_neo4j"]
