import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { EntityDetail, Subgraph } from '@/api/types'
import { useMetaStore } from '@/stores/meta'
import { dataset, meta } from '@/__tests__/fixtures'
import DataSourcesView from '../DataSourcesView.vue'
import EntityView from '../EntityView.vue'

const mocks = vi.hoisted(() => ({
  getEntity: vi.fn<() => Promise<EntityDetail>>(),
  getNetwork: vi.fn<() => Promise<Subgraph>>(),
}))

vi.mock('@/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/client')>()),
  api: { getEntity: mocks.getEntity, getNetwork: mocks.getNetwork },
}))

const ErrorMessageStub = defineComponent({
  props: { error: { type: null, required: true } },
  template: '<p role="alert">Request failed</p>',
})

const GraphCanvasStub = defineComponent({
  template: '<div data-testid="graph">Network graph</div>',
})

const entityDetail: EntityDetail = {
  entity: {
    id: 'syn-co-0003',
    schema: 'Company',
    caption: 'Fenwhistle Holdings Ltd',
    labels: ['Entity', 'LegalEntity', 'Organization', 'Company'],
    flags: { synthetic: true, sanctioned: false, pep: false, rca: false },
    countries: ['gb'],
    datasets: ['nr_synthetic'],
  },
  names: ['Fenwhistle Holdings Ltd'],
  properties: { jurisdiction: 'gb' },
  identifiers: { registration_number: ['SYN00003'] },
  provenance: [
    { dataset: 'nr_synthetic', record_id: 'syn-co-0003', retrieved_at: null, source_url: null },
  ],
  relationship_counts: { HAS_ADDRESS: 1 },
  alerts: [],
}

const network: Subgraph = {
  nodes: [],
  edges: [],
  truncated: false,
  limits: { max_nodes: 100, max_edges: 200 },
}

function mountEntity() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/entities/:id', name: 'entity', component: EntityView, props: true }],
  })
  return mount(EntityView, {
    props: { id: 'syn-co-0003' },
    global: {
      plugins: [router],
      stubs: { ErrorMessage: ErrorMessageStub, GraphCanvas: GraphCanvasStub },
    },
  })
}

describe('EntityView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mocks.getEntity.mockReset()
    mocks.getNetwork.mockReset()
    mocks.getNetwork.mockResolvedValue(network)
  })

  it('organizes entity identity before details and shows the network', async () => {
    mocks.getEntity.mockResolvedValue(entityDetail)
    const wrapper = mountEntity()
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('Fenwhistle Holdings Ltd')
    expect(wrapper.get('#network-heading').text()).toBe('Network')
    expect(wrapper.get('#details-heading').text()).toBe('Details')
    expect(wrapper.get('#sources-heading').text()).toBe('Source records')
    expect(wrapper.get('[data-testid="graph"]').text()).toBe('Network graph')
  })

  it('offers recovery when entity details fail', async () => {
    mocks.getEntity
      .mockRejectedValueOnce(new Error('temporary failure'))
      .mockResolvedValueOnce(entityDetail)
    const wrapper = mountEntity()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(mocks.getEntity).toHaveBeenCalledTimes(2)
    expect(wrapper.get('h1').text()).toBe('Fenwhistle Holdings Ltd')
  })

  it('offers independent recovery when the network fails', async () => {
    mocks.getEntity.mockResolvedValue(entityDetail)
    mocks.getNetwork
      .mockRejectedValueOnce(new Error('temporary failure'))
      .mockResolvedValueOnce(network)
    const wrapper = mountEntity()
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(mocks.getNetwork).toHaveBeenCalledTimes(2)
    expect(wrapper.get('[data-testid="graph"]').text()).toBe('Network graph')
  })
})

describe('DataSourcesView', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows load time when the API provides freshness data', () => {
    const source = dataset('nr_synthetic', true, 12, 'NeonRadar synthetic data')
    source.loaded_at = '2026-11-22T10:15:02Z'
    useMetaStore().meta = meta([source])
    const wrapper = mount(DataSourcesView)

    expect(wrapper.get('[data-testid="datasets"]').text()).toContain('2026-11-22 10:15:02 UTC')
    expect(wrapper.get('h2').text()).toBe('NeonRadar synthetic data')
  })

  it('keeps source information recoverable when the first meta request fails', async () => {
    const store = useMetaStore()
    store.error = 'The API could not be reached.'
    const wrapper = mount(DataSourcesView)

    expect(wrapper.get('[role="alert"]').text()).toContain('could not be loaded')
    expect(wrapper.get('button').text()).toBe('Try again')
  })

  it('does not hide existing sources while metadata refreshes', () => {
    const source = dataset('nr_synthetic', true, 12, 'NeonRadar synthetic data')
    const store = useMetaStore()
    store.meta = meta([source])
    store.loading = true
    const wrapper = mount(DataSourcesView)

    expect(wrapper.get('[data-testid="datasets"]').text()).toContain('NeonRadar synthetic data')
    expect(wrapper.text()).toContain('Refreshing source information')
  })
})
