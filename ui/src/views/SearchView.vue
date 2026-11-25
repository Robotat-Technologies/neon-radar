<script setup lang="ts">
// Search (/): full-text search over names and addresses, plus exact account numbers (C3).
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { SearchLabel, SearchResponse } from '@/api/types'
import EntityBadges from '@/components/EntityBadges.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import UiIcon from '@/components/UiIcon.vue'
import { searchCountText } from '@/lib/search'
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
const filtersOpen = ref(false)
const showStickySearch = ref(false)
const searchPanel = ref<HTMLElement | null>(null)
const filterToggle = ref<HTMLButtonElement | null>(null)
let observer: IntersectionObserver | null = null
let request = 0

const trimmed = computed(() => query.value.trim())
const tooShort = computed(() => trimmed.value.length > 0 && trimmed.value.length < MIN_LENGTH)
const filterSummary = computed(() =>
  labels.value.length === 0 ? 'All entity types' : labels.value.join(', '),
)

function toggleFilters(): void {
  filtersOpen.value = !filtersOpen.value
}

async function editFiltersFromUtility(): Promise<void> {
  filtersOpen.value = true
  await nextTick()
  searchPanel.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  filterToggle.value?.focus()
}

function asList(value: unknown): string[] {
  if (Array.isArray(value)) return value.filter((item): item is string => typeof item === 'string')
  return typeof value === 'string' ? [value] : []
}

async function run(q: string, selected: SearchLabel[]): Promise<void> {
  const current = ++request
  loading.value = true
  error.value = null
  try {
    const answer = await api.search({ q, labels: selected.length ? selected : null })
    if (current !== request) return
    result.value = answer
  } catch (caught) {
    if (current !== request) return
    error.value = caught
    result.value = null
  } finally {
    if (current === request) loading.value = false
  }
}

function clearSearch(): void {
  request += 1
  result.value = null
  error.value = null
  loading.value = false
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
    else clearSearch()
  },
  { immediate: true },
)

function onQueryInput(event: Event): void {
  if ((event.target as HTMLInputElement).value.trim() === '') clearSearch()
}

onMounted(() => {
  if (!searchPanel.value || !('IntersectionObserver' in window)) return
  observer = new IntersectionObserver(
    ([entry]) => {
      showStickySearch.value = entry ? !entry.isIntersecting : false
    },
    { threshold: 0, rootMargin: '-72px 0px 0px' },
  )
  observer.observe(searchPanel.value)
})
onBeforeUnmount(() => observer?.disconnect())

function submit(): void {
  if (trimmed.value.length < MIN_LENGTH) return
  const selected = asList(route.query.labels)
  if (
    route.query.q === trimmed.value &&
    selected.length === labels.value.length &&
    selected.every((label, index) => label === labels.value[index])
  ) {
    void run(trimmed.value, labels.value)
    return
  }
  void router.push({
    name: 'search',
    query: { q: trimmed.value, labels: labels.value.length ? labels.value : undefined },
  })
}
</script>

<template>
  <section class="search-view" aria-labelledby="search-heading">
    <header class="search-view__header">
      <p class="eyebrow">EXPLORE THE GRAPH</p>
      <h1 id="search-heading">Search</h1>
      <p class="muted">
        Start with a name. Follow the connections. Find entities by name, address or exact account
        number.
      </p>
    </header>

    <form ref="searchPanel" class="search-form" role="search" @submit.prevent="submit">
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
          @input="onQueryInput"
        />
      </label>
      <button class="button-primary" type="submit" :disabled="trimmed.length < MIN_LENGTH">
        <UiIcon name="search" />Search
      </button>
      <div class="filter-disclosure">
        <button
          ref="filterToggle"
          type="button"
          class="filter-toggle"
          :aria-expanded="filtersOpen"
          aria-controls="entity-type-filters"
          @click="toggleFilters"
        >
          <span>Filters</span><strong>{{ filterSummary }}</strong
          ><span aria-hidden="true">{{ filtersOpen ? '−' : '+' }}</span>
        </button>
        <fieldset v-if="filtersOpen" id="entity-type-filters" class="label-filter">
          <legend>Entity type</legend>
          <label v-for="label in LABELS" :key="label" class="checkbox">
            <input v-model="labels" type="checkbox" :value="label" />
            {{ label }}
          </label>
        </fieldset>
      </div>
      <p v-if="tooShort" class="muted" role="status">Type at least {{ MIN_LENGTH }} characters.</p>
    </form>

    <form v-if="showStickySearch" class="search-utility-bar" role="search" @submit.prevent="submit">
      <label>
        <span class="visually-hidden">Search names, addresses or account numbers</span>
        <input
          v-model="query"
          type="search"
          name="sticky-q"
          :minlength="MIN_LENGTH"
          :maxlength="MAX_LENGTH"
          autocomplete="off"
          placeholder="Search names, addresses or account numbers"
          @input="onQueryInput"
        />
      </label>
      <button type="button" class="utility-filter" @click="editFiltersFromUtility">
        Edit filters <span>{{ labels.length }}</span>
      </button>
      <button class="button-primary" type="submit" :disabled="trimmed.length < MIN_LENGTH">
        <UiIcon name="search" />Search
      </button>
    </form>

    <section
      class="search-results"
      aria-labelledby="search-results-heading"
      aria-live="polite"
      :aria-busy="loading"
    >
      <h2 id="search-results-heading">Results</h2>
      <p v-if="loading" class="muted" role="status" data-testid="search-loading">Searching…</p>
      <ErrorMessage v-else-if="error" :error="error" />
      <template v-else-if="result">
        <p class="muted" data-testid="search-count">
          {{ searchCountText(result) }}
        </p>
        <p v-if="result.items.length === 0" class="muted" data-testid="search-empty">
          Try a different spelling or change the filters.
        </p>
        <ul v-else class="result-list" data-testid="search-results">
          <li v-for="hit in result.items" :key="hit.entity.id" class="card">
            <div class="result-heading">
              <span class="entity-symbol"><UiIcon name="network" /></span>
              <RouterLink :to="{ name: 'entity', params: { id: hit.entity.id } }">
                {{ hit.entity.caption }}
              </RouterLink>
              <UiIcon class="result-arrow" name="arrow" />
            </div>
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
      <template v-else>
        <div class="state-panel">
          <UiIcon name="search" />
          <h3>Your investigation starts here</h3>
          <p class="muted" data-testid="search-prompt">
            Enter a name, address or account number to begin.
          </p>
          <p class="muted">Source records and relationships, in one connected workspace.</p>
        </div>
        <div class="search-entry-points">
          <RouterLink to="/alerts" class="entry-card"
            ><UiIcon name="alerts" /><span
              ><strong>Review pattern alerts</strong
              ><small>Inspect explanations and supporting evidence</small></span
            ><UiIcon name="arrow"
          /></RouterLink>
          <RouterLink to="/sources" class="entry-card"
            ><UiIcon name="sources" /><span
              ><strong>Know your data</strong
              ><small>Explore sources, licences and load dates</small></span
            ><UiIcon name="arrow"
          /></RouterLink>
        </div>
      </template>
    </section>
  </section>
</template>
