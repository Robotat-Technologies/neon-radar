// When the graph shows text (level of detail). Pure geometry in screen pixels, so the rule is
// tested without a canvas:
// 1. 50 or more relationships in view (their middle on screen) is an overview: no relationship text, except on the
//    alert path (amounts and step numbers).
// 2. Otherwise a relationship shows its text when its line is at least the text width plus
//    24 px long and the text covers no node and no other text.
// 3. Account numbers show from 150% of the fitted zoom, outside an overview, or when the
//    account is on the alert path or is the page's entity. Other entity names always show.

export const OVERVIEW_EDGES = 50
export const LABEL_SLACK = 24
export const ACCOUNT_LABEL_ZOOM = 1.5

export interface Box {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface EdgeCandidate {
  id: string
  source: string
  target: string
  /** Where the line leaves the source node and meets the target node. */
  start: { x: number; y: number }
  end: { x: number; y: number }
  /** The label's centre. */
  mid: { x: number; y: number }
  /** The label's size, unrotated. */
  width: number
  height: number
  /** On the alert path: always labelled, and placed first. */
  priority: boolean
}

export interface NodeBox extends Box {
  id: string
}

export function overlaps(a: Box, b: Box): boolean {
  return a.x1 < b.x2 && b.x1 < a.x2 && a.y1 < b.y2 && b.y1 < a.y2
}

function lengthOf(edge: EdgeCandidate): number {
  return Math.hypot(edge.end.x - edge.start.x, edge.end.y - edge.start.y)
}

/** In view: where its text would go (the middle of the line) is on screen. */
export function inView(edge: EdgeCandidate, view: Box): boolean {
  return (
    edge.mid.x >= view.x1 && edge.mid.x <= view.x2 && edge.mid.y >= view.y1 && edge.mid.y <= view.y2
  )
}

/** The screen box of a label drawn along its line (the text turns with the line). */
export function labelBox(edge: EdgeCandidate): Box {
  const angle = Math.atan2(edge.end.y - edge.start.y, edge.end.x - edge.start.x)
  const cos = Math.abs(Math.cos(angle))
  const sin = Math.abs(Math.sin(angle))
  const halfW = (edge.width * cos + edge.height * sin) / 2
  const halfH = (edge.width * sin + edge.height * cos) / 2
  return {
    x1: edge.mid.x - halfW,
    y1: edge.mid.y - halfH,
    x2: edge.mid.x + halfW,
    y2: edge.mid.y + halfH,
  }
}

export interface LabelChoice {
  overview: boolean
  shown: Set<string>
}

export function chooseEdgeLabels(
  edges: readonly EdgeCandidate[],
  nodes: readonly NodeBox[],
  view: Box,
): LabelChoice {
  const visible = edges.filter((edge) => inView(edge, view))
  const overview = visible.length >= OVERVIEW_EDGES
  const ordered = [...visible].sort(
    (a, b) => Number(b.priority) - Number(a.priority) || lengthOf(b) - lengthOf(a),
  )
  const placed: Box[] = []
  const shown = new Set<string>()
  for (const edge of ordered) {
    if (!edge.priority) {
      if (overview || lengthOf(edge) < edge.width + LABEL_SLACK) continue
    }
    const box = labelBox(edge)
    const hitsNode = nodes.some(
      (node) => node.id !== edge.source && node.id !== edge.target && overlaps(box, node),
    )
    if (!edge.priority && (hitsNode || placed.some((other) => overlaps(box, other)))) continue
    placed.push(box)
    shown.add(edge.id)
  }
  return { overview, shown }
}

/** Whether an account's number shows; `relativeZoom` is the zoom over the fitted zoom. */
export function showsAccountLabel(
  relativeZoom: number,
  overview: boolean,
  pinned: boolean,
): boolean {
  return pinned || (!overview && relativeZoom >= ACCOUNT_LABEL_ZOOM - 1e-9)
}
