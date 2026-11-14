<script setup lang="ts">
// Flags describe source records and retain their source attribution.
import { computed } from 'vue'

import type { NodeFlags } from '@/api/types'
import { flagBadges } from '@/lib/flags'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ flags: NodeFlags; datasets: readonly string[] }>()

const metaStore = useMetaStore()
const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

const flags = computed(() =>
  flagBadges(
    props.flags,
    props.datasets.map((slug) => metaStore.datasetTitle(slug)),
    localeStore.locale,
  ),
)
</script>

<template>
  <span class="badges">
    <span v-if="props.flags.synthetic" class="badge badge--synthetic">
      {{ text.synthetic }}
    </span>
    <span v-for="flag in flags" :key="flag.kind" class="badge badge--flag" dir="auto">
      {{ flag.text }}
    </span>
  </span>
</template>
