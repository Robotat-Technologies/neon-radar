// GET /meta: the disclaimers, the dataset registry with what is loaded, and versions. Every page
// that shows entities or alerts waits for it, so the notices are always there first. The shell
// refreshes it on every navigation, so loading a real dataset switches the notice without a
// reload; while a refresh runs, and when one fails, the notices already shown stay.
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, api, type ApiClient } from '@/api/client'
import type { MetaResponse } from '@/api/types'
import { dataNoticeText, selectDataNotice } from '@/lib/notices'

export const useMetaStore = defineStore('meta', () => {
  const meta = ref<MetaResponse | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)
  let request = 0

  async function load(client: ApiClient = api): Promise<void> {
    const current = ++request
    loading.value = true
    try {
      const answer = await client.getMeta()
      if (current !== request) return
      meta.value = answer
      error.value = null
    } catch (caught) {
      // A failed refresh keeps the notices already shown; only a first load reports an error.
      if (current !== request || meta.value) return
      error.value =
        caught instanceof ApiError ? caught.message : 'The NeonRadar API could not be reached.'
    } finally {
      if (current === request) loading.value = false
    }
  }

  /** Fetch /meta again unless a request is already running; the current notices stay meanwhile. */
  function refresh(client: ApiClient = api): Promise<void> {
    return loading.value ? Promise.resolve() : load(client)
  }

  const noticeKind = computed(() => (meta.value ? selectDataNotice(meta.value.datasets) : null))
  const noticeText = computed(() =>
    meta.value && noticeKind.value ? dataNoticeText(noticeKind.value, meta.value.disclaimers) : '',
  )

  /** The registry title of a dataset slug, or the slug when the registry does not list it. */
  function datasetTitle(slug: string): string {
    return meta.value?.datasets.find((dataset) => dataset.slug === slug)?.title ?? slug
  }

  return { meta, error, loading, load, refresh, noticeKind, noticeText, datasetTitle }
})
