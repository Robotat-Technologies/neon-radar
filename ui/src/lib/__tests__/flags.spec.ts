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
})
