import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api/client'
import type { SearchResponse } from '@/api/types'
import SearchView from '@/views/SearchView.vue'

function answer(query: string, total = 0): SearchResponse {
  return { query, items: [], total_estimate: total }
}

function deferred<T>() {
  let resolve: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve: resolve! }
}

async function mountSearch(path = '/') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'search', component: SearchView },
      { path: '/entities/:id', name: 'entity', component: SearchView },
    ],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(SearchView, { global: { plugins: [router, createPinia()] } })
  return { router, wrapper }
}

describe('SearchView', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.restoreAllMocks())

  it('offers an empty state before a search', async () => {
    const { wrapper } = await mountSearch()

    expect(wrapper.get('[data-testid="search-prompt"]').text()).toBe(
      'Enter a name, address or account number to begin.',
    )
    expect(wrapper.get('[aria-live="polite"]').attributes('aria-busy')).toBe('false')
  })

  it('announces loading and explains an empty search response', async () => {
    const pending = deferred<SearchResponse>()
    vi.spyOn(api, 'search').mockReturnValue(pending.promise)
    const { wrapper } = await mountSearch('/?q=lea')

    expect(wrapper.get('[data-testid="search-loading"]').attributes('role')).toBe('status')
    pending.resolve(answer('lea'))
    await flushPromises()
    expect(wrapper.get('[data-testid="search-count"]').text()).toBe('No matches for “lea”.')
    expect(wrapper.get('[data-testid="search-empty"]').text()).toBe(
      'Try a different spelling or change the filters.',
    )
  })

  it('keeps the result for the latest query when responses arrive out of order', async () => {
    const first = deferred<SearchResponse>()
    const second = deferred<SearchResponse>()
    vi.spyOn(api, 'search').mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    const { router, wrapper } = await mountSearch('/?q=lea')

    await router.push({ name: 'search', query: { q: 'fen' } })
    second.resolve(answer('fen'))
    await flushPromises()
    expect(wrapper.get('[data-testid="search-count"]').text()).toBe('No matches for “fen”.')

    first.resolve(answer('lea'))
    await flushPromises()
    expect(wrapper.get('[data-testid="search-count"]').text()).toBe('No matches for “fen”.')
  })

  it('invalidates a pending response when the query is cleared', async () => {
    const pending = deferred<SearchResponse>()
    vi.spyOn(api, 'search').mockReturnValue(pending.promise)
    const { wrapper } = await mountSearch('/?q=lea')

    expect(wrapper.find('[data-testid="search-loading"]').exists()).toBe(true)
    await wrapper.get('[data-testid="search-input"]').setValue('')
    expect(wrapper.find('[data-testid="search-prompt"]').exists()).toBe(true)
    expect(wrapper.get('[aria-live="polite"]').attributes('aria-busy')).toBe('false')

    pending.resolve(answer('lea'))
    await flushPromises()

    expect(wrapper.find('[data-testid="search-prompt"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="search-count"]').exists()).toBe(false)
  })

  it('keeps entity type filters collapsed until the filter control is opened', async () => {
    const { wrapper } = await mountSearch()

    const toggle = wrapper.get('.filter-toggle')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(toggle.text()).toContain('All entity types')
    expect(wrapper.find('#entity-type-filters').exists()).toBe(false)

    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    const inputs = wrapper.findAll('#entity-type-filters input[type="checkbox"]')
    expect(inputs).toHaveLength(6)

    await inputs[0]!.setValue(true)
    expect(toggle.text()).toContain('Person')
  })
})
