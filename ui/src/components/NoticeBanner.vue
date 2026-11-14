<script setup lang="ts">
// Local translations are shown only for matching source notices.
import { computed } from 'vue'

import { messages } from '@/lib/messages'
import { localizedDataNotice, standingNoticeText } from '@/lib/notice-translations'
import type { DataNoticeKind } from '@/lib/notices'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps<{ standing: string; kind: DataNoticeKind; notice: string }>()

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

const standing = computed(() => standingNoticeText(props.standing, localeStore.locale))

const notice = computed(() => localizedDataNotice(props.notice, props.kind, localeStore.locale))
</script>

<template>
  <section class="notices" :aria-label="text.notices">
    <p
      class="notice notice--standing"
      role="note"
      :dir="localeStore.isArabic ? 'rtl' : 'ltr'"
      data-testid="standing-disclaimer"
    >
      {{ standing }}
    </p>

    <p
      class="notice"
      :class="props.kind === 'synthetic_demo' ? 'notice--synthetic' : 'notice--real'"
      role="note"
      :dir="localeStore.isArabic ? 'rtl' : 'ltr'"
      data-testid="data-notice"
      :data-notice-kind="props.kind"
    >
      {{ notice }}
    </p>
  </section>
</template>
