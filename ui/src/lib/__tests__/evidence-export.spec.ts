import { describe, expect, it } from 'vitest'

import { readExample } from '@/__tests__/fixtures'
import type { Alert, AlertDetail, Subgraph } from '@/api/types'
import { evidenceCsv } from '@/lib/evidence-export'

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
