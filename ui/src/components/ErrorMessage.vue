<script setup lang="ts">
// Known UI errors are translated; other API details retain their original text.
import { computed } from 'vue'

import { ApiError } from '@/api/client'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'

const props = defineProps<{ error: unknown }>()

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

const message = computed(() => {
  if (props.error instanceof ApiError) {
    if (props.error.status === 404) return text.value.entityNotFound
    if (props.error.status === 0) return text.value.apiUnavailable
    return props.error.message
  }

  return text.value.pageLoadError
})
</script>

<template>
  <p class="error" role="alert" dir="auto">{{ message }}</p>
</template>
