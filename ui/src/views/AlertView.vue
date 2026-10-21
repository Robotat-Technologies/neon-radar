<script setup lang="ts">
// Alert (/alerts/:id): the evidence subgraph, the explanation steps, the typology reference
// with its citations, and the metrics (contract C4).
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { AlertDetail, Citation, TypologyDetail } from '@/api/types'
import AlertDataLabel from '@/components/AlertDataLabel.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import { formatMetric, formatStrength, formatTimestamp, humanizeKey } from '@/lib/format'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ id: string }>()
const router = useRouter()
const metaStore = useMetaStore()

const detail = ref<AlertDetail | null>(null)
const error = ref<unknown>(null)
const typology = ref<TypologyDetail | null>(null)
const selectedStep = ref<number | null>(null)
let request = 0

async function load(id: string): Promise<void> {
  const current = ++request
  detail.value = null
  error.value = null
  typology.value = null
  selectedStep.value = null
  try {
    const answer = await api.getAlert(id)
    if (current !== request) return
    detail.value = answer
    try {
      const reference = await api.getTypology(answer.alert.typology)
      if (current === request) typology.value = reference
    } catch {
      // The alert still shows its typology slug and citation keys without the catalog entry.
    }
  } catch (caught) {
    if (current === request) error.value = caught
  }
}

watch(() => props.id, load, { immediate: true })

const alert = computed(() => detail.value?.alert ?? null)
const subjectIds = computed(() => alert.value?.subjects.map((subject) => subject.entity_id) ?? [])
const highlightedEdges = computed(() => {
  const step = alert.value?.explanation.steps.find((item) => item.order === selectedStep.value)
  return step ? step.edge_ids : []
})
const metrics = computed(() => Object.entries(alert.value?.metrics ?? {}))
const evidenceWindow = computed(() => alert.value?.evidence.window ?? null)

/** The alert's citation keys, with the bibliography entry when the catalog has it. */
const citations = computed(() => {
  const known = new Map<string, Citation>(
    (typology.value?.citations ?? []).map((citation) => [citation.key, citation]),
  )
  return (alert.value?.explanation.typology_reference.citations ?? []).map((key) => ({
    key,
    citation: known.get(key) ?? null,
  }))
})

function toggleStep(order: number): void {
  selectedStep.value = selectedStep.value === order ? null : order
}

function openNode(id: string): void {
  void router.push({ name: 'entity', params: { id } })
}
</script>

<template>
  <ErrorMessage v-if="error" :error="error" />
  <p v-else-if="!detail || !alert" class="muted">Loading…</p>
  <article v-else class="alert">
    <header class="page-header">
      <p class="muted">{{ alert.alert_id }}</p>
      <h1 data-testid="alert-headline">{{ alert.headline }}</h1>
      <div class="meta-line">
        <span class="badge" :class="`badge--${alert.priority}`">{{ alert.priority }} priority</span>
        <span>Pattern strength {{ formatStrength(alert.pattern_strength) }}</span>
        <span class="muted">Created {{ formatTimestamp(alert.created_at) }}</span>
        <AlertDataLabel :flags="alert.data_flags" />
      </div>
      <p>
        Matches the graph pattern of
        <strong>{{ typology?.name ?? alert.typology.replace(/_/g, ' ') }}</strong
        >. {{ alert.explanation.summary }}
      </p>
    </header>

    <section aria-labelledby="evidence-heading">
      <h2 id="evidence-heading">Evidence</h2>
      <GraphCanvas
        :subgraph="detail.evidence"
        :focus-ids="subjectIds"
        :highlight-edge-ids="highlightedEdges"
        label="Evidence subgraph of this alert"
        @select="openNode"
      />
    </section>

    <div class="columns">
      <section aria-labelledby="steps-heading">
        <h2 id="steps-heading">Explanation</h2>
        <p class="muted">Select a step to highlight its relationships in the graph.</p>
        <ol class="steps" data-testid="explanation-steps">
          <li v-for="step in alert.explanation.steps" :key="step.order">
            <button
              type="button"
              class="step"
              :aria-pressed="selectedStep === step.order"
              @click="toggleStep(step.order)"
            >
              {{ step.text }}
            </button>
          </li>
        </ol>

        <h2>Subjects</h2>
        <ul class="plain-list">
          <li v-for="subject in alert.subjects" :key="subject.entity_id" class="row">
            <RouterLink :to="{ name: 'entity', params: { id: subject.entity_id } }">
              {{ subject.caption }}
            </RouterLink>
            <span class="muted">{{ humanizeKey(subject.role) }}</span>
          </li>
        </ul>

        <h2>Other explanations for this structure</h2>
        <ul class="plain-list">
          <li v-for="note in alert.explanation.false_positive_notes" :key="note">{{ note }}</li>
        </ul>
      </section>

      <section aria-labelledby="metrics-heading">
        <h2 id="metrics-heading">Metrics</h2>
        <dl class="properties">
          <dt>pattern strength</dt>
          <dd>{{ formatStrength(alert.pattern_strength) }}</dd>
          <template v-for="[key, value] in metrics" :key="key">
            <dt>{{ humanizeKey(key) }}</dt>
            <dd>{{ formatMetric(value) }}</dd>
          </template>
          <template v-if="evidenceWindow">
            <dt>window</dt>
            <dd>
              {{ formatTimestamp(evidenceWindow.start) }} to
              {{ formatTimestamp(evidenceWindow.end) }}
            </dd>
          </template>
          <dt>datasets</dt>
          <dd>
            {{ alert.data_flags.datasets.map((slug) => metaStore.datasetTitle(slug)).join(', ') }}
          </dd>
        </dl>

        <h2>Typology</h2>
        <p>
          <strong>{{ typology?.name ?? alert.typology }}</strong>
          <span class="muted">
            ({{ alert.typology }}, version {{ alert.typology_version
            }}<template v-if="typology">, definition status {{ typology.status }}</template
            >)
          </span>
        </p>
        <p v-if="typology">{{ typology.summary }}</p>
        <p class="muted">Explainer: {{ alert.explanation.typology_reference.doc_path }}</p>
        <h3>Sources</h3>
        <ul class="plain-list" data-testid="citations">
          <li v-for="item in citations" :key="item.key" class="row">
            <template v-if="item.citation">
              <a :href="item.citation.url" rel="noopener noreferrer" target="_blank">{{
                item.citation.title
              }}</a>
              <span class="muted">
                {{ item.citation.publisher
                }}<template v-if="item.citation.year !== null">, {{ item.citation.year }}</template>
              </span>
            </template>
            <span v-else>{{ item.key }}</span>
          </li>
        </ul>
      </section>
    </div>

    <details class="reproduce">
      <summary>How to reproduce this finding</summary>
      <dl class="properties">
        <dt>detector</dt>
        <dd>{{ alert.detector.name }} {{ alert.detector.version }}</dd>
        <dt>run</dt>
        <dd>{{ alert.run_id }}</dd>
        <dt>query SHA-256</dt>
        <dd class="mono">{{ alert.detector.query_sha256 }}</dd>
      </dl>
      <pre class="mono">{{ alert.evidence.query.cypher }}</pre>
      <pre class="mono">{{ JSON.stringify(alert.evidence.query.parameters, null, 2) }}</pre>
    </details>
  </article>
</template>
