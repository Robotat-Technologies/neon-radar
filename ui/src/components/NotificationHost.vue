<script setup lang="ts">
// The one place toasts render (lib/notifications.ts). Mounted in the shell outside the metadata
// gate, so feedback works while the notices load or fail. Toasts sit at the inline end.
import { computed } from 'vue'
import { Toaster } from 'vue-sonner'
import 'vue-sonner/style.css'

import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()
const dir = computed(() => (localeStore.isArabic ? 'rtl' : 'ltr'))
const position = computed(() => (localeStore.isArabic ? 'bottom-left' : 'bottom-right'))
</script>

<template>
  <div class="notification-host" data-testid="notification-host">
    <Toaster :dir="dir" :position="position" theme="light" close-button />
  </div>
</template>

<style>
.notification-host [data-sonner-toaster][data-sonner-theme] {
  --normal-bg: var(--color-surface);
  --normal-border: var(--color-border);
  --normal-text: var(--color-text);
  font-family: var(--font-body);
}

.notification-host [data-sonner-toast] {
  overflow-wrap: anywhere;
}
</style>
