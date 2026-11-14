<script setup lang="ts">
// A Cytoscape canvas for a C3 Subgraph (fcose layout), with a legend and the same nodes as a
// list, because a canvas says nothing to a screen reader.
import cytoscape, { type Core, type EdgeSingular, type LayoutOptions } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { messages } from '@/lib/messages'
import { displayTerm } from '@/lib/terms'
import { useLocaleStore } from '@/stores/locale'
import type { GraphEdge, GraphNode, Subgraph } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import { datasetsOf } from '@/lib/flags'
import { edgeLabel, opensEntityPage, toCytoscapeElements } from '@/lib/graph'
import { fcoseLayout, graphStyle } from '@/lib/graph-style'

cytoscape.use(fcose)

const props = defineProps<{
  subgraph: Subgraph
  label: string
  focusIds?: readonly string[]
  highlightEdgeIds?: readonly string[]
}>()
const emit = defineEmits<{ select: [id: string] }>()
const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])
const container = ref<HTMLElement | null>(null)
let cy: Core | null = null

function applyHighlights(): void {
  if (!cy) return
  cy.elements().removeClass('focus highlighted')
  for (const id of props.focusIds ?? []) cy.getElementById(id).addClass('focus')
  for (const id of props.highlightEdgeIds ?? []) cy.getElementById(id).addClass('highlighted')
}
function applyLanguage(): void {
  if (!cy) return

  cy.style()
    .fromJson([
      ...graphStyle,
      {
        selector: 'edge',
        style: {
          label: (edge: EdgeSingular) => {
            const data = edge.data() as GraphEdge
            const label = edgeLabel(data)

            return label === data.type ? displayTerm(data.type, localeStore.locale) : label
          },
        },
      },
    ])
    .update()
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
  applyLanguage()
}

onMounted(render)
watch(() => props.subgraph, render)
watch(() => [props.focusIds, props.highlightEdgeIds], applyHighlights, { deep: true })
watch(() => localeStore.locale, applyLanguage)
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
      {{ text.graphCounts(props.subgraph.nodes.length, props.subgraph.edges.length) }}
      {{ text.graphHelp }}
      <strong v-if="props.subgraph.truncated">
        {{ text.graphTruncated(props.subgraph.limits.max_nodes, props.subgraph.limits.max_edges) }}
      </strong>
    </figcaption>

    <details class="graph__nodes">
      <summary>
        {{ text.graphNodes }} (<bdi>{{ props.subgraph.nodes.length }}</bdi
        >)
      </summary>

      <ul>
        <li v-for="node in props.subgraph.nodes" :key="node.id" class="row">
          <RouterLink
            v-if="opensEntityPage(node)"
            :to="{ name: 'entity', params: { id: node.id } }"
          >
            <bdi>{{ node.caption }}</bdi>
          </RouterLink>

          <span v-else
            ><bdi>{{ node.caption }}</bdi></span
          >
          <span class="muted"
            ><bdi>{{ displayTerm(node.schema, localeStore.locale) }}</bdi></span
          >
          <EntityBadges :flags="node.flags" :datasets="datasetsOf(node.properties)" />
        </li>
      </ul>
    </details>
  </figure>
</template>
