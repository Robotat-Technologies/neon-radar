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
/** Joins possible source datasets without implying that every source lists the flag. */
export function joinDatasetNames(names: readonly string[], locale: 'en' | 'ar' = 'en'): string {
  const unique = [...new Set(names)]

  if (unique.length === 0) {
    return locale === 'ar' ? 'مجموعة البيانات المصدرية' : 'its source dataset'
  }

  const displayNames = locale === 'ar' ? unique.map((name) => `\u2068${name}\u2069`) : unique

  if (displayNames.length === 1) return displayNames[0] as string

  const separator = locale === 'ar' ? '، ' : ', '
  const or = locale === 'ar' ? ' أو ' : ' or '

  return `${displayNames.slice(0, -1).join(separator)}${or}${displayNames[displayNames.length - 1]}`
}

/** Describes source-published flags, always naming the possible source datasets. */
export function flagBadges(
  flags: NodeFlags,
  datasetNames: readonly string[],
  locale: 'en' | 'ar' = 'en',
): FlagBadge[] {
  const source = joinDatasetNames(datasetNames)

  if (locale === 'en') {
    return FLAG_PHRASES.filter(([kind]) => flags[kind]).map(([kind, phrase]) => ({
      kind,
      text: `listed in ${source} ${phrase}`,
    }))
  }

  const arabicSource = joinDatasetNames(datasetNames, 'ar')
  const phrases: Record<FlagKind, string> = {
    sanctioned: 'خاضع للعقوبات',
    pep: 'شخص معرّض سياسياً',
    rca: 'قريب أو شريك مقرّب لشخص معرّض سياسياً',
  }

  return FLAG_PHRASES.filter(([kind]) => flags[kind]).map(([kind]) => ({
    kind,
    text: `مُدرج في ${arabicSource} بصفة: ${phrases[kind]}`,
  }))
}

/** The `datasets` property of a graph node or edge as a list of slugs (empty when absent). */
export function datasetsOf(properties: Record<string, unknown>): string[] {
  const value = properties.datasets
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : []
}
