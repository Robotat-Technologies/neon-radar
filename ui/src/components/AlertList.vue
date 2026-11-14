<script setup lang="ts">
// Rows of the alert queue; API headlines retain their original wording.
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { localizedAlertHeadline, localizedAlertText } from '@/lib/alert-translations'
import type { AlertSummary } from '@/api/types'
import AlertDataLabel from '@/components/AlertDataLabel.vue'
import { formatStrength, formatTimestamp } from '@/lib/format'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps<{ alerts: readonly AlertSummary[] }>()

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])
</script>

<template>
  <ul class="alert-list" data-testid="alert-list">
    <li v-for="alert in props.alerts" :key="alert.alert_id" class="card">
      <RouterLink
        :to="{ name: 'alert', params: { id: alert.alert_id } }"
        class="alert-list__headline"
      >
        <bdi>{{ localizedAlertHeadline(alert.headline, alert.typology, localeStore.locale) }}</bdi>
      </RouterLink>

      <div class="meta-line">
        <span class="badge" :class="`badge--${alert.priority}`">
          {{ text.priority }}: {{ text.priorityNames[alert.priority] }}
        </span>
        <span>
          {{ text.patternStrength }}:
          <bdi>{{ formatStrength(alert.pattern_strength) }}</bdi>
        </span>
        <bdi>{{
          localizedAlertText(
            alert.typology === 'circular_flow'
              ? 'Round-tripping or circular flows'
              : alert.typology.replace(/_/g, ' '),
            alert.typology,
            localeStore.locale,
          )
        }}</bdi>
        <bdi class="muted">{{ formatTimestamp(alert.created_at) }}</bdi>
        <AlertDataLabel :flags="alert" />
      </div>
    </li>
  </ul>
</template>
