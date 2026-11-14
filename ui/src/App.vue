<script setup lang="ts">
// The shell keeps the API notices visible before displaying page data.
import { computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import NoticeBanner from '@/components/NoticeBanner.vue'
import { messages } from '@/lib/messages'
import { useLocaleStore } from '@/stores/locale'
import { useMetaStore } from '@/stores/meta'

const localeStore = useLocaleStore()
const text = computed(() => messages[localeStore.locale])

const metaStore = useMetaStore()
const removeAfterEach = useRouter().afterEach(() => {
  void metaStore.refresh()
})

onMounted(() => {
  if (!metaStore.meta) void metaStore.load()
})
onUnmounted(removeAfterEach)
</script>

<template>
  <header class="site-header">
    <RouterLink to="/" class="brand">
      <bdi>NeonRadar</bdi>
    </RouterLink>

    <nav :aria-label="text.mainNavigation">
      <RouterLink to="/">{{ text.search }}</RouterLink>
      <RouterLink to="/alerts">{{ text.alerts }}</RouterLink>
      <RouterLink to="/sources">{{ text.dataSources }}</RouterLink>
    </nav>

    <button
      type="button"
      :lang="localeStore.isArabic ? 'en' : 'ar'"
      :dir="localeStore.isArabic ? 'ltr' : 'rtl'"
      @click="localeStore.toggleLocale()"
    >
      {{ text.switchLanguage }}
    </button>
  </header>

  <main class="page">
    <template v-if="metaStore.meta && metaStore.noticeKind">
      <NoticeBanner
        :standing="metaStore.meta.disclaimers.standing"
        :kind="metaStore.noticeKind"
        :notice="metaStore.noticeText"
      />
      <RouterView />
    </template>

    <div v-else-if="metaStore.error" class="error" role="alert" data-testid="meta-error">
      <p>{{ text.noticesUnavailable }}</p>
      <p dir="auto">{{ metaStore.error }}</p>
      <button type="button" @click="metaStore.load()">
        {{ text.retry }}
      </button>
    </div>

    <p v-else class="muted">{{ text.loading }}</p>
  </main>

  <footer v-if="metaStore.meta" class="site-footer muted">
    <bdi>NeonRadar {{ metaStore.meta.app_version }}</bdi>
    · {{ text.contracts }}
    <bdi>{{ metaStore.meta.contracts_version }}</bdi>
    · {{ text.graphSchema }}
    <bdi>{{ metaStore.meta.schema_version }}</bdi>
  </footer>
</template>
