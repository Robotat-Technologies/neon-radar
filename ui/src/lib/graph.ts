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

export function edgeClasses(edge: GraphEdge): string[] {
  const classes = [`type-${edge.type.toLowerCase()}`]
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

/** The label drawn on an edge: the amount for a payment, otherwise the relationship type. */
export function edgeLabel(edge: Pick<GraphEdge, 'type' | 'properties'>): string {
  const { amount, currency } = edge.properties
  if (edge.type === 'PAID' && typeof amount === 'number' && typeof currency === 'string') {
    return formatAmount(amount, currency)
  }
  return edge.type
}
