// Contract C3 Subgraph -> Cytoscape elements. The mapping is one to one: a node becomes
// {data: {...node}} and an edge {data: {...edge}}, so the UI does no graph reshaping. Classes
// only carry what the style sheet needs (schema, flags, relationship type).
import type { ElementDefinition } from 'cytoscape'

import type { GraphEdge, GraphNode, Subgraph } from '@/api/types'
import { formatAmount } from './format'

export function nodeClasses(node: GraphNode): string[] {
  const classes = [`schema-${node.schema.toLowerCase()}`]
  if (node.flags.synthetic) classes.push('synthetic')
  if (node.flags.sanctioned) classes.push('sanctioned')
  if (node.flags.pep) classes.push('pep')
  if (node.flags.rca) classes.push('rca')
  return classes
}

/** The relationship families of the network's visual language; each has its own line style. */
export type RelationshipFamily =
  'money' | 'ownership' | 'roles' | 'account' | 'address' | 'match' | 'other'

const FAMILY: Partial<Record<GraphEdge['type'], RelationshipFamily>> = {
  PAID: 'money',
  OWNS: 'ownership',
  CONTROLS: 'ownership',
  CONSOLIDATES: 'ownership',
  DIRECTOR_OF: 'roles',
  REPRESENTS: 'roles',
  HOLDS_POSITION: 'roles',
  EMPLOYED_BY: 'roles',
  MEMBER_OF: 'roles',
  FAMILY_OF: 'roles',
  ASSOCIATE_OF: 'roles',
  HOLDS_ACCOUNT: 'account',
  HAS_ADDRESS: 'address',
  POSSIBLY_SAME_AS: 'match',
}

export function relationshipFamily(type: GraphEdge['type']): RelationshipFamily {
  return FAMILY[type] ?? 'other'
}

export function edgeClasses(edge: GraphEdge): string[] {
  const classes = [`type-${edge.type.toLowerCase()}`, `family-${relationshipFamily(edge.type)}`]
  if (edge.properties.synthetic === true) classes.push('synthetic')
  return classes
}

/**
 * Nodes first, then edges. C3 guarantees that every edge's endpoints are nodes of the subgraph;
 * an edge that breaks this is left out, because Cytoscape refuses to draw it.
 */
export function toCytoscapeElements(subgraph: Subgraph): ElementDefinition[] {
  const nodeIds = new Set(subgraph.nodes.map((node) => node.id))
  const nodes: ElementDefinition[] = subgraph.nodes.map((node) => ({
    group: 'nodes',
    data: { ...node },
    classes: nodeClasses(node),
  }))
  const edges: ElementDefinition[] = subgraph.edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map((edge) => ({
      group: 'edges',
      data: { ...edge },
      classes: edgeClasses(edge),
    }))
  return [...nodes, ...edges]
}

/**
 * Whether a node opens on the entity page. `:Sanction` nodes are sanction records, not entities:
 * they are shown in the graph but not opened as an entity.
 */
export function opensEntityPage(node: Pick<GraphNode, 'schema'>): boolean {
  return node.schema !== 'Sanction'
}

/**
 * The text drawn next to an edge, from the edge's own properties only: the amount of a payment,
 * the share band of an ownership, the recorded role, otherwise the relationship type in words.
 */
export function edgeLabel(edge: Pick<GraphEdge, 'type' | 'properties'>): string {
  const { amount, currency, role, share_pct_min: min, share_pct_max: max } = edge.properties
  const nominee = edge.properties.is_nominee === true ? 'nominee ' : ''
  switch (edge.type) {
    case 'PAID':
      return typeof amount === 'number' && typeof currency === 'string'
        ? formatAmount(amount, currency)
        : 'paid'
    case 'OWNS':
      if (typeof min === 'number' && typeof max === 'number') return `owns ${min}–${max}%`
      return typeof min === 'number' ? `owns ${min}% or more` : 'owns'
    case 'HOLDS_ACCOUNT':
      return 'holds'
    case 'POSSIBLY_SAME_AS':
      return 'possible match, not confirmed'
    default:
      if (relationshipFamily(edge.type) !== 'ownership' && typeof role === 'string' && role) {
        return `${nominee}${role}`
      }
      return edge.type.toLowerCase().replace(/_/g, ' ')
  }
}
