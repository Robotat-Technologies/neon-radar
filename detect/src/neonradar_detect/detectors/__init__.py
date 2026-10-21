"""Detectors: one module per typology, named in the typology file's `detector` field.

Each module has `NAME` (its module path), `VERSION` and `detect(driver, database, typology)`,
which returns `neonradar_detect.alerts.Finding`s; the runner turns them into C4 alerts.
"""
