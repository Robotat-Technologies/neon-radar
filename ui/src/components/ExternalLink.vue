<script setup lang="ts">
// A link to a source outside NeonRadar, opened only when the user selects it. Only http and
// https addresses become links; anything else (javascript:, data:, relative paths) stays text.
import { computed } from 'vue'

import { safeHref } from '@/lib/format'

const props = defineProps<{ href: string | null | undefined }>()
const target = computed(() => safeHref(props.href))
</script>

<template>
  <a v-if="target" :href="target" rel="noopener noreferrer" target="_blank"><slot /></a>
  <span v-else><slot /></span>
</template>
