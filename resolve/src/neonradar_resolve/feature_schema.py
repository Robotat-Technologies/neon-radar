"""Feature tables for the Splink models (PHASE-2.md 7.1.5). `features.py` (M2.10a) writes them;
`models.py` (M2.10b) reads them. One row per resolvable record; every empty list is NULL.
"""

from __future__ import annotations

import pyarrow as pa

PERSON_SCHEMA = pa.schema(
    [
        ("unique_id", pa.string()),
        ("synthetic", pa.bool_()),
        ("name_key", pa.string()),  # neonradar_keys PersonKey.key
        ("name_key_rare", pa.string()),  # name_key when at most RARE_NAME_MAX records share it
        ("forename", pa.string()),  # first given-name token, when the source says which it is
        ("surname", pa.string()),  # first family-name token, when known
        ("initial", pa.string()),  # first letter of forename
        ("name_tokens", pa.list_(pa.string())),
        ("name_symbols", pa.list_(pa.string())),  # Wikidata QIDs of name groups
        ("skeletons", pa.list_(pa.string())),
        ("birth_full", pa.list_(pa.string())),  # yyyy-mm-dd values
        ("birth_ym", pa.list_(pa.string())),  # yyyy-mm values, including those of full dates
        ("birth_years", pa.list_(pa.int32())),
        ("birth_year_min", pa.int32()),
        ("birth_ym_min", pa.string()),
        ("countries", pa.list_(pa.string())),  # nationality, citizenship and residence codes
        ("postcode", pa.string()),  # one normalised UK postcode, or NULL
        ("linked_orgs", pa.list_(pa.string())),  # company keys of linked organisations
        ("identifiers", pa.list_(pa.string())),  # passport and national id numbers
    ]
)

ORG_SCHEMA = pa.schema(
    [
        ("unique_id", pa.string()),
        ("synthetic", pa.bool_()),
        ("name_key", pa.string()),  # neonradar_keys OrgKey.key
        ("name_key_rare", pa.string()),
        ("name_prefix", pa.string()),  # first four characters of name_key
        ("aliases", pa.list_(pa.string())),  # org keys of every name, alias and previous name
        ("ch_same_as", pa.string()),  # neonradar_keys ch_same_as_key
        ("name_tokens", pa.list_(pa.string())),
        ("jurisdiction", pa.string()),
        ("registration_numbers", pa.list_(pa.string())),
        ("incorporation_year", pa.int32()),
        ("postcode", pa.string()),
        ("legal_forms", pa.list_(pa.string())),
    ]
)

RARE_NAME_MAX = 50  # name_key_rare is NULL for keys shared by more records (no huge blocks)
