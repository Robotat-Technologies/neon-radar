<script setup lang="ts">
// Full-screen network (/entities/:id/network): the graph fills the page and the controls float
// over it (design C2). On a narrow screen the panels stack under the graph instead. The table
// lists every node and relationship, because a canvas says nothing to a screen reader.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { EntityDetail, Subgraph } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import GraphLegend from '@/components/GraphLegend.vue'
import NetworkAlertPanel from '@/components/NetworkAlertPanel.vue'
import { edgeLabel, opensEntityPage, type RelationshipFamily } from '@/lib/graph'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const detail = ref<EntityDetail | null>(null)
const network = ref<Subgraph | null>(null)
const error = ref<unknown>(null)
const hidden = ref<RelationshipFamily[]>([])
const zoom = ref(100)
const showTable = ref(false)
const graph = ref<InstanceType<typeof GraphCanvas> | null>(null)
const edgeSteps = ref<Record<string, number>>({})
const highlighted = ref<string[]>([])

const hops = computed(() => {
  const value = Number(route.query.hops)
  return value === 2 || value === 3 ? value : 1
})

let request = 0
async function load(id: string, depth: number): Promise<void> {
  const current = ++request
  error.value = null
  network.value = null
  try {
    const [entity, subgraph] = await Promise.all([
      detail.value?.entity.id === id ? detail.value : api.getEntity(id),
      api.getNetwork(id, { depth }),
    ])
    if (current !== request) return
    detail.value = entity
    network.value = subgraph
  } catch (caught) {
    if (current === request) error.value = caught
  }
}

watch(
  () => [props.id, hops.value] as const,
  ([id, depth]) => void load(id, depth),
  {
    immediate: true,
  },
)

const entity = computed(() => detail.value?.entity ?? null)
const edgeIds = computed(() => new Set((network.value?.edges ?? []).map((edge) => edge.id)))

function showPath(steps: Record<string, number>, edges: string[]): void {
  edgeSteps.value = steps
  highlighted.value = edges
}

const captions = computed(
  () => new Map((network.value?.nodes ?? []).map((node) => [node.id, node.caption])),
)

function setHops(depth: number): void {
  void router.replace({ query: { ...route.query, hops: String(depth) } })
}

function toggle(family: RelationshipFamily): void {
  hidden.value = hidden.value.includes(family)
    ? hidden.value.filter((item) => item !== family)
    : [...hidden.value, family]
}

function openNode(id: string): void {
  if (id !== props.id) void router.push({ name: 'network', params: { id }, query: route.query })
}
</script>

<template>
  <ErrorMessage v-if="error" :error="error" />
  <p v-else-if="!entity" class="muted">Loading…</p>
  <div v-else class="netview">
    <section class="panel netview__entity" aria-labelledby="netview-heading">
      <p class="muted">{{ entity.schema }} · {{ entity.id }}</p>
      <h1 id="netview-heading">{{ entity.caption }}</h1>
      <EntityBadges :flags="entity.flags" :datasets="entity.datasets" />
      <p v-if="network" class="muted">
        {{ network.nodes.length }} nodes, {{ network.edges.length }} relationships within {{ hops }}
        {{ hops === 1 ? 'hop' : 'hops' }}.
        <strong v-if="network.truncated">The graph was cut at the size limit.</strong>
      </p>
      <RouterLink :to="{ name: 'entity', params: { id: entity.id } }">
        All details and sources
      </RouterLink>
    </section>

    <div class="netview__stage">
      <GraphCanvas
        v-if="network"
        ref="graph"
        bare
        :subgraph="network"
        :focus-ids="[entity.id]"
        :hidden-families="hidden"
        :edge-steps="edgeSteps"
        :highlight-edge-ids="highlighted"
        :label="`Network of ${entity.caption} within ${hops} hops. The table view lists the same nodes and relationships.`"
        @select="openNode"
        @zoom="zoom = $event"
      />
      <p v-else class="muted">Loading the network…</p>

      <div role="toolbar" aria-label="Graph controls" class="panel netview__toolbar">
        <div role="group" aria-label="Hops" class="netview__hops">
          <span aria-hidden="true">Hops</span>
          <button
            v-for="depth in [1, 2, 3]"
            :key="depth"
            type="button"
            :aria-pressed="hops === depth"
            :aria-label="`${depth} ${depth === 1 ? 'hop' : 'hops'}`"
            @click="setHops(depth)"
          >
            {{ depth }}
          </button>
        </div>
        <button type="button" aria-label="Zoom out" @click="graph?.zoomBy(1 / 1.4)">−</button>
        <output class="netview__zoom" aria-label="Zoom">{{ zoom }}%</output>
        <button type="button" aria-label="Zoom in" @click="graph?.zoomBy(1.4)">+</button>
        <button type="button" @click="graph?.fit()">Fit</button>
        <button type="button" :aria-expanded="showTable" @click="showTable = !showTable">
          Table view
        </button>
      </div>
    </div>

    <details open class="panel netview__legend">
      <summary>Show</summary>
      <GraphLegend toggleable :hidden="hidden" @toggle="toggle" />
    </details>

    <NetworkAlertPanel
      v-if="detail?.alerts.length && network"
      :alerts="detail.alerts"
      :edge-ids="edgeIds"
      :hops="hops"
      @path="showPath"
      @hops="setHops"
    />

    <section v-if="showTable && network" class="panel netview__table" aria-label="Table view">
      <h2>Nodes ({{ network.nodes.length }})</h2>
      <ul class="plain-list">
        <li v-for="node in network.nodes" :key="node.id">
          <RouterLink
            v-if="opensEntityPage(node)"
            :to="{ name: 'network', params: { id: node.id }, query: route.query }"
            >{{ node.caption }}</RouterLink
          >
          <span v-else>{{ node.caption }}</span>
          <span class="muted">, {{ node.schema }}</span>
        </li>
      </ul>
      <h2>Relationships ({{ network.edges.length }})</h2>
      <ul class="plain-list">
        <li v-for="edge in network.edges" :key="edge.id">
          {{ captions.get(edge.source) }} → {{ captions.get(edge.target) }}:
          <span class="muted">{{ edgeLabel(edge) }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>
