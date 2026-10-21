// Which data notice the UI shows next to the standing disclaimer (PHASE-1.md M1.9d and 7.1;
// contracts/C3-api.md "Meta and health"). The texts themselves come from GET /meta, verbatim.
import type { DatasetInfo, Disclaimers } from '@/api/types'

export type DataNoticeKind = 'synthetic_demo' | 'real_data'

/**
 * The synthetic demo notice only when every loaded dataset (record_count above 0) is synthetic;
 * otherwise the real data notice. The registry always lists the real sources, so registered but
 * unloaded datasets change nothing. A null record_count means the API could not read the graph,
 * so nothing is known about what is loaded: the real data notice then.
 */
export function selectDataNotice(datasets: readonly DatasetInfo[]): DataNoticeKind {
  if (datasets.some((dataset) => dataset.record_count === null)) return 'real_data'
  const loaded = datasets.filter((dataset) => (dataset.record_count ?? 0) > 0)
  return loaded.every((dataset) => dataset.synthetic) ? 'synthetic_demo' : 'real_data'
}

export function dataNoticeText(kind: DataNoticeKind, disclaimers: Disclaimers): string {
  return kind === 'synthetic_demo' ? disclaimers.synthetic_demo : disclaimers.real_data
}
