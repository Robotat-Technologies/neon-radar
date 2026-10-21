import { describe, expect, it } from 'vitest'

import { disclaimers, registry } from '@/__tests__/fixtures'
import { dataNoticeText, selectDataNotice } from '@/lib/notices'

describe('selectDataNotice', () => {
  it('shows the synthetic demo notice when only synthetic datasets are loaded', () => {
    expect(selectDataNotice(registry({ nr_synthetic: 1200 }))).toBe('synthetic_demo')
  })

  it('shows the real data notice when any real dataset is loaded', () => {
    expect(selectDataNotice(registry({ nr_synthetic: 1200, gleif_lei: 3 }))).toBe('real_data')
    expect(selectDataNotice(registry({ gb_companies_house: 1 }))).toBe('real_data')
  })

  it('ignores real datasets that are registered but not loaded', () => {
    const datasets = registry({ nr_synthetic: 5 })
    expect(datasets.filter((d) => !d.synthetic)).toHaveLength(4)
    expect(selectDataNotice(datasets)).toBe('synthetic_demo')
  })

  it('shows the real data notice when the API could not count the records', () => {
    expect(selectDataNotice(registry({ nr_synthetic: null }))).toBe('real_data')
    expect(selectDataNotice(registry({ nr_synthetic: 5, gleif_lei: null }))).toBe('real_data')
  })

  it('treats an empty graph as nothing real loaded', () => {
    expect(selectDataNotice(registry())).toBe('synthetic_demo')
  })
})

describe('dataNoticeText', () => {
  it('returns the served texts verbatim', () => {
    expect(dataNoticeText('synthetic_demo', disclaimers)).toBe(disclaimers.synthetic_demo)
    expect(dataNoticeText('real_data', disclaimers)).toBe(disclaimers.real_data)
    expect(disclaimers.synthetic_demo.startsWith('Synthetic data. Every company')).toBe(true)
    expect(disclaimers.real_data.startsWith('This view includes records from public')).toBe(true)
  })
})
