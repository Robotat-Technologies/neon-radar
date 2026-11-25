import { mount, RouterLinkStub } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import { readExample } from '@/__tests__/fixtures'
import type { GraphEdge, Subgraph } from '@/api/types'

const { cytoscapeMock, useMock } = vi.hoisted(() => ({
  cytoscapeMock: vi.fn<(...args: unknown[]) => unknown>(),
  useMock: vi.fn<(...args: unknown[]) => unknown>(),
}))

vi.mock('cytoscape', () => ({
  default: Object.assign(cytoscapeMock, { use: useMock }),
}))
vi.mock('cytoscape-fcose', () => ({ default: {} }))

import GraphCanvas from '@/components/GraphCanvas.vue'

const example = readExample<Subgraph>('c3/subgraph.json')

function mountGraph(subgraph: Subgraph = example) {
  cytoscapeMock.mockReturnValue({
    destroy: vi.fn<(...args: unknown[]) => unknown>(),
    elements: () => ({ removeClass: vi.fn<(...args: unknown[]) => unknown>() }),
    getElementById: () => ({ addClass: vi.fn<(...args: unknown[]) => unknown>() }),
    on: vi.fn<(...args: unknown[]) => unknown>(),
  })

  return mount(GraphCanvas, {
    props: { subgraph, label: 'Network for Fenwhistle Holdings Ltd' },
    global: { stubs: { EntityBadges: true, RouterLink: RouterLinkStub } },
  })
}

describe('GraphCanvas accessibility', () => {
  it('describes the interactive graph and provides its typed visual key', () => {
    const wrapper = mountGraph()
    const canvas = wrapper.get('[data-testid="graph-canvas"]')
    const descriptionId = canvas.attributes('aria-describedby')

    expect(canvas.attributes('aria-label')).toBe('Network for Fenwhistle Holdings Ltd')
    expect(descriptionId).toBeTruthy()
    expect(wrapper.get(`#${descriptionId}`).text()).toContain(
      'Use the readable node and relationship lists below for a keyboard-accessible alternative.',
    )

    const key = wrapper.get('.graph__key').text()
    expect(key).toContain('Arrows point from the source node to the target node.')
    expect(key).toContain('A dashed outline marks a synthetic node.')
    expect(key).toContain('A dashed line marks a synthetic relationship.')
    expect(key).toContain('BankAccount nodes use a rectangle shape.')
    expect(key).toContain('Company nodes use a rounded rectangle shape.')
    expect(key).toContain('PAID means “paid”.')
    expect(key).toContain('HOLDS_ACCOUNT means “holds the account”.')
  })

  it('provides linked, readable alternatives for every relationship', () => {
    const wrapper = mountGraph()
    const relationships = wrapper.get('.graph__relationships')

    expect(relationships.get('summary').text()).toBe('Readable relationships (5)')
    const relationshipItems = relationships.findAll('.graph__relationship')
    expect(relationshipItems).toHaveLength(5)
    expect(relationshipItems[0]?.attributes('aria-label')).toBe(
      'NRSYN0000000007 made a payment of EUR 120,000.00 to NRSYN0000000012 (PAID)',
    )
    expect(relationshipItems[4]?.attributes('aria-label')).toBe(
      'Fenwhistle Holdings Ltd holds the account NRSYN0000000007 (HOLDS_ACCOUNT)',
    )
    expect(relationships.findAll('a')).toHaveLength(10)
  })

  it('keeps an unconfirmed possible match explicit in the key and readable alternative', () => {
    const possibleMatch: GraphEdge = {
      ...example.edges[0]!,
      id: 'syn-possible-match-0001',
      type: 'POSSIBLY_SAME_AS',
    }
    const wrapper = mountGraph({ ...example, edges: [possibleMatch] })

    expect(wrapper.get('.graph__key').text()).toContain(
      'POSSIBLY_SAME_AS has no arrow and means the match is not confirmed.',
    )
    expect(wrapper.get('.graph__relationships').text()).toContain(
      'may describe the same entity as (not confirmed)',
    )
  })
})
