// Text for the source-data flags (PHASE-1.md 7.1 vocabulary). A flag is a fact a source
// published, never a finding of NeonRadar, so every badge names the dataset it came from.
// No other source topics are shown in Phase 1.
import type { NodeFlags } from '@/api/types'

export type FlagKind = 'sanctioned' | 'pep' | 'rca'

export interface FlagBadge {
  kind: FlagKind
  text: string
}

const FLAG_PHRASES: ReadonlyArray<readonly [FlagKind, string]> = [
  ['sanctioned', 'as sanctioned'],
  ['pep', 'as a politically exposed person'],
  ['rca', 'as a relative or close associate of a politically exposed person'],
]

/** "A", "A or B", "A, B or C": a record comes from one of them (C1 gives each record one dataset). */
export function joinDatasetNames(names: readonly string[]): string {
  const unique = [...new Set(names)]
  if (unique.length === 0) return 'its source dataset'
  if (unique.length === 1) return unique[0] as string
  return `${unique.slice(0, -1).join(', ')} or ${unique[unique.length - 1]}`
}

/** "listed in <dataset> as sanctioned" and the like, one per flag that is set. */
export function flagBadges(flags: NodeFlags, datasetNames: readonly string[]): FlagBadge[] {
  const source = joinDatasetNames(datasetNames)
  return FLAG_PHRASES.filter(([kind]) => flags[kind]).map(([kind, phrase]) => ({
    kind,
    text: `listed in ${source} ${phrase}`,
  }))
}

/** The `datasets` property of a graph node or edge as a list of slugs (empty when absent). */
export function datasetsOf(properties: Record<string, unknown>): string[] {
  const value = properties.datasets
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}
