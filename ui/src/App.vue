<script setup lang="ts">
// Data remains behind the mandatory notice gate; navigation refreshes its metadata.
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import NoticeBanner from '@/components/NoticeBanner.vue'
import UiIcon from '@/components/UiIcon.vue'
import { useMetaStore } from '@/stores/meta'

const metaStore = useMetaStore()
const route = useRoute()
const main = ref<HTMLElement | null>(null)
const section = computed(() => {
  if (route.path.startsWith('/alerts')) return 'Alert review'
  if (route.path.startsWith('/entities/')) return 'Entity explorer'
  if (route.path === '/sources') return 'Data sources'
  return 'Search'
})
const removeAfterEach = useRouter().afterEach(() => {
  void metaStore.refresh()
})
watch(
  () => route.path,
  async () => {
    await nextTick()
    main.value?.focus()
  },
)
onMounted(() => {
  if (!metaStore.meta) void metaStore.load()
})
onUnmounted(removeAfterEach)
</script>

<template>
  <a class="skip-link" href="#main-content">Skip to main content</a>
  <div class="app-layout">
    <header class="site-header">
      <RouterLink to="/" class="brand">
        <span class="brand__mark"><UiIcon name="network" /></span>
        <span>NeonRadar<span class="brand__subtitle">INVESTIGATION TOOLKIT</span></span>
      </RouterLink>
      <div class="nav-label">WORKSPACE</div>
      <nav aria-label="Main">
        <RouterLink to="/" :class="{ 'nav-context-active': route.path.startsWith('/entities/') }">
          <UiIcon name="search" /><span>Search</span>
        </RouterLink>
        <RouterLink
          to="/alerts"
          :class="{ 'nav-context-active': route.path.startsWith('/alerts/') }"
          ><UiIcon name="alerts" /><span>Alerts</span></RouterLink
        >
        <RouterLink to="/sources"><UiIcon name="sources" /><span>Data sources</span></RouterLink>
      </nav>
      <div class="sidebar-note">
        <UiIcon name="shield" />
        <div>
          <strong>Local-first by design</strong>
          <p>Your workspace. Your evidence.</p>
        </div>
      </div>
    </header>

    <div class="workspace">
      <div class="workspace-bar">
        <div class="breadcrumb">
          <span>Workspace</span><span aria-hidden="true">/</span><strong>{{ section }}</strong>
        </div>
        <span class="workspace-label"><UiIcon name="network" />Graph investigation</span>
      </div>
      <main id="main-content" ref="main" class="page" tabindex="-1">
        <template v-if="metaStore.meta && metaStore.noticeKind">
          <NoticeBanner
            :standing="metaStore.meta.disclaimers.standing"
            :kind="metaStore.noticeKind"
            :notice="metaStore.noticeText"
          />
          <RouterView />
        </template>
        <div v-else-if="metaStore.error" class="state-panel" role="alert" data-testid="meta-error">
          <h1>Workspace unavailable</h1>
          <p>
            NeonRadar could not load its notices from the API, so it shows no data.
            {{ metaStore.error }}
          </p>
          <button type="button" @click="metaStore.load()">Try again</button>
        </div>
        <p v-else class="state-panel muted" role="status">Loading workspace…</p>
      </main>
      <footer v-if="metaStore.meta" class="site-footer muted">
        <span>NeonRadar {{ metaStore.meta.app_version }}</span>
        <span
          >Contracts {{ metaStore.meta.contracts_version }} · Graph schema
          {{ metaStore.meta.schema_version }}</span
        >
      </footer>
    </div>
  </div>
</template>
