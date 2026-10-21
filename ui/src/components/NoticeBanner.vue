<script setup lang="ts">
// The standing disclaimer, always, and the synthetic demo notice or the real data notice
// (PHASE-1.md 7.1). Both texts come verbatim from GET /meta.
import type { DataNoticeKind } from '@/lib/notices'

const props = defineProps<{ standing: string; kind: DataNoticeKind; notice: string }>()
</script>

<template>
  <section class="notices" aria-label="Notices">
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
  </section>
</template>
