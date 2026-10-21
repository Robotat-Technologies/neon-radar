import { describe, expect, it } from 'vitest'

import type { SearchResponse } from '@/api/types'
import { SEARCH_WINDOW, searchCountText } from '@/lib/search'

function answer(total: number, shown: number): SearchResponse {
  const hit = { score: 1, matched_name: 'Lea' } as SearchResponse['items'][number]
  return { query: 'lea', items: Array.from({ length: shown }, () => hit), total_estimate: total }
}

describe('searchCountText', () => {
  it('says when nothing matched', () => {
    expect(searchCountText(answer(0, 0))).toBe('No matches for “lea”.')
  })

  it('gives the count when every match is shown', () => {
    expect(searchCountText(answer(1, 1))).toBe('1 match for “lea”.')
    expect(searchCountText(answer(3, 3))).toBe('3 matches for “lea”.')
  })

  it('calls a count above the shown hits an estimate', () => {
    expect(searchCountText(answer(25, 20))).toBe('About 25 matches for “lea”.')
  })

  it('never states a count once the API window is full', () => {
    expect(searchCountText(answer(SEARCH_WINDOW, 20))).toBe('200 or more matches for “lea”.')
    expect(searchCountText(answer(SEARCH_WINDOW + 1, 20))).toBe('200 or more matches for “lea”.')
  })
})
