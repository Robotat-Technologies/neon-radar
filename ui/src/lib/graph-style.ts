// Cytoscape style sheet: shapes by schema, a dashed outline for synthetic nodes, and the
// highlight classes the pages set. Plain colours for now; the visual identity arrives in Phase 5.
import type { EdgeSingular, StylesheetJson } from 'cytoscape'

import type { GraphEdge } from '@/api/types'
import { edgeLabel } from './graph'

export const graphStyle: StylesheetJson = [
  {
    selector: 'node',
    style: {
      label: 'data(caption)',
      'background-color': '#64748b',
      color: '#1f2933',
      'font-size': 10,
      'text-valign': 'bottom',
      'text-margin-y': 4,
      'text-wrap': 'ellipsis',
      'text-max-width': '140px',
      width: 26,
      height: 26,
    },
  },
  { selector: 'node.schema-person', style: { shape: 'ellipse', 'background-color': '#2f6fbf' } },
  {
    selector:
      'node.schema-company, node.schema-organization, node.schema-publicbody, node.schema-legalentity',
    style: { shape: 'round-rectangle', 'background-color': '#6d4fb3' },
  },
  {
    selector: 'node.schema-bankaccount',
    style: { shape: 'rectangle', 'background-color': '#1f8a7a' },
  },
  { selector: 'node.schema-address', style: { shape: 'diamond', 'background-color': '#a16207' } },
  { selector: 'node.schema-position', style: { shape: 'hexagon', 'background-color': '#64748b' } },
  { selector: 'node.schema-sanction', style: { shape: 'tag', 'background-color': '#9f1239' } },
  {
    selector: 'node.synthetic',
    style: { 'border-width': 2, 'border-style': 'dashed', 'border-color': '#334155' },
  },
  {
    selector: 'node.focus',
    style: { 'border-width': 4, 'border-style': 'solid', 'border-color': '#d97706' },
  },
  {
    selector: 'edge',
    style: {
      label: (edge: EdgeSingular) => edgeLabel(edge.data() as GraphEdge),
      width: 1.5,
      'curve-style': 'bezier',
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'font-size': 8,
      color: '#334155',
      'text-rotation': 'autorotate',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.8,
    },
  },
  { selector: 'edge.synthetic', style: { 'line-style': 'dashed' } },
  {
    selector: 'edge.highlighted',
    style: {
      width: 4,
      'line-style': 'solid',
      'line-color': '#d97706',
      'target-arrow-color': '#d97706',
    },
  },
]

export const fcoseLayout = {
  name: 'fcose',
  animate: false,
  randomize: true,
  quality: 'default',
  nodeSeparation: 90,
  idealEdgeLength: 110,
}
