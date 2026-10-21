<script setup lang="ts">
// An API error as a sentence for people (the problem's detail when there is one).
import { computed } from 'vue'

import { ApiError } from '@/api/client'

const props = defineProps<{ error: unknown }>()

const message = computed(() => {
  if (props.error instanceof ApiError) {
    if (props.error.status === 404) return 'Nothing with this id was found.'
    return props.error.message
  }
  return 'Something went wrong while loading this page.'
})
</script>

<template>
  <p class="error" role="alert">{{ message }}</p>
</template>
