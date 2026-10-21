<script setup lang="ts">
// Data sources (/sources): the dataset registry from GET /meta with licences, attribution and
// what is loaded. The real data notice points here ("listed with their licences on the Data
// sources page").
import { computed } from 'vue'

import { useMetaStore } from '@/stores/meta'

const metaStore = useMetaStore()
const datasets = computed(() => metaStore.meta?.datasets ?? [])
</script>

<template>
  <section>
    <h1>Data sources</h1>
    <p class="muted">
      Every dataset NeonRadar knows about, whether or not anything from it is loaded. Records are
      shown as each source published them.
    </p>
    <ul class="result-list" data-testid="datasets">
      <li v-for="dataset in datasets" :key="dataset.slug" class="card">
        <strong>{{ dataset.title }}</strong>
        <span v-if="dataset.synthetic" class="badge badge--synthetic">Synthetic</span>
        <dl class="properties">
          <dt>records loaded</dt>
          <dd>{{ dataset.record_count === null ? 'unknown' : dataset.record_count }}</dd>
          <dt>licence</dt>
          <dd>
            <a :href="dataset.licence_url" rel="noopener noreferrer" target="_blank">{{
              dataset.licence_id
            }}</a>
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
  </section>
</template>
