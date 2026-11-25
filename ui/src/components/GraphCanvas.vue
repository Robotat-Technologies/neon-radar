<script setup lang="ts">
// A Cytoscape canvas for a C3 Subgraph (fcose layout), with a legend and the same nodes as a
// list, because a canvas says nothing to a screen reader.
import cytoscape, { type Core, type LayoutOptions } from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { RouterLink } from 'vue-router'

import type { GraphEdge, GraphNode, Subgraph } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import UiIcon from '@/components/UiIcon.vue'
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

const descriptionId = `graph-description-${useId()}`

const schemaLegend: Record<GraphNode['schema'], string> = {
  Person: 'ellipse',
  Company: 'rounded rectangle',
  Organization: 'rounded rectangle',
  PublicBody: 'rounded rectangle',
  LegalEntity: 'rounded rectangle',
  Address: 'diamond',
  BankAccount: 'rectangle',
  Position: 'hexagon',
  Sanction: 'tag',
}

const relationshipText: Record<GraphEdge['type'], string> = {
  OWNS: 'owns',
  CONTROLS: 'controls',
  CONSOLIDATES: 'consolidates',
  DIRECTOR_OF: 'is a director of',
  HOLDS_ACCOUNT: 'holds the account',
  PAID: 'paid',
  HAS_ADDRESS: 'has an address at',
  REPRESENTS: 'represents',
  FAMILY_OF: 'is family of',
  ASSOCIATE_OF: 'is an associate of',
  MEMBER_OF: 'is a member of',
  EMPLOYED_BY: 'is employed by',
  LINKED_TO: 'is linked to',
  SUCCEEDED_BY: 'was succeeded by',
  HOLDS_POSITION: 'holds the position of',
  SUBJECT_OF: 'is subject of',
  POSSIBLY_SAME_AS: 'may describe the same entity as (not confirmed)',
}

const nodeLegend = computed(() =>
  [...new Set(props.subgraph.nodes.map((node) => node.schema))].map((schema) => ({
    schema,
    shape: schemaLegend[schema],
  })),
)
const relationshipLegend = computed(() =>
  [...new Set(props.subgraph.edges.map((edge) => edge.type))].map((type) => ({
    type,
    text: relationshipText[type],
  })),
)
const relationships = computed(() => {
  const nodesById = new Map(props.subgraph.nodes.map((node) => [node.id, node]))
  return props.subgraph.edges.flatMap((edge) => {
    const source = nodesById.get(edge.source)
    const target = nodesById.get(edge.target)
    return source && target ? [{ edge, source, target }] : []
  })
})
const hasSyntheticNodes = computed(() => props.subgraph.nodes.some((node) => node.flags.synthetic))
const hasSyntheticRelationships = computed(() =>
  props.subgraph.edges.some((edge) => edge.properties.synthetic === true),
)
const hasPossibleMatches = computed(() =>
  props.subgraph.edges.some((edge) => edge.type === 'POSSIBLY_SAME_AS'),
)

function readableRelationship(edge: GraphEdge): string {
  if (edge.type !== 'PAID') return relationshipText[edge.type]
  const amount = edgeLabel(edge)
  return amount === 'PAID' ? 'made a payment to' : `made a payment of ${amount} to`
}

const container = ref<HTMLElement | null>(null)
let cy: Core | null = null

function applyHighlights(): void {
  if (!cy) return
  cy.elements().removeClass('focus highlighted')
  for (const id of props.focusIds ?? []) cy.getElementById(id).addClass('focus')
  for (const id of props.highlightEdgeIds ?? []) cy.getElementById(id).addClass('highlighted')
}

function zoomBy(factor: number): void {
  if (!cy) return
  cy.zoom({
    level: Math.max(cy.minZoom(), Math.min(cy.maxZoom(), cy.zoom() * factor)),
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
  })
}

function fitGraph(): void {
  cy?.fit(undefined, 36)
}

function resetLayout(): void {
  cy?.layout(fcoseLayout as LayoutOptions).run()
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
    <div class="graph__toolbar">
      <span>Drag to pan · scroll to zoom</span>
      <div class="graph__controls" role="group" aria-label="Graph controls">
        <button type="button" aria-label="Zoom in" @click="zoomBy(1.25)">
          <UiIcon name="plus" />
        </button>
        <button type="button" aria-label="Zoom out" @click="zoomBy(0.8)">
          <UiIcon name="minus" />
        </button>
        <button type="button" @click="fitGraph"><UiIcon name="fit" />Fit</button>
        <button type="button" @click="resetLayout">Reset layout</button>
      </div>
    </div>
    <div
      ref="container"
      class="graph__canvas"
      role="img"
      :aria-label="props.label"
      :aria-describedby="descriptionId"
      data-testid="graph-canvas"
    ></div>
    <figcaption :id="descriptionId" class="graph__legend">
      <span class="graph__summary">
        {{ props.subgraph.nodes.length }} nodes, {{ props.subgraph.edges.length }} relationships.
      </span>
      <span class="graph__instructions">
        The graph can be panned and zoomed. Select an entity node to open it; sanction records
        remain in the graph and do not open. Use the readable node and relationship lists below for
        a keyboard-accessible alternative.
      </span>
      <strong v-if="props.subgraph.truncated" class="graph__truncation">
        The graph was cut at {{ props.subgraph.limits.max_nodes }} nodes and
        {{ props.subgraph.limits.max_edges }} relationships.
      </strong>
    </figcaption>
    <details class="graph__key">
      <summary>Graph key</summary>
      <ul class="graph__key-list">
        <li>Arrows point from the source node to the target node.</li>
        <li v-if="hasSyntheticNodes">A dashed outline marks a synthetic node.</li>
        <li v-if="hasSyntheticRelationships">A dashed line marks a synthetic relationship.</li>
        <li v-if="hasPossibleMatches">
          POSSIBLY_SAME_AS has no arrow and means the match is not confirmed.
        </li>
        <li v-for="item in nodeLegend" :key="item.schema">
          {{ item.schema }} nodes use a {{ item.shape }} shape.
        </li>
        <li v-for="item in relationshipLegend" :key="item.type">
          {{ item.type }} means “{{ item.text }}”.
        </li>
      </ul>
    </details>
    <details class="graph__nodes">
      <summary>Readable nodes ({{ props.subgraph.nodes.length }})</summary>
      <ul>
        <li v-for="node in props.subgraph.nodes" :key="node.id" class="row graph__node">
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
    <details class="graph__relationships">
      <summary>Readable relationships ({{ relationships.length }})</summary>
      <ul>
        <li
          v-for="relationship in relationships"
          :key="relationship.edge.id"
          class="graph__relationship"
          :aria-label="`${relationship.source.caption} ${readableRelationship(relationship.edge)} ${relationship.target.caption} (${relationship.edge.type})`"
        >
          <RouterLink
            v-if="opensEntityPage(relationship.source)"
            :to="{ name: 'entity', params: { id: relationship.source.id } }"
            >{{ relationship.source.caption }}</RouterLink
          >
          <span v-else>{{ relationship.source.caption }}</span>
          <span class="graph__relationship-text"
            >&nbsp;{{ readableRelationship(relationship.edge) }}&nbsp;</span
          >
          <RouterLink
            v-if="opensEntityPage(relationship.target)"
            :to="{ name: 'entity', params: { id: relationship.target.id } }"
            >{{ relationship.target.caption }}</RouterLink
          >
          <span v-else>{{ relationship.target.caption }}</span>
          <span class="graph__relationship-type">&nbsp;({{ relationship.edge.type }})</span>
        </li>
      </ul>
    </details>
  </figure>
</template>
