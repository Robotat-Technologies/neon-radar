# data/

This folder is mostly local working space. Git ignores everything in it except synthetic fixtures, this file and an empty import folder.

## What may be committed

- `data/fixtures/`: **synthetic fixtures only.** Every entity id starts with `syn-`, every record belongs to the `nr_synthetic` dataset, and nothing in a fixture describes a real person, company, address or account.
- `data/README.md`: this file.
- `data/import/.gitkeep`: keeps the folder that the local Neo4j stack mounts for imports.

## What must not be committed

Everything else: bulk downloads, API responses, spike output, Neo4j exports, detection runs, and any file with real personal data or any row derived from OpenSanctions. The `.gitignore` rules enforce this, but they are a safety net, not permission: never force-add a file here with `git add -f`.

| Folder | What goes there | Committed |
|---|---|---|
| `data/fixtures/` | Synthetic fixtures | Yes |
| `data/cache/` | Spike and loader output from public sources. It can hold personal data, so delete it after 7 days (`access.spike_cache_days` in `docs/build/project.yaml`) | No |
| `data/import/` | Files staged for the local Neo4j import mount | No (only `.gitkeep`) |
| `data/runs/` | Detection run output; the audit copy of each run's alerts | No |

## Guardrails

These two rules come from `docs/build/PHASE-1.md` section 2.1 and apply to everything in this folder.

> **G1. No real person or company is ever labelled suspicious.** Synthetic laundering scenarios run only among synthetic entities (ids starting `syn-`). Real registry entities may receive synthetic background activity only, never a scenario role. Any exception needs an ADR approved by the project lead and the data steward, and must watermark every such transaction and alert in the interface, keep them out of exports, screenshots and the public demo, and come with a revised real-data notice (7.1).

> **G2. The repository holds code and synthetic fixtures only.** Never commit bulk data, API responses about real people, real personal data, or any row derived from OpenSanctions. Spike outputs go to `data/cache/` (gitignored).
