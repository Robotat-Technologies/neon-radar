<script setup lang="ts">
// Alert (/alerts/:id): evidence, explanation, references and metrics.
// API content retains its original wording; interface labels are translated.
import { computed, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { displayTerm } from '@/lib/terms'
import { api } from '@/api/client'
import {
  localizedAlertHeadline,
  localizedAlertText,
  localizedCycleSummary,
  localizedPaymentStep,
} from '@/lib/alert-translations'
import type { AlertDetail, Citation, TypologyDetail } from '@/api/types'
import AlertDataLabel from '@/components/AlertDataLabel.vue'
import ErrorMessage from '@/components/ErrorMessage.vue'
import ExternalLink from '@/components/ExternalLink.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import { formatMetric, formatStrength, formatTimestamp } from '@/lib/format'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { useMetaStore } from '@/stores/meta'

const props = defineProps<{ id: string }>()
const router = useRouter()
const metaStore = useMetaStore()
const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

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
      // Keep the typology slug and citation keys when its catalog entry is unavailable.
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

/** The alert's citation keys, with bibliography entries when available. */
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
  <p v-else-if="!detail || !alert" class="muted">{{ text.loading }}</p>

  <article v-else class="alert">
    <header class="page-header">
      <p class="muted">
        <bdi>{{ alert.alert_id }}</bdi>
      </p>

      <h1 data-testid="alert-headline">
        <bdi>
          {{ localizedAlertHeadline(alert.headline, alert.typology, localeStore.locale) }}
        </bdi>
      </h1>

      <div class="meta-line">
        <span class="badge" :class="`badge--${alert.priority}`">
          {{ text.priority }}: {{ text.priorityNames[alert.priority] }}
        </span>

        <span>
          {{ text.patternStrength }}:
          <bdi>{{ formatStrength(alert.pattern_strength) }}</bdi>
        </span>

        <span class="muted">
          {{ text.created }}:
          <bdi>{{ formatTimestamp(alert.created_at) }}</bdi>
        </span>

        <AlertDataLabel :flags="alert.data_flags" />
      </div>

      <p>
        {{ text.matchesGraphPattern }}
        <strong>
          <bdi>
            {{
              localizedAlertText(
                typology?.name ?? alert.typology.replace(/_/g, ' '),
                alert.typology,
                localeStore.locale,
              )
            }}
          </bdi> </strong
        >.
        <bdi>
          {{ localizedCycleSummary(alert.explanation.summary, alert.typology, localeStore.locale) }}
        </bdi>
      </p>
    </header>

    <section aria-labelledby="evidence-heading">
      <h2 id="evidence-heading">{{ text.evidence }}</h2>

      <GraphCanvas
        :subgraph="detail.evidence"
        :focus-ids="subjectIds"
        :highlight-edge-ids="highlightedEdges"
        :label="text.evidenceGraphLabel"
        @select="openNode"
      />
    </section>

    <div class="columns">
      <section aria-labelledby="steps-heading">
        <h2 id="steps-heading">{{ text.explanation }}</h2>
        <p class="muted">{{ text.selectExplanationStep }}</p>

        <ol class="steps" data-testid="explanation-steps">
          <li v-for="step in alert.explanation.steps" :key="step.order">
            <button
              type="button"
              class="step"
              :aria-pressed="selectedStep === step.order"
              @click="toggleStep(step.order)"
            >
              <bdi>
                {{ localizedPaymentStep(step.text, alert.typology, localeStore.locale) }}
              </bdi>
            </button>
          </li>
        </ol>

        <h2>{{ text.subjects }}</h2>

        <ul class="plain-list">
          <li v-for="subject in alert.subjects" :key="subject.entity_id" class="row">
            <RouterLink :to="{ name: 'entity', params: { id: subject.entity_id } }">
              <bdi>{{ subject.caption }}</bdi>
            </RouterLink>
            <span class="muted">
              <bdi>{{ displayTerm(subject.role, localeStore.locale) }}</bdi>
            </span>
          </li>
        </ul>

        <h2>{{ text.otherExplanations }}</h2>

        <ul class="plain-list">
          <li v-for="note in alert.explanation.false_positive_notes" :key="note" dir="auto">
            {{ localizedAlertText(note, alert.typology, localeStore.locale) }}
          </li>
        </ul>
      </section>

      <section aria-labelledby="metrics-heading">
        <h2 id="metrics-heading">{{ text.metrics }}</h2>

        <dl class="properties">
          <dt>{{ text.patternStrength }}</dt>
          <dd>
            <bdi>{{ formatStrength(alert.pattern_strength) }}</bdi>
          </dd>

          <template v-for="[key, value] in metrics" :key="key">
            <dt>
              <bdi>{{ displayTerm(key, localeStore.locale) }}</bdi>
            </dt>
            <dd>
              <bdi>{{ formatMetric(value) }}</bdi>
            </dd>
          </template>

          <template v-if="evidenceWindow">
            <dt>{{ text.evidenceWindow }}</dt>
            <dd>
              <bdi>{{ formatTimestamp(evidenceWindow.start) }}</bdi>
              {{ text.to }}
              <bdi>{{ formatTimestamp(evidenceWindow.end) }}</bdi>
            </dd>
          </template>

          <dt>{{ text.datasets }}</dt>
          <dd>
            <bdi>
              {{ alert.data_flags.datasets.map((slug) => metaStore.datasetTitle(slug)).join(', ') }}
            </bdi>
          </dd>
        </dl>

        <h2>{{ text.typology }}</h2>

        <p>
          <strong>
            <bdi>
              {{
                localizedAlertText(
                  typology?.name ?? alert.typology,
                  alert.typology,
                  localeStore.locale,
                )
              }}
            </bdi>
          </strong>
          <span class="muted">
            (<bdi>{{ alert.typology }}</bdi
            >, {{ text.version }} <bdi>{{ alert.typology_version }}</bdi>
            <template v-if="typology">
              , {{ text.definitionStatus }}
              <bdi>{{ displayTerm(typology.status, localeStore.locale) }}</bdi> </template
            >)
          </span>
        </p>

        <p v-if="typology" dir="auto">
          {{ localizedAlertText(typology.summary, alert.typology, localeStore.locale) }}
        </p>
        <p class="muted">
          {{ text.explainer }}:
          <bdi>{{ alert.explanation.typology_reference.doc_path }}</bdi>
        </p>

        <h3>{{ text.sources }}</h3>

        <ul class="plain-list" data-testid="citations">
          <li v-for="item in citations" :key="item.key" class="row">
            <template v-if="item.citation">
              <ExternalLink :href="item.citation.url">
                <bdi>{{ item.citation.title }}</bdi>
              </ExternalLink>
              <span class="muted">
                <bdi>{{ item.citation.publisher }}</bdi>
                <template v-if="item.citation.year !== null">
                  , <bdi>{{ item.citation.year }}</bdi>
                </template>
              </span>
            </template>
            <span v-else
              ><bdi>{{ item.key }}</bdi></span
            >
          </li>
        </ul>
      </section>
    </div>

    <details class="reproduce">
      <summary>{{ text.reproduceFinding }}</summary>

      <dl class="properties">
        <dt>{{ text.detector }}</dt>
        <dd>
          <bdi>{{ alert.detector.name }} {{ alert.detector.version }}</bdi>
        </dd>

        <dt>{{ text.run }}</dt>
        <dd>
          <bdi>{{ alert.run_id }}</bdi>
        </dd>

        <dt>{{ text.queryHash }}</dt>
        <dd class="mono">
          <bdi>{{ alert.detector.query_sha256 }}</bdi>
        </dd>
      </dl>

      <pre class="mono" dir="ltr">{{ alert.evidence.query.cypher }}</pre>
      <pre class="mono" dir="ltr">{{
        JSON.stringify(alert.evidence.query.parameters, null, 2)
      }}</pre>
    </details>
  </article>
</template>
