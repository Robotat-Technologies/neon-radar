// Test fixtures built from the repository's own contract files: the wording texts
// (contracts/wording/) and the synthetic contract examples (contracts/examples/).
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import type { DatasetInfo, Disclaimers, MetaResponse } from '@/api/types'

const HERE = dirname(fileURLToPath(import.meta.url))

/** The UI folder (ui/) and the repository root (ui/src/__tests__ is three levels down). */
export const UI_ROOT = resolve(HERE, '../..')
export const REPO_ROOT = resolve(HERE, '../../..')

export function repoPath(relative: string): string {
  return resolve(REPO_ROOT, relative)
}

export function readRepoText(relative: string): string {
  return readFileSync(repoPath(relative), 'utf-8')
}

export function readExample<T>(relative: string): T {
  return JSON.parse(readRepoText(`contracts/examples/${relative}`)) as T
}

/** As the API serves them: the file's text without its final newline (load_disclaimer). */
function wording(id: string): string {
  return readRepoText(`contracts/wording/${id}.txt`).replace(/\n+$/, '')
}

export const disclaimers: Disclaimers = {
  standing: wording('standing-v1'),
  synthetic_demo: wording('synthetic-demo-v1'),
  real_data: wording('real-data-v1'),
}

export function dataset(
  slug: string,
  synthetic: boolean,
  recordCount: number | null,
  title = slug,
): DatasetInfo {
  return {
    slug,
    title,
    licence_id: synthetic ? 'Apache-2.0' : 'OGL-UK-3.0',
    licence_url: 'about:blank',
    attribution: null,
    synthetic,
    personal_data: !synthetic,
    record_count: recordCount,
    loaded_at: null,
  }
}

/** The registry as Phase 1 has it: four real sources and the synthetic one. */
export function registry(counts: Partial<Record<string, number | null>> = {}): DatasetInfo[] {
  const count = (slug: string) => (slug in counts ? (counts[slug] ?? null) : 0)
  return [
    dataset('gb_companies_house', false, count('gb_companies_house')),
    dataset('gleif_lei', false, count('gleif_lei')),
    dataset('icij_offshore_leaks', false, count('icij_offshore_leaks')),
    dataset('opensanctions_default', false, count('opensanctions_default')),
    dataset('nr_synthetic', true, count('nr_synthetic'), 'NeonRadar synthetic data'),
  ]
}

export function meta(datasets: DatasetInfo[]): MetaResponse {
  return {
    app_version: '0.1.0',
    contracts_version: '1.0.0',
    schema_version: '1.0.0',
    datasets,
    disclaimers,
    counts: { nodes_by_label: {}, relationships_by_type: {} },
  }
}
