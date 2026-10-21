<script setup lang="ts">
// The "Synthetic" badge and the source-data flags of one node, in the 7.1 vocabulary.
import { computed } from 'vue'

import type { NodeFlags } from '@/api/types'
import { flagBadges } from '@/lib/flags'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ flags: NodeFlags; datasets: readonly string[] }>()

const metaStore = useMetaStore()
const flags = computed(() =>
  flagBadges(
    props.flags,
    props.datasets.map((slug) => metaStore.datasetTitle(slug)),
  ),
)
</script>

<template>
  <span class="badges">
    <span v-if="props.flags.synthetic" class="badge badge--synthetic">Synthetic</span>
    <span v-for="flag in flags" :key="flag.kind" class="badge badge--flag">{{ flag.text }}</span>
  </span>
</template>
