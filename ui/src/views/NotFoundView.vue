<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])
</script>

<template>
  <section>
    <h1>{{ text.pageNotFound }}</h1>
    <p>
      {{ text.pageNotFoundDescription }}
      <RouterLink to="/">{{ text.goToSearch }}</RouterLink
      >.
    </p>
  </section>
</template>
