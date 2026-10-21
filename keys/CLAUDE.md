# keys: neonradar_keys

- Purpose: matching keys for names (Latin, Arabic and Cyrillic scripts), organisation names,
  addresses, postcodes, countries, nationalities and identifiers. Pure functions, no I/O.
  Empty until M2.8 (PHASE-2.md 4.1, 4.2).
- Owner: graph and entity resolution squad (nr-graph).
- Used by: the loaders (address record ids), the resolver (features) and the graph loader
  (`address_key`, Latin search names). One implementation of every key.
- Depends on: rigour, normality, anyascii (pins in PHASE-2.md 3.1); never on another member.
- Commands: `uv run pytest keys/tests`.
- Traps:
  - `from rigour.text.scripts import text_scripts`; never fuzzy country lookups.
  - Never use rigour or normality directly for keys elsewhere: keys come from here only.
  - rigour needs python-stdnum (LGPL-2.1-or-later, used unmodified, OD-20).
