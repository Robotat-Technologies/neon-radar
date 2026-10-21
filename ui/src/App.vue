<script setup lang="ts">
// The shell: navigation, the notices from GET /meta on every page, then the page. No page that
// shows entities or alerts renders before the notices are there, and every navigation refreshes
// them, so the notice follows what is loaded.
import { onMounted, onUnmounted } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'

import NoticeBanner from '@/components/NoticeBanner.vue'
import { useMetaStore } from '@/stores/meta'

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
    <RouterLink to="/" class="brand">NeonRadar</RouterLink>
    <nav aria-label="Main">
      <RouterLink to="/">Search</RouterLink>
      <RouterLink to="/alerts">Alerts</RouterLink>
      <RouterLink to="/sources">Data sources</RouterLink>
    </nav>
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
      <p>
        NeonRadar could not load its notices from the API, so it shows no data.
        {{ metaStore.error }}
      </p>
      <button type="button" @click="metaStore.load()">Try again</button>
    </div>
    <p v-else class="muted">Loading…</p>
  </main>

  <footer v-if="metaStore.meta" class="site-footer muted">
    NeonRadar {{ metaStore.meta.app_version }} · contracts {{ metaStore.meta.contracts_version }} ·
    graph schema {{ metaStore.meta.schema_version }}
  </footer>
</template>
