<script setup lang="ts">
// The alerts that name this entity, over the full-screen network (design C2): one at a time,
// with its explanation steps. The page draws the chosen alert as the alert path; selecting a
// step highlights its relationships. Steps whose relationships lie outside the loaded hops are
// counted, with a way to load 3 hops.
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'

import { api } from '@/api/client'
import type { AlertDetail, AlertSummary } from '@/api/types'
import ErrorMessage from '@/components/ErrorMessage.vue'

const props = defineProps<{
  alerts: readonly AlertSummary[]
  /** The relationships loaded in the graph. */
  edgeIds: ReadonlySet<string>
  hops: number
}>()
const emit = defineEmits<{
  path: [steps: Record<string, number>, highlighted: string[]]
  hops: [depth: number]
}>()

const index = ref(0)
const detail = ref<AlertDetail | null>(null)
const error = ref<unknown>(null)
const selected = ref<number | null>(null)

const current = computed(() => props.alerts[Math.min(index.value, props.alerts.length - 1)])
const steps = computed(() => detail.value?.alert.explanation.steps ?? [])
const outside = computed(
  () => steps.value.filter((step) => step.edge_ids.some((id) => !props.edgeIds.has(id))).length,
)

let request = 0
async function load(id: string | undefined): Promise<void> {
  const mine = ++request
  detail.value = null
  error.value = null
  selected.value = null
  if (!id) return
  try {
    const answer = await api.getAlert(id)
    if (mine === request) detail.value = answer
  } catch (caught) {
    if (mine === request) error.value = caught
  }
}

watch(() => current.value?.alert_id, load, { immediate: true })
watch(
  () => props.alerts,
  () => (index.value = 0),
)

watch(
  [steps, selected],
  () => {
    const path = Object.fromEntries(
      steps.value.flatMap((step) => step.edge_ids.map((id) => [id, step.order] as const)),
    )
    const step = steps.value.find((item) => item.order === selected.value)
    emit('path', path, step ? [...step.edge_ids] : [])
  },
  { immediate: true },
)

function toggle(order: number): void {
  selected.value = selected.value === order ? null : order
}
</script>

<template>
  <section v-if="current" class="panel netview__alerts" aria-labelledby="netview-alerts-heading">
    <div class="netview__alerts-head">
      <h2 id="netview-alerts-heading">Alert {{ index + 1 }} of {{ props.alerts.length }}</h2>
      <span class="badge" :class="`badge--${current.priority}`">
        {{ current.priority }} priority
      </span>
    </div>
    <RouterLink :to="{ name: 'alert', params: { id: current.alert_id } }">
      {{ current.headline }}
    </RouterLink>
    <ErrorMessage v-if="error" :error="error" />
    <p v-else-if="!detail" class="muted">Loading the steps…</p>
    <template v-else>
      <p v-if="outside && props.hops < 3" class="muted">
        {{ outside }} of {{ steps.length }} steps lie outside {{ props.hops }}
        {{ props.hops === 1 ? 'hop' : 'hops' }}.
        <button type="button" @click="emit('hops', 3)">Show 3 hops</button>
      </p>
      <p class="muted">Select a step to highlight it in the graph.</p>
      <ol class="steps netview__steps" data-testid="network-alert-steps">
        <li v-for="step in steps" :key="step.order">
          <button
            type="button"
            class="step"
            :aria-pressed="selected === step.order"
            @click="toggle(step.order)"
          >
            {{ step.text }}
          </button>
        </li>
      </ol>
    </template>
    <div v-if="props.alerts.length > 1" class="netview__alerts-nav">
      <button type="button" :disabled="index === 0" @click="index--">Previous alert</button>
      <button type="button" :disabled="index === props.alerts.length - 1" @click="index++">
        Next alert
      </button>
    </div>
  </section>
</template>
