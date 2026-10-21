<script setup lang="ts">
// Entity (/entities/:id): the node, its network (fcose layout), details, provenance and alerts.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { EntityDetail, Subgraph } from '@/api/types'
import AlertList from '@/components/AlertList.vue'
import EntityBadges from '@/components/EntityBadges.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import { formatValue, humanizeKey } from '@/lib/format'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ id: string }>()
const router = useRouter()
const metaStore = useMetaStore()

const detail = ref<EntityDetail | null>(null)
const error = ref<unknown>(null)
const network = ref<Subgraph | null>(null)
const networkError = ref<unknown>(null)
const depth = ref(1)

// Only the latest request may write its answer, so a slow earlier answer never replaces it.
let detailRequest = 0
let networkRequest = 0

async function loadDetail(id: string): Promise<void> {
  const request = ++detailRequest
  detail.value = null
  error.value = null
  try {
    const answer = await api.getEntity(id)
    if (request === detailRequest) detail.value = answer
  } catch (caught) {
    if (request === detailRequest) error.value = caught
  }
}

async function loadNetwork(id: string, hops: number): Promise<void> {
  const request = ++networkRequest
  networkError.value = null
  try {
    const answer = await api.getNetwork(id, { depth: hops })
    if (request === networkRequest) network.value = answer
  } catch (caught) {
    if (request !== networkRequest) return
    network.value = null
    networkError.value = caught
  }
}

watch(
  () => props.id,
  (id) => {
    depth.value = 1
    network.value = null
    void loadDetail(id)
    void loadNetwork(id, 1)
  },
  { immediate: true },
)
watch(depth, (hops) => void loadNetwork(props.id, hops))

const entity = computed(() => detail.value?.entity ?? null)
const identifiers = computed(() => Object.entries(detail.value?.identifiers ?? {}))
// Identifier values are shown once, under identifiers, not again among the properties.
const properties = computed(() =>
  Object.entries(detail.value?.properties ?? {}).filter(
    ([key]) => !(key in (detail.value?.identifiers ?? {})),
  ),
)
const relationshipCounts = computed(() => Object.entries(detail.value?.relationship_counts ?? {}))

function openNode(id: string): void {
  if (id !== props.id) void router.push({ name: 'entity', params: { id } })
}
</script>

<template>
  <ErrorMessage v-if="error" :error="error" />
  <p v-else-if="!detail || !entity" class="muted">Loading…</p>
  <article v-else class="entity">
    <header class="page-header">
      <p class="muted">{{ entity.schema }} · {{ entity.id }}</p>
      <h1>{{ entity.caption }}</h1>
      <EntityBadges :flags="entity.flags" :datasets="entity.datasets" />
    </header>

    <section aria-labelledby="network-heading">
      <div class="section-header">
        <h2 id="network-heading">Network</h2>
        <label class="inline-field">
          Hops
          <select v-model.number="depth" data-testid="network-depth">
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
          </select>
        </label>
      </div>
      <ErrorMessage v-if="networkError" :error="networkError" />
      <GraphCanvas
        v-else-if="network"
        :subgraph="network"
        :focus-ids="[entity.id]"
        :label="`Network of ${entity.caption} within ${depth} hops`"
        @select="openNode"
      />
      <p v-else class="muted">Loading the network…</p>
    </section>

    <div class="columns">
      <section aria-labelledby="details-heading">
        <h2 id="details-heading">Details</h2>
        <dl class="properties">
          <template v-if="detail.names.length">
            <dt>names</dt>
            <dd>{{ detail.names.join('; ') }}</dd>
          </template>
          <template v-if="entity.countries.length">
            <dt>countries</dt>
            <dd>{{ entity.countries.join(', ').toUpperCase() }}</dd>
          </template>
          <template v-for="[key, values] in identifiers" :key="`id-${key}`">
            <dt>{{ humanizeKey(key) }}</dt>
            <dd>{{ values.join(', ') }}</dd>
          </template>
          <template v-for="[key, value] in properties" :key="`p-${key}`">
            <dt>{{ humanizeKey(key) }}</dt>
            <dd>{{ formatValue(value) }}</dd>
          </template>
        </dl>
      </section>

      <section aria-labelledby="relationships-heading">
        <h2 id="relationships-heading">Relationships</h2>
        <p v-if="relationshipCounts.length === 0" class="muted">None recorded.</p>
        <dl v-else class="properties">
          <template v-for="[type, count] in relationshipCounts" :key="type">
            <dt>{{ type }}</dt>
            <dd>{{ count }}</dd>
          </template>
        </dl>

        <h2>Sources</h2>
        <ul class="plain-list">
          <li v-for="record in detail.provenance" :key="`${record.dataset}-${record.record_id}`">
            {{ metaStore.datasetTitle(record.dataset) }}, record {{ record.record_id }}
            <template v-if="record.source_url">
              (<a :href="record.source_url" rel="noopener noreferrer" target="_blank">source page</a
              >)
            </template>
          </li>
        </ul>
      </section>
    </div>

    <section aria-labelledby="alerts-heading">
      <h2 id="alerts-heading">Alerts that name this entity</h2>
      <p v-if="detail.alerts.length === 0" class="muted">No alert names this entity.</p>
      <template v-else>
        <AlertList :alerts="detail.alerts" />
        <RouterLink :to="{ name: 'alerts', query: { entity_id: entity.id } }">
          All alerts for this entity
        </RouterLink>
      </template>
    </section>
  </article>
</template>
