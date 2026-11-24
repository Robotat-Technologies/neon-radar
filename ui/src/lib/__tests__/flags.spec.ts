import { describe, expect, it } from 'vitest'

import { datasetsOf, flagBadges, joinDatasetNames } from '@/lib/flags'

const NONE = { synthetic: false, sanctioned: false, pep: false, rca: false }

describe('flagBadges', () => {
  it('uses the 7.1 vocabulary and names the dataset', () => {
    const all = { synthetic: false, sanctioned: true, pep: true, rca: true }
    expect(flagBadges(all, ['OpenSanctions (default collection)']).map((b) => b.text)).toEqual([
      'listed in OpenSanctions (default collection) as sanctioned',
      'listed in OpenSanctions (default collection) as a politically exposed person',
      'listed in OpenSanctions (default collection) as a relative or close associate of a politically exposed person',
    ])
  })

  it('shows nothing for a node without source-data flags, synthetic or not', () => {
    expect(flagBadges(NONE, ['NeonRadar synthetic data'])).toEqual([])
    expect(flagBadges({ ...NONE, synthetic: true }, ['NeonRadar synthetic data'])).toEqual([])
  })

  it('shows only the flags that are set', () => {
    expect(flagBadges({ ...NONE, pep: true }, ['NeonRadar synthetic data'])).toEqual([
      {
        kind: 'pep',
        text: 'listed in NeonRadar synthetic data as a politically exposed person',
      },
    ])
  })
})

describe('joinDatasetNames', () => {
  it('joins one, two or more names, without repeats', () => {
    expect(joinDatasetNames(['A'])).toBe('A')
    expect(joinDatasetNames(['A', 'B', 'A'])).toBe('A or B')
    expect(joinDatasetNames(['A', 'B', 'C'])).toBe('A, B or C')
    expect(joinDatasetNames([])).toBe('its source dataset')
  })
})

describe('datasetsOf', () => {
  it('reads the datasets property of a graph node or edge', () => {
    expect(datasetsOf({ datasets: ['nr_synthetic'] })).toEqual(['nr_synthetic'])
    expect(datasetsOf({ datasets: 'nr_synthetic' })).toEqual([])
    expect(datasetsOf({})).toEqual([])
  })

  describe('Arabic source-data flags', () => {
    it('names the source and describes each enabled flag', () => {
      const all = { ...NONE, sanctioned: true, pep: true, rca: true }

      expect(flagBadges(all, ['Demo source'], 'ar')).toEqual([
        {
          kind: 'sanctioned',
          text: 'مُدرج في \u2068Demo source\u2069 بصفة: خاضع للعقوبات',
        },
        {
          kind: 'pep',
          text: 'مُدرج في \u2068Demo source\u2069 بصفة: شخص معرّض سياسياً',
        },
        {
          kind: 'rca',
          text: 'مُدرج في \u2068Demo source\u2069 بصفة: قريب أو شريك مقرّب لشخص معرّض سياسياً',
        },
      ])
    })

    it('does not add flags to synthetic entities', () => {
      expect(flagBadges(NONE, ['Demo source'], 'ar')).toEqual([])
      expect(flagBadges({ ...NONE, synthetic: true }, ['Demo source'], 'ar')).toEqual([])
    })

    it('keeps alternative sources distinct and removes duplicate names', () => {
      expect(joinDatasetNames(['A', 'B', 'A'], 'ar')).toBe('\u2068A\u2069 أو \u2068B\u2069')

      expect(joinDatasetNames(['A', 'B', 'C'], 'ar')).toBe(
        '\u2068A\u2069، \u2068B\u2069 أو \u2068C\u2069',
      )
    })

    it('handles a missing source name without inventing one', () => {
      expect(flagBadges({ ...NONE, pep: true }, [], 'ar')).toEqual([
        {
          kind: 'pep',
          text: 'مُدرج في مجموعة البيانات المصدرية بصفة: شخص معرّض سياسياً',
        },
      ])
    })
  })
})
