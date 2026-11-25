<script setup lang="ts">
// Data sources (/sources): the dataset registry from GET /meta with licences, attribution and
// what is loaded. The real data notice points here ("listed with their licences on the Data
// sources page").
import { computed } from 'vue'

import ExternalLink from '@/components/ExternalLink.vue'
import UiIcon from '@/components/UiIcon.vue'
import { formatTimestamp } from '@/lib/format'
import { useMetaStore } from '@/stores/meta'

const metaStore = useMetaStore()
const datasets = computed(() => metaStore.meta?.datasets ?? [])
</script>

<template>
  <section aria-labelledby="data-sources-heading">
    <header class="page-header">
      <p class="eyebrow">PROVENANCE & TRANSPARENCY</p>
      <h1 id="data-sources-heading">Data sources</h1>
      <p class="muted">
        Every dataset NeonRadar knows about, whether or not anything from it is loaded. Records are
        shown as each source published them.
      </p>
    </header>

    <template v-if="metaStore.meta">
      <p v-if="metaStore.loading" class="muted" role="status">Refreshing source information…</p>
      <p v-if="datasets.length === 0" class="muted">No data sources are registered.</p>
      <ul v-else class="result-list source-grid" data-testid="datasets">
        <li v-for="dataset in datasets" :key="dataset.slug" class="card">
          <div class="source-heading">
            <span class="entity-symbol"><UiIcon name="sources" /></span>
            <div>
              <h2>{{ dataset.title }}</h2>
              <span v-if="dataset.synthetic" class="badge badge--synthetic">Synthetic</span>
            </div>
          </div>
          <dl class="properties">
            <dt>records loaded</dt>
            <dd>{{ dataset.record_count === null ? 'not available' : dataset.record_count }}</dd>
            <dt>last loaded</dt>
            <dd>{{ dataset.loaded_at ? formatTimestamp(dataset.loaded_at) : 'Not available' }}</dd>
            <dt>licence</dt>
            <dd>
              <ExternalLink :href="dataset.licence_url">{{ dataset.licence_id }}</ExternalLink>
            </dd>
            <template v-if="dataset.attribution">
              <dt>attribution</dt>
              <dd>{{ dataset.attribution }}</dd>
            </template>
            <dt>personal data</dt>
            <dd>{{ dataset.personal_data ? 'may include personal data' : 'no' }}</dd>
            <dt>identifier</dt>
            <dd class="mono">{{ dataset.slug }}</dd>
          </dl>
        </li>
      </ul>
    </template>
    <template v-else-if="metaStore.error">
      <p class="error" role="alert">
        Source information could not be loaded. {{ metaStore.error }}
      </p>
      <button type="button" :disabled="metaStore.loading" @click="metaStore.load()">
        Try again
      </button>
    </template>
    <template v-else>
      <p v-if="metaStore.loading" class="muted">Loading data sources…</p>
      <template v-else>
        <p class="error" role="alert">Source information is not available.</p>
        <button type="button" @click="metaStore.load()">Try again</button>
      </template>
    </template>
  </section>
</template>
