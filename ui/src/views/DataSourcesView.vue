<script setup lang="ts">
// Dataset registry from GET /meta, including licences, attribution and loaded counts.
import { computed } from 'vue'

import ExternalLink from '@/components/ExternalLink.vue'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { useMetaStore } from '@/stores/meta'
import { localizedAttribution } from '@/lib/attribution-translations'
const metaStore = useMetaStore()
const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])
const datasets = computed(() => metaStore.meta?.datasets ?? [])
</script>

<template>
  <section>
    <h1>{{ text.dataSources }}</h1>
    <p class="muted">{{ text.sourcesDescription }}</p>

    <ul class="result-list" data-testid="datasets">
      <li v-for="dataset in datasets" :key="dataset.slug" class="card">
        <strong
          ><bdi>{{ dataset.title }}</bdi></strong
        >
        <span v-if="dataset.synthetic" class="badge badge--synthetic">
          {{ text.synthetic }}
        </span>

        <dl class="properties">
          <dt>{{ text.recordsLoaded }}</dt>
          <dd>
            <bdi>{{ dataset.record_count === null ? text.unknown : dataset.record_count }}</bdi>
          </dd>

          <dt>{{ text.licence }}</dt>
          <dd>
            <ExternalLink :href="dataset.licence_url">
              <bdi>{{ dataset.licence_id }}</bdi>
            </ExternalLink>
          </dd>

          <template v-if="dataset.attribution">
            <dt>{{ text.attribution }}</dt>
            <dd>
              <p dir="auto">
                {{ localizedAttribution(dataset.slug, dataset.attribution, localeStore.locale) }}
              </p>

              <details
                v-if="
                  localeStore.isArabic &&
                  localizedAttribution(dataset.slug, dataset.attribution, 'ar') !==
                    dataset.attribution
                "
              >
                <summary>{{ text.originalAttribution }}</summary>
                <p dir="auto">{{ dataset.attribution }}</p>
              </details>
            </dd>
          </template>

          <dt>{{ text.personalData }}</dt>
          <dd>{{ dataset.personal_data ? text.mayIncludePersonalData : text.no }}</dd>

          <dt>{{ text.identifier }}</dt>
          <dd class="mono">
            <bdi>{{ dataset.slug }}</bdi>
          </dd>
        </dl>
      </li>
    </ul>
  </section>
</template>
