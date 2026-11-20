<script setup lang="ts">
// A Cytoscape canvas for a C3 Subgraph (fcose layout), with a legend and the same nodes as a
// list, because a canvas says nothing to a screen reader. Text follows the zoom rule in
// lib/graph-labels.ts: it keeps one size on screen and shows only where it fits.
import cytoscape, { type Core, type LayoutOptions } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { GraphNode, Subgraph } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import { datasetsOf } from '@/lib/flags'
import { opensEntityPage, toCytoscapeElements } from '@/lib/graph'
import { chooseEdgeLabels, showsAccountLabel } from '@/lib/graph-labels'
import { fcoseLayout, GRAPH_FONT, graphStyle, LABEL_PX, stepText } from '@/lib/graph-style'

cytoscape.use(fcose)

const props = defineProps<{
  subgraph: Subgraph
  label: string
  focusIds?: readonly string[]
  highlightEdgeIds?: readonly string[]
  /** The alert path: each edge id with its step number. */
  edgeSteps?: Readonly<Record<string, number>>
}>()
const emit = defineEmits<{ select: [id: string] }>()

const container = ref<HTMLElement | null>(null)
const syntheticEdges = computed(
  () => props.subgraph.edges.filter((edge) => edge.properties.synthetic === true).length,
)
let cy: Core | null = null
let fittedZoom = 1
let frame = 0
let measureContext: CanvasRenderingContext2D | null | undefined

function textWidth(text: string): number {
  if (measureContext === undefined) {
    measureContext = document.createElement('canvas').getContext('2d')
    if (measureContext) measureContext.font = `600 ${LABEL_PX}px ${GRAPH_FONT}`
  }
  return measureContext ? measureContext.measureText(text).width : text.length * LABEL_PX * 0.6
}

/** Re-sizes the text for the zoom and decides which text shows (lib/graph-labels.ts). */
function updateLabels(): void {
  frame = 0
  if (!cy) return
  const graph = cy
  graph.style().update()
  const nodes = graph.nodes(':visible').map((node) => ({
    id: node.id(),
    ...node.renderedBoundingBox({ includeLabels: false }),
  }))
  const edges = graph.edges(':visible').map((edge) => ({
    id: edge.id(),
    source: edge.source().id(),
    target: edge.target().id(),
    start: edge.renderedSourceEndpoint(),
    end: edge.renderedTargetEndpoint(),
    mid: edge.renderedMidpoint(),
    width: textWidth(stepText(edge)) + 6,
    height: LABEL_PX + 6,
    priority: edge.hasClass('alert-path'),
  }))
  const view = { x1: 0, y1: 0, x2: graph.width(), y2: graph.height() }
  const { overview, shown } = chooseEdgeLabels(edges, nodes, view)
  const relativeZoom = graph.zoom() / fittedZoom
  graph.batch(() => {
    graph.edges().forEach((edge) => {
      edge.toggleClass('label-on', shown.has(edge.id()))
    })
    graph.nodes().forEach((node) => {
      const pinned = node.hasClass('focus') || node.hasClass('alert-node')
      const on =
        !node.hasClass('schema-bankaccount') || showsAccountLabel(relativeZoom, overview, pinned)
      node.toggleClass('label-on', on)
    })
  })
}

function scheduleLabels(): void {
  if (!frame) frame = requestAnimationFrame(updateLabels)
}

function applyHighlights(): void {
  if (!cy) return
  const graph = cy
  graph.elements().removeClass('focus highlighted alert-path alert-node')
  graph.edges().removeData('step')
  for (const id of props.focusIds ?? []) graph.getElementById(id).addClass('focus')
  for (const [id, step] of Object.entries(props.edgeSteps ?? {})) {
    const edge = graph.getElementById(id)
    if (edge.empty()) continue
    edge.data('step', step).addClass('alert-path')
    edge.connectedNodes().addClass('alert-node')
  }
  for (const id of props.highlightEdgeIds ?? []) graph.getElementById(id).addClass('highlighted')
  scheduleLabels()
}

function render(): void {
  if (!container.value) return
  cy?.destroy()
  cy = cytoscape({
    container: container.value,
    elements: toCytoscapeElements(props.subgraph),
    style: graphStyle,
    layout: fcoseLayout as LayoutOptions,
    minZoom: 0.2,
    maxZoom: 5,
  })
  fittedZoom = cy.zoom()
  cy.on('viewport resize', scheduleLabels)
  cy.on('tap', 'node', (event) => {
    if (opensEntityPage(event.target.data() as GraphNode)) emit('select', String(event.target.id()))
  })
  applyHighlights()
}

onMounted(render)
watch(() => props.subgraph, render)
watch(() => [props.focusIds, props.highlightEdgeIds, props.edgeSteps], applyHighlights, {
  deep: true,
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  frame = 0
  cy?.destroy()
  cy = null
})
</script>

<template>
  <figure class="graph">
    <div
      ref="container"
      class="graph__canvas"
      role="img"
      :aria-label="props.label"
      data-testid="graph-canvas"
    ></div>
    <figcaption class="graph__legend">
      {{ props.subgraph.nodes.length }} nodes, {{ props.subgraph.edges.length }} relationships, of
      which {{ syntheticEdges }} are synthetic. A dashed outline marks a synthetic node; select a
      node to open it (sanction records stay in the graph and do not open). Zoom in to read the text
      on the relationships.
      <strong v-if="props.subgraph.truncated">
        The graph was cut at {{ props.subgraph.limits.max_nodes }} nodes and
        {{ props.subgraph.limits.max_edges }} relationships.
      </strong>
    </figcaption>
    <details class="graph__nodes">
      <summary>Nodes in this graph ({{ props.subgraph.nodes.length }})</summary>
      <ul>
        <li v-for="node in props.subgraph.nodes" :key="node.id" class="row">
          <RouterLink
            v-if="opensEntityPage(node)"
            :to="{ name: 'entity', params: { id: node.id } }"
            >{{ node.caption }}</RouterLink
          >
          <span v-else>{{ node.caption }}</span>
          <span class="muted">{{ node.schema }}</span>
          <EntityBadges :flags="node.flags" :datasets="datasetsOf(node.properties)" />
        </li>
      </ul>
    </details>
  </figure>
</template>
