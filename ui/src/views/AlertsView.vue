<script setup lang="ts">
// Alerts (/alerts): the alert queue in the API's order (priority, then pattern strength),
// filtered by priority, typology or entity, a page at a time.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { api } from '@/api/client'
import type { AlertListParams, AlertPriority, AlertSummary, TypologySummary } from '@/api/types'
import AlertList from '@/components/AlertList.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import { PRIORITIES } from '@/lib/alerts'

const route = useRoute()
const router = useRouter()
const localeStore = useLocaleStore()
const uiText = computed(() => messages[localeStore.locale])

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
    <h1>{{ uiText.alerts }}</h1>
    <p class="muted">{{ uiText.alertsExplanation }}</p>

    <form class="filters" @submit.prevent="applyFilters">
      <label class="inline-field">
        {{ uiText.priority }}
        <select v-model="priority">
          <option value="">{{ uiText.any }}</option>
          <option v-for="value in PRIORITIES" :key="value" :value="value">
            {{ uiText.priorityNames[value] }}
          </option>
        </select>
      </label>

      <label class="inline-field">
        {{ uiText.typology }}
        <select v-model="typology">
          <option value="">{{ uiText.any }}</option>
          <option v-for="item in typologies" :key="item.slug" :value="item.slug" dir="auto">
            {{ item.name }}
          </option>
        </select>
      </label>

      <button type="submit">{{ uiText.apply }}</button>

      <span v-if="entityId" class="muted">
        {{ uiText.alertsForEntity }}
        <bdi>{{ entityId }}</bdi>
        (<RouterLink :to="{ name: 'alerts' }">{{ uiText.showAll }}</RouterLink
        >)
      </span>
    </form>

    <ErrorMessage v-if="error" :error="error" />
    <p v-else-if="!loading && items.length === 0" class="muted">
      {{ uiText.noAlerts }}
    </p>

    <AlertList v-if="items.length" :alerts="items" />

    <p v-if="loading" class="muted">{{ uiText.loading }}</p>
    <button v-else-if="nextCursor" type="button" @click="loadPage(nextCursor)">
      {{ uiText.moreAlerts }}
    </button>
  </section>
</template>
