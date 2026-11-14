<script setup lang="ts">
// Entity (/entities/:id): the node, its network (fcose layout), details, provenance and alerts.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { EntityDetail, Subgraph } from '@/api/types'
import AlertList from '@/components/AlertList.vue'
import EntityBadges from '@/components/EntityBadges.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import ExternalLink from '@/components/ExternalLink.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import { formatValue, safeHref } from '@/lib/format'
import { displayTerm } from '@/lib/terms'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ id: string }>()
const router = useRouter()
const metaStore = useMetaStore()
const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

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
  <p v-else-if="!detail || !entity" class="muted">{{ text.loading }}</p>

  <article v-else class="entity">
    <header class="page-header">
      <p class="muted">
        <bdi>{{ displayTerm(entity.schema, localeStore.locale) }}</bdi> · <bdi>{{ entity.id }}</bdi>
      </p>
      <h1>
        <bdi>{{ entity.caption }}</bdi>
      </h1>
      <EntityBadges :flags="entity.flags" :datasets="entity.datasets" />
    </header>

    <section aria-labelledby="network-heading">
      <div class="section-header">
        <h2 id="network-heading">{{ text.network }}</h2>

        <label class="inline-field">
          {{ text.hops }}
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
        :label="text.networkDescription(entity.caption, depth)"
        @select="openNode"
      />

      <p v-else class="muted">{{ text.loadingNetwork }}</p>
    </section>

    <div class="columns">
      <section aria-labelledby="details-heading">
        <h2 id="details-heading">{{ text.details }}</h2>

        <dl class="properties">
          <template v-if="detail.names.length">
            <dt>{{ text.names }}</dt>
            <dd>
              <bdi>{{ detail.names.join('; ') }}</bdi>
            </dd>
          </template>

          <template v-if="entity.countries.length">
            <dt>{{ text.countries }}</dt>
            <dd>
              <bdi>{{ entity.countries.join(', ').toUpperCase() }}</bdi>
            </dd>
          </template>

          <template v-for="[key, values] in identifiers" :key="`id-${key}`">
            <dt>
              <bdi>{{ displayTerm(key, localeStore.locale) }}</bdi>
            </dt>
            <dd>
              <bdi>{{ values.join(', ') }}</bdi>
            </dd>
          </template>

          <template v-for="[key, value] in properties" :key="`p-${key}`">
            <dt>
              <bdi>{{ displayTerm(key, localeStore.locale) }}</bdi>
            </dt>
            <dd>
              <bdi>{{ formatValue(value) }}</bdi>
            </dd>
          </template>
        </dl>
      </section>

      <section aria-labelledby="relationships-heading">
        <h2 id="relationships-heading">{{ text.relationships }}</h2>

        <p v-if="relationshipCounts.length === 0" class="muted">
          {{ text.noneRecorded }}
        </p>

        <dl v-else class="properties">
          <template v-for="[type, count] in relationshipCounts" :key="type">
            <dt>
              <bdi>{{ displayTerm(type, localeStore.locale) }}</bdi>
            </dt>
            <dd>
              <bdi>{{ count }}</bdi>
            </dd>
          </template>
        </dl>

        <h2>{{ text.sources }}</h2>

        <ul class="plain-list">
          <li v-for="record in detail.provenance" :key="`${record.dataset}-${record.record_id}`">
            <bdi>{{ metaStore.datasetTitle(record.dataset) }}</bdi
            >, {{ text.record }} <bdi>{{ record.record_id }}</bdi>

            <template v-if="safeHref(record.source_url)">
              (<ExternalLink :href="record.source_url">{{ text.sourcePage }}</ExternalLink
              >)
            </template>

            <template v-else-if="record.source_url">
              ({{ text.source }}: <bdi>{{ record.source_url }}</bdi
              >)
            </template>
          </li>
        </ul>
      </section>
    </div>

    <section aria-labelledby="alerts-heading">
      <h2 id="alerts-heading">{{ text.entityAlerts }}</h2>

      <p v-if="detail.alerts.length === 0" class="muted">
        {{ text.noEntityAlerts }}
      </p>

      <template v-else>
        <AlertList :alerts="detail.alerts" />
        <RouterLink :to="{ name: 'alerts', query: { entity_id: entity.id } }">
          {{ text.allEntityAlerts }}
        </RouterLink>
      </template>
    </section>
  </article>
</template>
