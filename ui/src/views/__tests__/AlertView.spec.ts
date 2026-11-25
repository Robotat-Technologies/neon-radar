import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { readExample } from '@/__tests__/fixtures'
import { api } from '@/api/client'
import type { Alert, AlertDetail, Subgraph } from '@/api/types'
import { downloadEvidence } from '@/lib/evidence-export'
import AlertView from '@/views/AlertView.vue'

vi.mock('@/lib/evidence-export', () => ({ downloadEvidence: vi.fn<typeof downloadEvidence>() }))

const detail: AlertDetail = {
  alert: readExample<Alert>('c4/circular_flow.json'),
  evidence: readExample<Subgraph>('c3/subgraph.json'),
}

describe('Alert evidence downloads', () => {
  afterEach(() => vi.restoreAllMocks())

  it('keeps both export actions available even when the typology catalog fails', async () => {
    vi.spyOn(api, 'getAlert').mockResolvedValue(detail)
    vi.spyOn(api, 'getTypology').mockRejectedValue(new Error('Unavailable'))
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: AlertView },
        { path: '/alerts', component: { template: '<div />' } },
        { path: '/entities/:id', name: 'entity', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    const wrapper = mount(AlertView, {
      props: { id: detail.alert.alert_id },
      global: { plugins: [createPinia(), router], stubs: { GraphCanvas: true } },
    })
    await flushPromises()
    const actions = wrapper.get('[aria-label="Download evidence"]')
    const buttons = actions.findAll('button')
    expect(buttons.map((button) => button.text())).toEqual(['Download JSON', 'Download CSV'])
    await buttons[0]!.trigger('click')
    expect(downloadEvidence).toHaveBeenLastCalledWith(detail, 'json')
    await buttons[1]!.trigger('click')
    expect(downloadEvidence).toHaveBeenLastCalledWith(detail, 'csv')
    expect(wrapper.text()).toContain('The typology reference could not be loaded.')
  })
})
