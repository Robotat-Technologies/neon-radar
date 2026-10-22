# keys: neonradar_keys

- Purpose: one implementation of every matching key (PHASE-2.md M2.8, docs/er/keys.md): person
  and organisation names in Latin, Arabic and Cyrillic, UK postcodes and addresses, countries,
  nationalities and the identifiers of rules D1 to D4. Owner: nr-graph.
- Pure functions, no I/O apart from the two packaged files in `data/` (each ships in the wheel with
  its `*.LICENSE.txt`). Used by the loaders, the resolver and the graph loader; depends on rigour,
  normality, anyascii, typing-extensions only.
- Every output change needs a test and a `RULES_VERSION` bump. Commands: `uv run pytest keys/tests`.
- Rebuild `data/ar_symbols.json.gz` with `keys/scripts/build_ar_symbol_index.py` (tag and
  SHA-256 of the new rigour) whenever the lock moves rigour, and bump `RULES_VERSION`;
  `test_symbol_index_matches_installed_rigour` fails until then.
- Traps:
  - Do not "simplify" a rule without a failing test: rigour leaves Arabic alef, ta marbuta, alef
    maqsura and hamza forms apart; ICU garbles unvocalised Arabic; rigour's Cyrillic ASCII drops
    digraphs; `normality.ascii_text` turns modifier-letter apostrophes into "?".
  - Never call fuzzy country lookups; `from rigour.text.scripts import text_scripts`.
  - `uk_company_number` accepts only Companies House forms; `SY` only with `synthetic=True`.
  - Never use rigour or normality directly for keys elsewhere: keys come from here only.
  - rigour needs python-stdnum (LGPL-2.1-or-later, used unmodified, OD-20).
