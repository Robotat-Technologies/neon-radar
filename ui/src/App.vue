<script setup lang="ts">
// The shell: navigation, the notices from GET /meta on every page, then the page. No page that
// shows entities or alerts renders before the notices are there.
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

import NoticeBanner from '@/components/NoticeBanner.vue'
import { useMetaStore } from '@/stores/meta'

const metaStore = useMetaStore()

onMounted(() => {
  if (!metaStore.meta) void metaStore.load()
})
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
