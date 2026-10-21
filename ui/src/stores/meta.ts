// GET /meta: the disclaimers, the dataset registry with what is loaded, and versions. Every page
// that shows entities or alerts waits for it, so the notices are always there first.
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { ApiError, api, type ApiClient } from '@/api/client'
import type { MetaResponse } from '@/api/types'
import { dataNoticeText, selectDataNotice } from '@/lib/notices'

export const useMetaStore = defineStore('meta', () => {
  const meta = ref<MetaResponse | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  async function load(client: ApiClient = api): Promise<void> {
    loading.value = true
    error.value = null
    try {
      meta.value = await client.getMeta()
    } catch (caught) {
      error.value =
        caught instanceof ApiError ? caught.message : 'The NeonRadar API could not be reached.'
    } finally {
      loading.value = false
    }
  }

  const noticeKind = computed(() => (meta.value ? selectDataNotice(meta.value.datasets) : null))
  const noticeText = computed(() =>
    meta.value && noticeKind.value ? dataNoticeText(noticeKind.value, meta.value.disclaimers) : '',
  )

  /** The registry title of a dataset slug, or the slug when the registry does not list it. */
  function datasetTitle(slug: string): string {
    return meta.value?.datasets.find((dataset) => dataset.slug === slug)?.title ?? slug
  }

  return { meta, error, loading, load, noticeKind, noticeText, datasetTitle }
})
