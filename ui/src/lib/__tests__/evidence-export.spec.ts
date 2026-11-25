import { afterEach, describe, expect, it, vi } from 'vitest'

import { readExample } from '@/__tests__/fixtures'
import type { Alert, AlertDetail, Subgraph } from '@/api/types'
import { downloadWithNotice, evidenceCsv } from '@/lib/evidence-export'
import { notify } from '@/lib/notifications'

vi.mock('@/lib/notifications', () => ({ notify: vi.fn<typeof notify>() }))

function detail(): AlertDetail {
  return {
    alert: readExample<Alert>('c4/circular_flow.json'),
    evidence: readExample<Subgraph>('c3/subgraph.json'),
  }
}

describe('evidenceCsv', () => {
  it('includes the alert, graph, nodes, relationships and provenance', () => {
    const example = detail()
    const csv = evidenceCsv(example)
    expect(csv.startsWith('﻿"Section","Item","Field","Value"\r\n')).toBe(true)
    expect(csv).toContain(`"Alert","${example.alert.alert_id}","headline"`)
    expect(csv).toContain('"Graph","Evidence graph","truncated"')
    expect(csv).toContain(`"Node","${example.evidence.nodes[0]!.id}","caption"`)
    expect(csv).toContain(`"Relationship","${example.evidence.edges[0]!.id}","source"`)
    expect(csv).toContain('"explanation.typology_reference.citations[1]"')
    expect(csv).toContain('"evidence.query.cypher"')
  })

  it('quotes special characters and neutralizes spreadsheet formulas without changing numbers', () => {
    const example = detail()
    example.alert.headline = ' =SUM(1,2)\n"test"'
    example.alert.metrics = { numeric: -2, formula: '@test', tab: '\tcommand', plain: 'café' }
    const csv = evidenceCsv(example)
    expect(csv).toContain('"\' =SUM(1,2)\n""test"""')
    expect(csv).toContain('"metrics.numeric","-2"')
    expect(csv).toContain('"metrics.formula","\'@test"')
    expect(csv).toContain('"metrics.tab","\'\tcommand"')
    expect(csv).toContain('"metrics.plain","café"')
  })

  it('represents empty collections and a truncated graph', () => {
    const example = detail()
    example.evidence.nodes = []
    example.evidence.edges = []
    example.evidence.truncated = true
    expect(evidenceCsv(example)).toContain('"Nodes","","","[]"')
    expect(evidenceCsv(example)).toContain('"Relationships","","","[]"')
    expect(evidenceCsv(example)).toContain('"Graph","Evidence graph","truncated","true"')
  })
})

describe('downloadWithNotice', () => {
  const text = { started: 'Download started.', failed: 'The download could not start.' }
  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.mocked(notify).mockClear()
  })

  it('says the download started, not that a file was saved', () => {
    vi.stubGlobal('URL', { createObjectURL: () => 'blob:evidence', revokeObjectURL: () => {} })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    downloadWithNotice(detail(), 'json', text)
    expect(notify).toHaveBeenCalledExactlyOnceWith({
      severity: 'info',
      message: 'Download started.',
      dedupeKey: 'evidence-download',
    })
  })

  it('reports a download that cannot start, without the raw error', () => {
    vi.stubGlobal('URL', {}) // URL.createObjectURL is missing, so the download throws
    downloadWithNotice(detail(), 'csv', text)
    expect(notify).toHaveBeenCalledExactlyOnceWith({
      severity: 'error',
      message: 'The download could not start.',
      dedupeKey: 'evidence-download',
    })
  })
})
