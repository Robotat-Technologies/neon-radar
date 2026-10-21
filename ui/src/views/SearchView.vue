<script setup lang="ts">
// Search (/): full-text search over names and addresses, plus exact account numbers (C3).
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { SearchLabel, SearchResponse } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import { useMetaStore } from '@/stores/meta'

const LABELS: readonly SearchLabel[] = [
  'Person',
  'Company',
  'Organization',
  'LegalEntity',
  'Address',
  'Account',
]
const MIN_LENGTH = 2
const MAX_LENGTH = 200

const route = useRoute()
const router = useRouter()
const metaStore = useMetaStore()

const query = ref('')
const labels = ref<SearchLabel[]>([])
const result = ref<SearchResponse | null>(null)
const error = ref<unknown>(null)
const loading = ref(false)

const trimmed = computed(() => query.value.trim())
const tooShort = computed(() => trimmed.value.length > 0 && trimmed.value.length < MIN_LENGTH)

function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string')
  return typeof value === 'string' ? [value] : []
}

async function run(q: string, selected: SearchLabel[]): Promise<void> {
  loading.value = true
  error.value = null
  try {
    result.value = await api.search({ q, labels: selected.length ? selected : null })
  } catch (caught) {
    error.value = caught
    result.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => route.query,
  (routeQuery) => {
    const q = typeof routeQuery.q === 'string' ? routeQuery.q : ''
    const selected = asList(routeQuery.labels).filter((label): label is SearchLabel =>
      (LABELS as readonly string[]).includes(label),
    )
    query.value = q
    labels.value = selected
    if (q.trim().length >= MIN_LENGTH) void run(q.trim(), selected)
    else result.value = null
  },
  { immediate: true },
)

function countText(answer: SearchResponse): string {
  const total = answer.total_estimate
  if (answer.items.length === 0) return `No matches for “${answer.query}”.`
  const noun = total === 1 ? 'match' : 'matches'
  const about = total > answer.items.length ? 'About ' : ''
  return `${about}${total} ${noun} for “${answer.query}”.`
}

function submit(): void {
  if (trimmed.value.length < MIN_LENGTH) return
  void router.push({
    name: 'search',
    query: { q: trimmed.value, labels: labels.value.length ? labels.value : undefined },
  })
}
</script>

<template>
  <section>
    <h1>Search</h1>
    <form class="search-form" role="search" @submit.prevent="submit">
      <label class="field">
        <span>Name, address or account number</span>
        <input
          v-model="query"
          type="search"
          name="q"
          :minlength="MIN_LENGTH"
          :maxlength="MAX_LENGTH"
          autocomplete="off"
          data-testid="search-input"
        />
      </label>
      <fieldset class="label-filter">
        <legend>Only these kinds (none ticked: all)</legend>
        <label v-for="label in LABELS" :key="label" class="checkbox">
          <input v-model="labels" type="checkbox" :value="label" />
          {{ label }}
        </label>
      </fieldset>
      <button type="submit" :disabled="trimmed.length < MIN_LENGTH">Search</button>
      <p v-if="tooShort" class="muted">Type at least {{ MIN_LENGTH }} characters.</p>
    </form>

    <p v-if="loading" class="muted">Searching…</p>
    <ErrorMessage v-else-if="error" :error="error" />
    <template v-else-if="result">
      <p class="muted" data-testid="search-count">
        {{ countText(result) }}
      </p>
      <ul class="result-list" data-testid="search-results">
        <li v-for="hit in result.items" :key="hit.entity.id" class="card">
          <RouterLink :to="{ name: 'entity', params: { id: hit.entity.id } }">
            {{ hit.entity.caption }}
          </RouterLink>
          <div class="meta-line">
            <span>{{ hit.entity.schema }}</span>
            <span v-if="hit.matched_name !== hit.entity.caption" class="muted">
              matched “{{ hit.matched_name }}”
            </span>
            <span v-if="hit.entity.countries.length">{{
              hit.entity.countries.join(', ').toUpperCase()
            }}</span>
            <span class="muted">{{
              hit.entity.datasets.map((slug) => metaStore.datasetTitle(slug)).join(', ')
            }}</span>
            <EntityBadges :flags="hit.entity.flags" :datasets="hit.entity.datasets" />
          </div>
        </li>
      </ul>
    </template>
  </section>
</template>
