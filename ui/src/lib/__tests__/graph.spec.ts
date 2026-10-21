import { describe, expect, it } from 'vitest'

import { readExample } from '@/__tests__/fixtures'
import type { Subgraph } from '@/api/types'
import { edgeLabel, opensEntityPage, toCytoscapeElements } from '@/lib/graph'

const example = readExample<Subgraph>('c3/subgraph.json')

describe('toCytoscapeElements', () => {
  it('maps every node and edge of the C3 example one to one', () => {
    const elements = toCytoscapeElements(example)
    const nodes = elements.filter((element) => element.group === 'nodes')
    const edges = elements.filter((element) => element.group === 'edges')

    expect(nodes).toHaveLength(example.nodes.length)
    expect(edges).toHaveLength(example.edges.length)
    nodes.forEach((element, index) => expect(element.data).toEqual(example.nodes[index]))
    edges.forEach((element, index) => expect(element.data).toEqual(example.edges[index]))
  })

  it('puts nodes before edges and keeps the C2 ids, source and target', () => {
    const elements = toCytoscapeElements(example)
    const firstEdge = elements.findIndex((element) => element.group === 'edges')
    expect(elements.slice(firstEdge).every((element) => element.group === 'edges')).toBe(true)

    const paid = elements.find((element) => element.data.id === 'syn-payment-000104')
    expect(paid?.data).toMatchObject({
      source: 'syn-acct-0021',
      target: 'syn-acct-0007',
      type: 'PAID',
    })
  })

  it('adds classes for schema, flags and relationship type', () => {
    const elements = toCytoscapeElements(example)
    const company = elements.find((element) => element.data.id === 'syn-co-0003')
    const account = elements.find((element) => element.data.id === 'syn-acct-0007')
    const holds = elements.find((element) => element.data.id === 'syn-ownership-0007')

    expect(company?.classes).toEqual(['schema-company', 'synthetic'])
    expect(account?.classes).toEqual(['schema-bankaccount', 'synthetic'])
    expect(holds?.classes).toEqual(['type-holds_account', 'synthetic'])
  })

  it('marks source-data flags and leaves synthetic off for real nodes', () => {
    const subgraph: Subgraph = {
      nodes: [
        {
          // A never-real company number (T prefix), as in contracts/tests (guardrail G1).
          id: 'gbch-co-T0000001',
          labels: ['Entity', 'LegalEntity', 'Organization', 'Company'],
          schema: 'Company',
          caption: 'Example',
          flags: { synthetic: false, sanctioned: true, pep: false, rca: true },
          properties: {},
        },
      ],
      edges: [],
      truncated: false,
      limits: { max_nodes: 1, max_edges: 2 },
    }
    expect(toCytoscapeElements(subgraph)[0]?.classes).toEqual([
      'schema-company',
      'sanctioned',
      'rca',
    ])
  })

  it('leaves out an edge whose endpoint is missing instead of failing', () => {
    const subgraph: Subgraph = { ...example, nodes: example.nodes.slice(1) }
    const missing = example.nodes[0]?.id
    const edges = toCytoscapeElements(subgraph).filter((element) => element.group === 'edges')

    expect(edges.length).toBeLessThan(example.edges.length)
    expect(edges.some((e) => e.data.source === missing || e.data.target === missing)).toBe(false)
  })

  it('returns no elements for an empty subgraph', () => {
    const empty: Subgraph = {
      nodes: [],
      edges: [],
      truncated: false,
      limits: { max_nodes: 1, max_edges: 2 },
    }
    expect(toCytoscapeElements(empty)).toEqual([])
  })
})

describe('edgeLabel', () => {
  it('shows a payment amount with its currency and the type otherwise', () => {
    expect(edgeLabel({ type: 'PAID', properties: { amount: 115200.0, currency: 'EUR' } })).toBe(
      'EUR 115,200.00',
    )
    expect(edgeLabel({ type: 'PAID', properties: { amount: 5, currency: 'JPY' } })).toBe('JPY 5')
    expect(edgeLabel({ type: 'HOLDS_ACCOUNT', properties: {} })).toBe('HOLDS_ACCOUNT')
    expect(edgeLabel({ type: 'PAID', properties: {} })).toBe('PAID')
  })
})

describe('opensEntityPage', () => {
  it('opens entities but not sanction records', () => {
    expect(opensEntityPage({ schema: 'Company' })).toBe(true)
    expect(opensEntityPage({ schema: 'BankAccount' })).toBe(true)
    expect(opensEntityPage({ schema: 'Sanction' })).toBe(false)
  })
})
