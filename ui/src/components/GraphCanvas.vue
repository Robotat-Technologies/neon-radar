<script setup lang="ts">
// A Cytoscape canvas for a C3 Subgraph (fcose layout), with a legend and the same nodes as a
// list, because a canvas says nothing to a screen reader.
import cytoscape, { type Core, type LayoutOptions } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { GraphNode, Subgraph } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import { datasetsOf } from '@/lib/flags'
import { opensEntityPage, toCytoscapeElements } from '@/lib/graph'
import { fcoseLayout, graphStyle } from '@/lib/graph-style'

cytoscape.use(fcose)

const props = defineProps<{
  subgraph: Subgraph
  label: string
  focusIds?: readonly string[]
  highlightEdgeIds?: readonly string[]
}>()
const emit = defineEmits<{ select: [id: string] }>()

const container = ref<HTMLElement | null>(null)
let cy: Core | null = null

function applyHighlights(): void {
  if (!cy) return
  cy.elements().removeClass('focus highlighted')
  for (const id of props.focusIds ?? []) cy.getElementById(id).addClass('focus')
  for (const id of props.highlightEdgeIds ?? []) cy.getElementById(id).addClass('highlighted')
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
    maxZoom: 3,
  })
  cy.on('tap', 'node', (event) => {
    if (opensEntityPage(event.target.data() as GraphNode)) emit('select', String(event.target.id()))
  })
  applyHighlights()
}

onMounted(render)
watch(() => props.subgraph, render)
watch(() => [props.focusIds, props.highlightEdgeIds], applyHighlights, { deep: true })
onBeforeUnmount(() => {
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
      {{ props.subgraph.nodes.length }} nodes, {{ props.subgraph.edges.length }} relationships. A
      dashed outline marks a synthetic node; select a node to open it (sanction records stay in the
      graph and do not open).
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
