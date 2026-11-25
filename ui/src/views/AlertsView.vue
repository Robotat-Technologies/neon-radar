<script setup lang="ts">
// Alerts (/alerts): the alert queue in the API's order (priority, then pattern strength),
// filtered by priority, typology or entity, a page at a time.
import { computed, ref, watch } from 'vue'
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
const typologyError = ref<unknown>(null)
const typologyLoading = ref(false)

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

const hasFilters = computed(() => Boolean(priority.value || typology.value || entityId.value))

async function loadTypologies(): Promise<void> {
  typologyLoading.value = true
  typologyError.value = null
  try {
    const list = await api.listTypologies()
    typologies.value = list.filter((item) => item.detector_available)
  } catch (caught) {
    typologies.value = []
    typologyError.value = caught
  } finally {
    typologyLoading.value = false
  }
}

void loadTypologies()

function applyFilters(): void {
  void router.push({
    name: 'alerts',
    query: {
      priority: priority.value || undefined,
      typology: typology.value || undefined,
      entity_id: entityId.value.trim() || undefined,
    },
  })
}

function resetFilters(): void {
  priority.value = ''
  typology.value = ''
  entityId.value = ''
  void router.push({ name: 'alerts' })
}

function retryAlerts(): void {
  void loadPage(null)
}
</script>

<template>
  <section>
    <header class="page-header">
      <p class="eyebrow">PATTERN REVIEW</p>
      <h1>Alerts</h1>
      <p class="muted">Explore structural patterns. Follow the evidence, not a score.</p>
    </header>
    <p class="muted">
      Each alert is a structural pattern that matches a typology's graph pattern. Alerts are ordered
      by priority, then pattern strength. Pattern strength is a heuristic: it says how closely the
      evidence matches the pattern, nothing more.
    </p>
    <form class="filters alerts-filters" @submit.prevent="applyFilters">
      <label class="inline-field alerts-filters__field">
        Priority
        <select v-model="priority">
          <option value="">any</option>
          <option v-for="value in PRIORITIES" :key="value" :value="value">{{ value }}</option>
        </select>
      </label>
      <label class="inline-field alerts-filters__field">
        Typology
        <select v-model="typology" :disabled="typologyLoading">
          <option value="">any</option>
          <option
            v-if="typology && !typologies.some((item) => item.slug === typology)"
            :value="typology"
          >
            {{ typology }}
          </option>
          <option v-for="item in typologies" :key="item.slug" :value="item.slug">
            {{ item.name }}
          </option>
        </select>
      </label>
      <button class="button-primary" type="submit">Apply filters</button>
      <button v-if="hasFilters" type="button" class="alerts-filters__reset" @click="resetFilters">
        Reset filters
      </button>
      <span v-if="entityId" class="muted alerts-filters__entity">
        Only alerts that name {{ entityId }} (<RouterLink :to="{ name: 'alerts' }"
          >show all</RouterLink
        >)
      </span>
    </form>

    <div v-if="typologyError" class="alerts-typologies__error" role="status">
      <p class="error">The typology filter could not be loaded.</p>
      <button type="button" @click="loadTypologies">Try again</button>
    </div>

    <div v-if="error" class="alerts__error">
      <ErrorMessage :error="error" />
      <button type="button" @click="retryAlerts">Try again</button>
    </div>
    <p v-else-if="!loading && items.length === 0" class="muted alerts__empty">
      No alerts match<template v-if="hasFilters"> these filters</template>.
      <button v-if="hasFilters" type="button" class="alerts__reset" @click="resetFilters">
        Reset filters
      </button>
    </p>
    <AlertList v-if="items.length" :alerts="items" />
    <p v-if="loading" class="muted alerts__loading">Loading alerts…</p>
    <button v-else-if="nextCursor" type="button" class="alerts__more" @click="loadPage(nextCursor)">
      More alerts
    </button>
  </section>
</template>
