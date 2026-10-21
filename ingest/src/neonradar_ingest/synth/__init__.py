"""Seeded synthetic data generator v0 (docs/build/PHASE-1.md M1.8e; ADR-0005).

Writes C1 records for synthetic companies, people, accounts and payments, plus ground-truth
label files kept apart from the records (R9). The same seed always gives byte-identical
records and labels; only the manifest's `created_at` changes. Phase 3 builds the full
generator on top of this one.
"""

GENERATOR = "neonradar_ingest.synth"
GENERATOR_VERSION = "0.1.0"
