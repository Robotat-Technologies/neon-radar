// Cytoscape style sheet, visual language version 2. Entities are pale shapes with an ink
// outline (the shape gives the schema, a dashed outline marks a synthetic node). Relationships
// carry the colour, and each family differs in colour, line, end marker and text, so any one of
// them tells it apart (also without colour). The alert path overrides the family style. Text
// keeps one size on screen whatever the zoom; graph-labels.ts decides when it shows. Highlights
// change width and colour only, never the dash, so a synthetic node stays marked.
import type { EdgeSingular, NodeSingular, StylesheetJson } from 'cytoscape'

import type { GraphEdge } from '@/api/types'
import { edgeLabel } from './graph'

export const INK = '#1f2933'
export const GRAPH_FONT = 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif'
export const LABEL_PX = 12
export const ALERT = '#ea580c'

/** The colour of each relationship family; text in that colour is at least 5.4:1 on white. */
export const FAMILY_COLOURS = {
  money: '#0f766e',
  ownership: '#1d4ed8',
  roles: '#7e22ce',
  account: '#475569',
  address: '#92400e',
  match: INK,
  other: '#52606d',
} as const

/** A size in model units that draws as `px` screen pixels at the current zoom. */
function screen(px: number) {
  return (element: NodeSingular | EdgeSingular) => px / element.cy().zoom()
}

/** The same, as a CSS length, for the properties typed as strings. */
function screenPx(px: number) {
  return (element: NodeSingular | EdgeSingular) => `${px / element.cy().zoom()}px`
}

/** The text of an edge, with its step number on the alert path. */
export function stepText(edge: EdgeSingular): string {
  const text = edgeLabel(edge.data() as GraphEdge)
  const step = edge.data('step') as number | undefined
  return step ? `Step ${step}: ${text}` : text
}

export const graphStyle: StylesheetJson = [
  {
    selector: 'node',
    style: {
      label: '',
      'font-family': GRAPH_FONT,
      'font-size': screenPx(LABEL_PX),
      color: INK,
      'text-valign': 'bottom',
      'text-margin-y': screen(4),
      'text-wrap': 'ellipsis',
      'text-max-width': '160px',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.85,
      'text-background-padding': screenPx(2),
      'background-color': '#e5e7eb',
      'border-width': screen(1.5),
      'border-color': INK,
      'border-style': 'solid',
      width: 26,
      height: 26,
    },
  },
  { selector: 'node.label-on', style: { label: 'data(caption)' } },
  { selector: 'node.schema-person', style: { shape: 'ellipse', 'background-color': '#dbeafe' } },
  {
    selector:
      'node.schema-company, node.schema-organization, node.schema-publicbody, node.schema-legalentity',
    style: { shape: 'round-rectangle', 'background-color': '#ede9fe' },
  },
  {
    selector: 'node.schema-bankaccount',
    style: { shape: 'round-rectangle', width: 34, height: 18, 'background-color': '#ccfbf1' },
  },
  { selector: 'node.schema-address', style: { shape: 'diamond', 'background-color': '#fef3c7' } },
  { selector: 'node.schema-position', style: { shape: 'hexagon', 'background-color': '#e5e7eb' } },
  { selector: 'node.schema-sanction', style: { shape: 'tag', 'background-color': '#ffe4e6' } },
  { selector: 'node.synthetic', style: { 'border-style': 'dashed' } },
  {
    selector: 'node.alert-node',
    style: {
      'underlay-color': ALERT,
      'underlay-opacity': 1,
      'underlay-padding': 4,
      'underlay-shape': 'round-rectangle',
    },
  },
  {
    selector: 'node.focus',
    style: { 'border-width': screen(3), 'font-weight': 'bold', width: 34, height: 34 },
  },
  {
    selector: 'edge',
    style: {
      label: '',
      'font-family': GRAPH_FONT,
      'font-size': screenPx(LABEL_PX),
      'font-weight': 600,
      'text-rotation': 'autorotate',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.9,
      'text-background-padding': screenPx(2),
      'curve-style': 'bezier',
      width: screen(1.5),
      'arrow-scale': 1,
      'line-color': FAMILY_COLOURS.other,
      'target-arrow-color': FAMILY_COLOURS.other,
      'target-arrow-shape': 'triangle',
      color: FAMILY_COLOURS.other,
    },
  },
  { selector: 'edge.label-on', style: { label: stepText } },
  {
    selector: 'edge.family-money',
    style: {
      'line-color': FAMILY_COLOURS.money,
      'target-arrow-color': FAMILY_COLOURS.money,
      color: FAMILY_COLOURS.money,
    },
  },
  {
    // A double line: a white core inside a blue outline, with a hollow arrow.
    selector: 'edge.family-ownership',
    style: {
      'line-color': '#ffffff',
      'line-outline-width': screen(1.5),
      'line-outline-color': FAMILY_COLOURS.ownership,
      'target-arrow-color': FAMILY_COLOURS.ownership,
      'target-arrow-fill': 'hollow',
      'arrow-scale': 1.3,
      color: FAMILY_COLOURS.ownership,
    },
  },
  {
    selector: 'edge.family-roles',
    style: {
      'line-style': 'dashed',
      'line-dash-pattern': [7, 3.5],
      'line-color': FAMILY_COLOURS.roles,
      'target-arrow-shape': 'chevron',
      'target-arrow-color': FAMILY_COLOURS.roles,
      color: FAMILY_COLOURS.roles,
    },
  },
  {
    selector: 'edge.family-account',
    style: {
      width: screen(1.25),
      'line-color': FAMILY_COLOURS.account,
      'target-arrow-shape': 'circle',
      'target-arrow-color': FAMILY_COLOURS.account,
      color: FAMILY_COLOURS.account,
    },
  },
  {
    selector: 'edge.family-address',
    style: {
      width: screen(2.25),
      'line-style': 'dotted',
      'line-cap': 'round',
      'line-color': FAMILY_COLOURS.address,
      'target-arrow-shape': 'none',
      color: FAMILY_COLOURS.address,
    },
  },
  {
    // POSSIBLY_SAME_AS is undirected (C3 1.1.0): dash-dot, no arrow.
    selector: 'edge.family-match',
    style: {
      'line-style': 'dashed',
      'line-dash-pattern': [10, 3, 2, 3],
      'line-color': FAMILY_COLOURS.match,
      'target-arrow-shape': 'none',
      color: FAMILY_COLOURS.match,
    },
  },
  {
    // The alert path: orange on a white casing, drawn above every other line. Width and colour
    // only, so a family's dash survives.
    selector: 'edge.alert-path',
    style: {
      width: screen(4.5),
      'line-color': ALERT,
      'line-outline-width': screen(2.5),
      'line-outline-color': '#ffffff',
      'target-arrow-color': ALERT,
      'target-arrow-fill': 'filled',
      'arrow-scale': 1.1,
      'z-index': 10,
      color: INK,
    },
  },
  { selector: 'edge.filtered', style: { display: 'none' } },
  {
    selector: 'edge.highlighted',
    style: { width: screen(8), 'line-color': ALERT, 'target-arrow-color': ALERT, 'z-index': 20 },
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
