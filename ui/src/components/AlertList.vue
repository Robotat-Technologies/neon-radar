<script setup lang="ts">
// Rows of the alert queue (AlertSummary).
import { RouterLink } from 'vue-router'

import type { AlertSummary } from '@/api/types'
import AlertDataLabel from '@/components/AlertDataLabel.vue'
import { formatStrength, formatTimestamp } from '@/lib/format'

const props = defineProps<{ alerts: readonly AlertSummary[] }>()
</script>

<template>
  <ul class="alert-list" data-testid="alert-list">
    <li v-for="alert in props.alerts" :key="alert.alert_id" class="card">
      <RouterLink
        :to="{ name: 'alert', params: { id: alert.alert_id } }"
        class="alert-list__headline"
      >
        {{ alert.headline }}
      </RouterLink>
      <div class="meta-line">
        <span class="badge" :class="`badge--${alert.priority}`">{{ alert.priority }} priority</span>
        <span>Pattern strength {{ formatStrength(alert.pattern_strength) }}</span>
        <span>{{ alert.typology.replace(/_/g, ' ') }}</span>
        <span class="muted">{{ formatTimestamp(alert.created_at) }}</span>
        <AlertDataLabel :flags="alert" />
      </div>
    </li>
  </ul>
</template>
