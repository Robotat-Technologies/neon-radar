import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '@/App.vue'
import type { FetchLike } from '@/api/client'
import type { MetaResponse } from '@/api/types'
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
  return { wrapper, router }
}

function metaAnswer(body: MetaResponse): Response {
  return new Response(JSON.stringify(body), { headers: { 'content-type': 'application/json' } })
}

/** A fetch that gives each /meta call the next answer of the list (an Error rejects). */
function stubMetaSequence(...answers: (MetaResponse | Error)[]) {
  const fetch = vi.fn<FetchLike>(() => {
    const next = answers.shift()
    if (next === undefined) throw new Error('no more answers')
    return next instanceof Error ? Promise.reject(next) : Promise.resolve(metaAnswer(next))
  })
  vi.stubGlobal('fetch', fetch)
  return fetch
}

describe('App shell', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('shows the standing disclaimer and the synthetic demo notice before the page', async () => {
    useMetaStore().meta = meta(registry({ nr_synthetic: 120 }))
    const { wrapper } = await mountApp()

    const standing = wrapper.get('[data-testid="standing-disclaimer"]')
    const notice = wrapper.get('[data-testid="data-notice"]')
    expect(standing.text()).toBe(disclaimers.standing)
    expect(notice.text()).toBe(disclaimers.synthetic_demo)
    expect(notice.attributes('data-notice-kind')).toBe('synthetic_demo')
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)
  })

  it('shows the real data notice when a real dataset is loaded', async () => {
    useMetaStore().meta = meta(registry({ nr_synthetic: 120, gb_companies_house: 20 }))
    const { wrapper } = await mountApp()

    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.real_data)
  })

  it('shows no page when the notices cannot be loaded', async () => {
    stubMetaSequence(new TypeError('Failed to fetch'))
    const { wrapper } = await mountApp()

    expect(wrapper.find('[data-testid="meta-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(false)
  })

  it('loads the notices from GET /api/v1/meta', async () => {
    const fetch = stubMetaSequence(meta(registry({ nr_synthetic: 1 })))
    const { wrapper } = await mountApp()

    expect(fetch).toHaveBeenCalledWith('/api/v1/meta', expect.anything())
    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)
  })

  it('refreshes the notices on navigation and switches when a real dataset is loaded', async () => {
    const fetch = stubMetaSequence(
      meta(registry({ nr_synthetic: 120 })),
      meta(registry({ nr_synthetic: 120, gb_companies_house: 20 })),
    )
    const { wrapper, router } = await mountApp()
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.synthetic_demo)

    await router.push('/alerts')
    await flushPromises()

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.real_data)
    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
  })

  it('keeps the current notices when a refresh fails', async () => {
    stubMetaSequence(meta(registry({ nr_synthetic: 120 })), new TypeError('Failed to fetch'))
    const { wrapper, router } = await mountApp()

    await router.push('/sources')
    await flushPromises()

    expect(wrapper.get('[data-testid="standing-disclaimer"]').text()).toBe(disclaimers.standing)
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.synthetic_demo)
    expect(wrapper.find('[data-testid="meta-error"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)
  })

  it('keeps the current notices on screen while a refresh is running', async () => {
    let release: (answer: Response) => void = () => {}
    const fetch = vi.fn<FetchLike>()
    fetch.mockResolvedValueOnce(metaAnswer(meta(registry({ nr_synthetic: 120 }))))
    fetch.mockReturnValueOnce(new Promise<Response>((resolve) => (release = resolve)))
    vi.stubGlobal('fetch', fetch)
    const { wrapper, router } = await mountApp()

    await router.push('/alerts')
    await flushPromises()
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.synthetic_demo)
    expect(wrapper.find('[data-testid="page"]').exists()).toBe(true)

    release(metaAnswer(meta(registry({ gleif_lei: 3 }))))
    await flushPromises()
    expect(wrapper.get('[data-testid="data-notice"]').text()).toBe(disclaimers.real_data)
  })
})
