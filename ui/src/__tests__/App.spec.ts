import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '@/App.vue'
import type { FetchLike } from '@/api/client'
import { useMetaStore } from '@/stores/meta'
import { disclaimers, meta, registry } from './fixtures'

const Page = { render: () => h('p', { 'data-testid': 'page' }, 'page content') }

async function mountApp() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: Page },
      { path: '/alerts', component: Page },
      { path: '/sources', component: Page },
    ],
  })
  await router.push('/')
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('App shell', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('shows the standing disclaimer and the synthetic demo notice before the page', async () => {
    useMetaStore().meta = meta(registry({ nr_synthetic: 120 }))
    const wrapper = await mountApp()

    const standing = wrapper.get('[data-testid="standing-disclaimer"]')
    const notice = wrapper.get('[data-testid="data-notice"]')
    expect(standing.text()).toBe(disclaimers.standing)
    expect(notice.text()).toBe(disclaimers.synthetic_demo)
    expect(notice.attributes('data-notice-kind')).toBe('synthetic_demo')
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)
  })

  it('shows the real data notice when a real dataset is loaded', async () => {
    useMetaStore().meta = meta(registry({ nr_synthetic: 120, gb_companies_house: 20 }))
    const wrapper = await mountApp()

    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.real_data)
  })

  it('shows no page when the notices cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<FetchLike>(() => Promise.reject(new TypeError('Failed to fetch'))),
    )
    const wrapper = await mountApp()

    expect(wrapper.find('[data-testid="meta-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(false)
  })

  it('loads the notices from GET /api/v1/meta', async () => {
    const fetch = vi.fn<FetchLike>(() =>
      Promise.resolve(
        new Response(JSON.stringify(meta(registry({ nr_synthetic: 1 }))), {
          headers: { 'content-type': 'application/json' },
        }),
      ),
    )
    vi.stubGlobal('fetch', fetch)
    const wrapper = await mountApp()

    expect(fetch).toHaveBeenCalledWith('/api/v1/meta', expect.anything())
    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)
  })
})
