<script setup lang="ts">
// Alert (/alerts/:id): the evidence subgraph, the explanation steps, the typology reference
// with its citations, and the metrics (contract C4).
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { api } from '@/api/client'
import type { AlertDetail, Citation, TypologyDetail } from '@/api/types'
import AlertDataLabel from '@/components/AlertDataLabel.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import ExternalLink from '@/components/ExternalLink.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import UiIcon from '@/components/UiIcon.vue'
import { downloadEvidence } from '@/lib/evidence-export'
import { formatMetric, formatStrength, formatTimestamp, humanizeKey } from '@/lib/format'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ id: string }>()
const router = useRouter()
const metaStore = useMetaStore()

const detail = ref<AlertDetail | null>(null)
const error = ref<unknown>(null)
const typology = ref<TypologyDetail | null>(null)
const typologyError = ref<unknown>(null)
const selectedStep = ref<number | null>(null)
let request = 0
let typologyRequest = 0

async function loadTypology(slug: string, detailRequest: number): Promise<void> {
  const current = ++typologyRequest
  typology.value = null
  typologyError.value = null
  try {
    const reference = await api.getTypology(slug)
    if (detailRequest === request && current === typologyRequest) typology.value = reference
  } catch (caught) {
    if (detailRequest === request && current === typologyRequest) typologyError.value = caught
  }
}

async function load(id: string): Promise<void> {
  const current = ++request
  detail.value = null
  error.value = null
  typology.value = null
  typologyError.value = null
  selectedStep.value = null
  try {
    const answer = await api.getAlert(id)
    if (current !== request) return
    detail.value = answer
    await loadTypology(answer.alert.typology, current)
  } catch (caught) {
    if (current === request) error.value = caught
  }
}

function retryAlert(): void {
  void load(props.id)
}

