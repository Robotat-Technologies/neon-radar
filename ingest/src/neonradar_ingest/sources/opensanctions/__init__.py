"""OpenSanctions: the licence gate, the mapping to C1 and the spike (PHASE-1.md M1.8d).

OpenSanctions data is CC BY-NC 4.0, and OpenSanctions states: "Any use inside a for-profit
business requires a data license." Nothing in this package fetches data unless
`access.opensanctions` in docs/build/project.yaml allows it, and only `licensed` access writes
records, to the spike cache only (guardrails G2 and G7, DATA_SOURCES.md).
"""
