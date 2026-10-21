<script setup lang="ts">
// "Synthetic" for an alert among synthetic entities only; next to a real entity, an alert whose
// evidence is all generated says the pattern lies in synthetic background activity.
import { computed } from 'vue'

import { alertDataLabel, type AlertDataFlags } from '@/lib/alerts'

const props = defineProps<{ flags: AlertDataFlags }>()
const label = computed(() => alertDataLabel(props.flags))
</script>

<template>
  <span v-if="label.kind === 'synthetic'" class="badge badge--synthetic">Synthetic</span>
  <span v-else-if="label.kind === 'synthetic_activity'" class="note">{{ label.text }}</span>
</template>