function retryTypology(): void {
  if (alert.value) void loadTypology(alert.value.typology, request)
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
  <div v-if="error" class="alert-detail__error">
    <ErrorMessage :error="error" />
    <button type="button" @click="retryAlert">Try again</button>
  </div>
  <p v-else-if="!detail || !alert" class="muted alert-detail__loading">Loading alert…</p>
  <article v-else class="alert alert-detail">
    <RouterLink class="back-link" to="/alerts">← Back to alerts</RouterLink>
    <header class="page-header page-header--split">
      <div>
        <p class="eyebrow">EVIDENCE REVIEW</p>
        <h1 data-testid="alert-headline">{{ alert.headline }}</h1>
        <p class="mono muted">{{ alert.alert_id }}</p>
        <div class="meta-line">
          <span class="badge" :class="`badge--${alert.priority}`"
            >{{ alert.priority }} priority</span
          >
          <span>Pattern strength {{ formatStrength(alert.pattern_strength) }}</span>
          <AlertDataLabel :flags="alert.data_flags" />
        </div>
      </div>
      <div class="export-block">
        <div class="export-actions" role="group" aria-label="Download evidence">
          <button class="button-primary" type="button" @click="downloadEvidence(detail, 'json')">
            <UiIcon name="download" />Download JSON
          </button>
          <button type="button" @click="downloadEvidence(detail, 'csv')">
            <UiIcon name="download" />Download CSV
          </button>
        </div>
        <p class="muted">Alert and evidence · ready for offline review</p>
      </div>
    </header>
    <p class="alert-summary">
      Matches the graph pattern of
      <strong>{{ typology?.name ?? alert.typology.replace(/_/g, ' ') }}</strong
      >.
      {{ alert.explanation.summary }}
    </p>
    <p v-if="detail.evidence.truncated" class="notice notice--standing">
      The evidence graph is truncated; downloads contain only the graph returned for this alert.
    </p>

    <div class="investigation-grid">
      <section class="panel graph-panel" aria-labelledby="evidence-heading">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">FOLLOW THE CONNECTIONS</p>
            <h2 id="evidence-heading">Evidence network</h2>
          </div>
          <UiIcon name="network" />
        </div>
        <GraphCanvas
          :subgraph="detail.evidence"
          :focus-ids="subjectIds"
          :highlight-edge-ids="highlightedEdges"
          label="Evidence subgraph of this alert"
          @select="openNode"
        />
      </section>
      <section class="panel explanation-panel" aria-labelledby="steps-heading">
        <div class="panel-heading">
          <div>
            <p class="eyebrow">UNDERSTAND THE PATTERN</p>
            <h2 id="steps-heading">Explanation</h2>
          </div>
        </div>
        <p class="muted">Select a step to highlight its relationships in the graph.</p>
        <ol class="steps" data-testid="explanation-steps">
          <li v-for="step in alert.explanation.steps" :key="step.order">
            <button
              type="button"
              class="step"
              :aria-pressed="selectedStep === step.order"
              @click="toggleStep(step.order)"
            >
              <span class="step__number" aria-hidden="true">{{ step.order }}</span
              ><span>{{ step.text }}</span>
            </button>
          </li>
        </ol>
      </section>
    </div>

    <div class="columns supporting-panels">
      <section class="panel" aria-labelledby="subjects-heading">
        <h2 id="subjects-heading">Subjects & context</h2>
        <ul class="plain-list">
          <li v-for="subject in alert.subjects" :key="subject.entity_id" class="row">
            <RouterLink :to="{ name: 'entity', params: { id: subject.entity_id } }">{{
              subject.caption
            }}</RouterLink>
            <span class="muted">{{ humanizeKey(subject.role) }}</span>
          </li>
        </ul>
        <h3>Other explanations for this structure</h3>
        <ul class="context-list">
          <li v-for="note in alert.explanation.false_positive_notes" :key="note">{{ note }}</li>
        </ul>
      </section>
      <section class="panel" aria-labelledby="metrics-heading">
        <h2 id="metrics-heading">Recorded metrics</h2>
        <dl class="properties">
          <dt>pattern strength</dt>
          <dd>{{ formatStrength(alert.pattern_strength) }}</dd>
          <template v-for="[key, value] in metrics" :key="key"
            ><dt>{{ humanizeKey(key) }}</dt>
            <dd>{{ formatMetric(value) }}</dd></template
          >
          <template v-if="evidenceWindow"
            ><dt>window</dt>
            <dd>
              {{ formatTimestamp(evidenceWindow.start) }} to
              {{ formatTimestamp(evidenceWindow.end) }}
            </dd></template
          >
          <dt>created</dt>
          <dd>{{ formatTimestamp(alert.created_at) }}</dd>
          <dt>datasets</dt>
          <dd>
            {{ alert.data_flags.datasets.map((slug) => metaStore.datasetTitle(slug)).join(', ') }}
          </dd>
        </dl>
      </section>
      <section class="panel" aria-labelledby="typology-heading">
        <h2 id="typology-heading">Typology & sources</h2>
        <p>
          <strong>{{ typology?.name ?? alert.typology }}</strong>
        </p>
        <p class="muted">
          Version {{ alert.typology_version
          }}<template v-if="typology"> · {{ typology.status }} definition</template>
        </p>
        <p v-if="typology">{{ typology.summary }}</p>
        <div v-if="typologyError" class="alert-detail__typology-error" role="status">
          <p class="error">The typology reference could not be loaded.</p>
          <p class="muted">
            The alert's evidence and explanation remain available, using its recorded typology
            reference and citation keys.
          </p>
          <button type="button" @click="retryTypology">Try again</button>
        </div>
        <ul class="plain-list" data-testid="citations">
          <li v-for="item in citations" :key="item.key">
            <template v-if="item.citation"
              ><ExternalLink :href="item.citation.url">{{ item.citation.title }}</ExternalLink
              ><span class="source-caption muted"
                >{{ item.citation.publisher
                }}<template v-if="item.citation.year !== null"
                  >, {{ item.citation.year }}</template
                ></span
              ></template
            >
            <span v-else>{{ item.key }}</span>
          </li>
        </ul>
        <p class="mono muted">Explainer: {{ alert.explanation.typology_reference.doc_path }}</p>
      </section>
    </div>
    <details class="reproduce panel">
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
