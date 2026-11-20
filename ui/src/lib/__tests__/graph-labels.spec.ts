import { describe, expect, it } from 'vitest'

import {
  chooseEdgeLabels,
  type EdgeCandidate,
  inView,
  labelBox,
  type NodeBox,
  OVERVIEW_EDGES,
  showsAccountLabel,
} from '@/lib/graph-labels'

const VIEW = { x1: 0, y1: 0, x2: 1000, y2: 800 }

/** A horizontal edge from (x, y) of the given length, with a 60 x 18 label. */
function edge(id: string, x: number, y: number, length: number, priority = false): EdgeCandidate {
  return {
    id,
    source: `${id}-s`,
    target: `${id}-t`,
    start: { x, y },
    end: { x: x + length, y },
    mid: { x: x + length / 2, y },
    width: 60,
    height: 18,
    priority,
  }
}

describe('chooseEdgeLabels', () => {
  it('shows text on a line long enough to hold it plus 24 px', () => {
    const { overview, shown } = chooseEdgeLabels(
      [edge('long', 0, 100, 84), edge('short', 0, 300, 83)],
      [],
      VIEW,
    )
    expect(overview).toBe(false)
    expect([...shown]).toEqual(['long'])
  })

  it('hides relationship text in an overview but keeps the alert path', () => {
    const edges = Array.from({ length: OVERVIEW_EDGES }, (_, i) => edge(`e${i}`, 0, i * 15, 400))
    edges.push(edge('alert', 500, 20, 40, true))
    const { overview, shown } = chooseEdgeLabels(edges, [], VIEW)
    expect(overview).toBe(true)
    expect([...shown]).toEqual(['alert'])
  })

  it('counts only the relationships in view', () => {
    const edges = Array.from({ length: OVERVIEW_EDGES }, (_, i) => edge(`e${i}`, 2000, i * 15, 400))
    edges.push(edge('here', 0, 100, 200))
    expect([...chooseEdgeLabels(edges, [], VIEW).shown]).toEqual(['here'])
  })

  it('leaves out text that would cover a node or other text', () => {
    const node: NodeBox = { id: 'n', x1: 90, y1: 90, x2: 110, y2: 110 }
    const { shown } = chooseEdgeLabels(
      [edge('over-node', 0, 100, 200), edge('first', 400, 100, 300), edge('second', 420, 105, 250)],
      [node],
      VIEW,
    )
    expect([...shown]).toEqual(['first'])
  })

  it('does not count the end nodes of the edge as covered', () => {
    const line = edge('own', 0, 100, 200)
    const ends: NodeBox[] = [
      { id: 'own-s', x1: -10, y1: 60, x2: 140, y2: 140 },
      { id: 'own-t', x1: 60, y1: 60, x2: 210, y2: 140 },
    ]
    expect([...chooseEdgeLabels([line], ends, VIEW).shown]).toEqual(['own'])
  })
})

describe('inView', () => {
  it('counts a relationship whose middle is on screen, not one that only passes through', () => {
    const passing = {
      ...edge('a', -500, 400, 0),
      end: { x: 1500, y: 400 },
      mid: { x: 1300, y: 400 },
    }
    expect(inView(edge('b', 900, 400, 200), VIEW)).toBe(true)
    expect(inView(passing, VIEW)).toBe(false)
  })
})

describe('labelBox', () => {
  it('turns with the line', () => {
    const flat = labelBox(edge('a', 0, 0, 100))
    expect(flat.x2 - flat.x1).toBeCloseTo(60)
    expect(flat.y2 - flat.y1).toBeCloseTo(18)
    const upright = labelBox({ ...edge('b', 0, 0, 100), end: { x: 0, y: 100 } })
    expect(upright.x2 - upright.x1).toBeCloseTo(18)
    expect(upright.y2 - upright.y1).toBeCloseTo(60)
  })
})

describe('showsAccountLabel', () => {
  it('shows account numbers from 150% zoom outside an overview, or when pinned', () => {
    expect(showsAccountLabel(1.49, false, false)).toBe(false)
    expect(showsAccountLabel(1.5, false, false)).toBe(true)
    expect(showsAccountLabel(3, true, false)).toBe(false)
    expect(showsAccountLabel(1, true, true)).toBe(true)
  })
})
