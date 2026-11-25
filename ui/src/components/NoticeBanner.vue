<script setup lang="ts">
// The standing disclaimer, always, and the synthetic demo notice or the real data notice
// (PHASE-1.md 7.1). Both texts come verbatim from GET /meta.
import type { DataNoticeKind } from '@/lib/notices'

const props = defineProps<{ standing: string; kind: DataNoticeKind; notice: string }>()
</script>

<template>
  <details class="notices" open>
    <summary class="notice-summary">
      <span class="notice-summary__title">Workspace notices</span>
      <span
        class="notice-summary__state"
        :class="
          props.kind === 'synthetic_demo'
            ? 'notice-summary__state--synthetic'
            : 'notice-summary__state--real'
        "
        data-testid="notice-summary-state"
      >
        {{ props.kind === 'synthetic_demo' ? 'Synthetic demo' : 'Real data loaded' }}
      </span>
      <span class="notice-summary__action">
        <span class="notice-summary__show">Show notices</span>
        <span class="notice-summary__hide">Hide notices</span>
      </span>
    </summary>
    <div class="notice-list" aria-label="Notices">
      <p class="notice notice--standing" role="note" data-testid="standing-disclaimer">
        {{ props.standing }}
      </p>
      <p
        class="notice"
        :class="props.kind === 'synthetic_demo' ? 'notice--synthetic' : 'notice--real'"
        role="note"
        data-testid="data-notice"
        :data-notice-kind="props.kind"
      >
        {{ props.notice }}
      </p>
    </div>
  </details>
</template>
