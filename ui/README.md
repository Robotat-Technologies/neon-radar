# NeonRadar UI

The explorer: Vue 3.5 (`<script setup lang="ts">`), TypeScript 6.0, Vite 8, Pinia, Vue Router and Cytoscape.js with the fcose layout. Scaffolded with create-vue 3.24 (`docs/build/PHASE-1.md` M1.9d). It reads only the NeonRadar API (contract C3, `contracts/C3-api.md`) on its own origin; nothing is loaded from another host.

## Pages

| Path            | Page                                                                          |
| --------------- | ----------------------------------------------------------------------------- |
| `/`             | Search over names, addresses and account numbers                              |
| `/entities/:id` | One entity: network canvas, details, sources, alerts                          |
| `/alerts`       | The alert queue, filtered by priority, typology or entity                     |
| `/alerts/:id`   | One alert: evidence graph, explanation steps, metrics, typology and citations |
| `/sources`      | The dataset registry with licences and what is loaded                         |

Every page waits for `GET /api/v1/meta` and shows its standing disclaimer, then the synthetic demo notice when every loaded dataset (`record_count` above 0) is synthetic, otherwise the real data notice (`src/lib/notices.ts`). If the notices cannot be loaded, no page is shown.

## Commands

Run from the repository root with `--prefix ui`, or from this folder.

| Command                      | What it does                                                                                                      |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `npm ci`                     | Install the locked dependencies                                                                                   |
| `npm run dev`                | Vite dev server on `http://localhost:5173`; `/api` goes to `http://127.0.0.1:8000` (`uv run neonradar api serve`) |
| `npm run gen:api`            | Regenerate `src/api/schema.d.ts` from `contracts/openapi/v1.json`; commit the result unchanged                    |
| `npm run lint`               | oxlint, ESLint and Prettier, checking only (CI)                                                                   |
| `npm run lint:fix`           | The same, fixing what they can                                                                                    |
| `npm run type-check`         | `vue-tsc --build`                                                                                                 |
| `npm run test:unit -- --run` | Vitest unit and component tests                                                                                   |
| `npm run build`              | Type-check and build into `dist/`                                                                                 |
| `npm run test:e2e`           | Playwright tests (`e2e/`); `shell.spec.ts` answers every API call from the contract examples                      |

## Rules

- API types come only from `src/api/schema.d.ts`, which `gen:api` writes; `src/api/types.ts` gives them short names. ESLint and Prettier skip the generated file.
- CSS uses logical properties only (`margin-inline-start`, `inline-size`), so right-to-left layouts work later; `src/__tests__/source-guards.spec.ts` checks it, together with the wording lint (`contracts/wording/forbidden-terms.txt`) and the absence of other hosts in the source.
- Flags appear only in the PHASE-1.md 7.1 vocabulary and name their dataset ("listed in <dataset> as sanctioned").
- Never add `@neo4j-nvl/*` or GPL packages, and keep TypeScript on `~6.0.3`.
