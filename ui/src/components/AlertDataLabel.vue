<script setup lang="ts">
// Preserve the distinction between synthetic entities and synthetic background activity.
import { computed } from 'vue'

import { alertDataLabel, type AlertDataFlags } from '@/lib/alerts'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps<{ flags: AlertDataFlags }>()

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])
const label = computed(() => alertDataLabel(props.flags))
</script>

<template>
  <span v-if="label.kind === 'synthetic'" class="badge badge--synthetic">
    {{ text.synthetic }}
  </span>
  <span v-else-if="label.kind === 'synthetic_activity'" class="note">
    {{ text.syntheticActivity }}
  </span>
</template>
