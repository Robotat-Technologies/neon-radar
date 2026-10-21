// Search result wording. `total_estimate` is a lower bound (C3): the label-filtered hits within
// the API's first 200 full-text hits, plus exact account-number matches.
import type { SearchResponse } from '@/api/types'

/** The full-text hits the API reads before filtering by label (C3 `SearchResponse`). */
export const SEARCH_WINDOW = 200

/** The line above the hits, for example `About 25 matches for “lea”.` */
export function searchCountText(answer: SearchResponse): string {
  const total = answer.total_estimate
  if (answer.items.length === 0) return `No matches for “${answer.query}”.`
  if (total >= SEARCH_WINDOW) return `${SEARCH_WINDOW} or more matches for “${answer.query}”.`
  const noun = total === 1 ? 'match' : 'matches'
  const about = total > answer.items.length ? 'About ' : ''
  return `${about}${total} ${noun} for “${answer.query}”.`
}
