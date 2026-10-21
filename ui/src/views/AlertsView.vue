<script setup lang="ts">
// Alerts (/alerts): the alert queue in the API's order (priority, then pattern strength),
// filtered by priority, typology or entity, a page at a time.
import { ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { AlertListParams, AlertPriority, AlertSummary, TypologySummary } from '@/api/types'
import AlertList from '@/components/AlertList.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import { PRIORITIES } from '@/lib/alerts'

const route = useRoute()
const router = useRouter()

const items = ref<AlertSummary[]>([])
const nextCursor = ref<string | null>(null)
const error = ref<unknown>(null)
const loading = ref(false)
const typologies = ref<TypologySummary[]>([])

const priority = ref<AlertPriority | ''>('')
const typology = ref('')
const entityId = ref('')
let filters: AlertListParams = {}
let request = 0

function text(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

async function loadPage(cursor: string | null): Promise<void> {
  const current = ++request
  loading.value = true
  error.value = null
  try {
    const page = await api.listAlerts({ ...filters, cursor })
    if (current !== request) return
    items.value = cursor ? [...items.value, ...page.items] : page.items
    nextCursor.value = page.next_cursor
  } catch (caught) {
    if (current === request) error.value = caught
  } finally {
    if (current === request) loading.value = false
  }
}

watch(
  () => route.query,
  (query) => {
    const wanted = text(query.priority)
    priority.value = (PRIORITIES as readonly string[]).includes(wanted)
      ? (wanted as AlertPriority)
      : ''
    typology.value = text(query.typology)
    entityId.value = text(query.entity_id)
    filters = {
      priority: priority.value || null,
      typology: typology.value || null,
      entity_id: entityId.value || null,
    }
    items.value = []
    nextCursor.value = null
    void loadPage(null)
  },
  { immediate: true },
)

api
  .listTypologies()
  .then((list) => (typologies.value = list.filter((item) => item.detector_available)))
  .catch(() => (typologies.value = []))

function applyFilters(): void {
  void router.push({
    name: 'alerts',
    query: {
      priority: priority.value || undefined,
      typology: typology.value || undefined,
      entity_id: entityId.value || undefined,
    },
  })
}
</script>

<template>
  <section>
    <h1>Alerts</h1>
    <p class="muted">
      Each alert is a structural pattern that matches a typology's graph pattern. Alerts are ordered
      by priority, then pattern strength. Pattern strength is a heuristic: it says how closely the
      evidence matches the pattern, nothing more.
    </p>
    <form class="filters" @submit.prevent="applyFilters">
      <label class="inline-field">
        Priority
        <select v-model="priority">
          <option value="">any</option>
          <option v-for="value in PRIORITIES" :key="value" :value="value">{{ value }}</option>
        </select>
      </label>
      <label class="inline-field">
        Typology
        <select v-model="typology">
          <option value="">any</option>
          <option v-for="item in typologies" :key="item.slug" :value="item.slug">
            {{ item.name }}
          </option>
        </select>
      </label>
      <button type="submit">Apply</button>
      <span v-if="entityId" class="muted">
        Only alerts that name {{ entityId }} (<RouterLink :to="{ name: 'alerts' }"
          >show all</RouterLink
        >)
      </span>
    </form>

    <ErrorMessage v-if="error" :error="error" />
    <p v-else-if="!loading && items.length === 0" class="muted">No alerts match.</p>
    <AlertList v-if="items.length" :alerts="items" />
    <p v-if="loading" class="muted">Loading…</p>
    <button v-else-if="nextCursor" type="button" @click="loadPage(nextCursor)">More alerts</button>
  </section>
</template>
