// The UI shell against a mocked API: every /api/v1 request is answered from the repository's
// contract files (wording texts and synthetic examples), so this runs without the API or Neo4j.
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test, type Page } from '@playwright/test'

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const read = (path: string) => readFileSync(resolve(REPO, path), 'utf-8')
const json = (path: string) => JSON.parse(read(path))
const wording = (id: string) => read(`contracts/wording/${id}.txt`).replace(/\n+$/, '')

const STANDING = wording('standing-v1')
const SYNTHETIC_DEMO = wording('synthetic-demo-v1')
const REAL_DATA = wording('real-data-v1')

const subgraph = json('contracts/examples/c3/subgraph.json')
const entityDetail = json('contracts/examples/c3/entity-detail.json')
const alert = json('contracts/examples/c4/circular_flow.json')
const summary = entityDetail.alerts[0]

function dataset(slug: string, synthetic: boolean, recordCount: number, title: string) {
  return {
    slug,
    title,
    licence_id: synthetic ? 'Apache-2.0' : 'OGL-UK-3.0',
    licence_url: 'about:blank',
    attribution: null,
    synthetic,
    personal_data: !synthetic,
    record_count: recordCount,
    loaded_at: null,
  }
}

function meta(realRecords = 0) {
  return {
    app_version: '0.1.0',
    contracts_version: '1.0.0',
    schema_version: '1.0.0',
    datasets: [
      dataset('gb_companies_house', false, realRecords, 'UK Companies House public register'),
      dataset('nr_synthetic', true, 41, 'NeonRadar synthetic data'),
    ],
    disclaimers: { standing: STANDING, synthetic_demo: SYNTHETIC_DEMO, real_data: REAL_DATA },
    counts: { nodes_by_label: {}, relationships_by_type: {} },
  }
}

const typology = {
  slug: 'circular_flow',
  name: 'Round-tripping or circular flows',
  tier: 'core',
  status: 'draft',
  summary: 'Funds leave an account, pass through other accounts and return to the originator.',
  detector_available: true,
  definition_markdown: null,
  graph_pattern: 'A directed cycle of PAID relationships.',
  citations: [
    {
      key: 'fatf_pml_2018',
      title: 'Professional Money Laundering',
      publisher: 'FATF',
      year: 2018,
      url: 'about:blank',
    },
  ],
  parameters: {},
  false_positives: [],
}

async function mockApi(page: Page, realRecords = 0) {
  const external: string[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (!['localhost', '127.0.0.1'].includes(url.hostname) && url.protocol !== 'data:') {
      external.push(request.url())
    }
  })
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname.replace('/api/v1', '')
    const answers: Record<string, unknown> = {
      '/meta': meta(realRecords),
      '/search': {
        query: 'fen',
        items: [
          { entity: entityDetail.entity, score: 3.2, matched_name: 'Fenwhistle Holdings Ltd' },
        ],
        total_estimate: 1,
      },
      '/entities/syn-co-0003': entityDetail,
      '/entities/syn-co-0003/network': subgraph,
      '/alerts': { items: [summary], next_cursor: null },
      [`/alerts/${alert.alert_id}`]: { alert, evidence: subgraph },
      '/typologies': [typology],
      '/typologies/circular_flow': typology,
    }
    if (path in answers) return route.fulfill({ json: answers[path] })
    return route.fulfill({
      status: 404,
      contentType: 'application/problem+json',
      json: {
        type: 'about:blank',
        title: 'Not Found',
        status: 404,
        detail: 'Not found.',
        instance: path,
      },
    })
  })
  return external
}

test('every page shows the standing disclaimer and the synthetic demo notice', async ({ page }) => {
  const external = await mockApi(page)
  for (const path of ['/', '/alerts', `/alerts/${alert.alert_id}`, '/entities/syn-co-0003']) {
    await page.goto(path)
    await expect(page.getByTestId('standing-disclaimer')).toHaveText(STANDING)
    await expect(page.getByTestId('data-notice')).toHaveText(SYNTHETIC_DEMO)
  }
  expect(external).toEqual([])
})

test('a loaded real dataset switches to the real data notice', async ({ page }) => {
  await mockApi(page, 12)
  await page.goto('/')
  await expect(page.getByTestId('data-notice')).toHaveText(REAL_DATA)
})

test('search finds an entity and opens its network', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')
  await page.getByTestId('search-input').fill('fen')
  await page.getByRole('button', { name: 'Search' }).click()
  await page.getByRole('link', { name: 'Fenwhistle Holdings Ltd' }).click()
  await expect(page).toHaveURL(/\/entities\/syn-co-0003$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Fenwhistle Holdings Ltd')
  await expect(page.getByTestId('graph-canvas').locator('canvas').first()).toBeVisible()
  await expect(page.locator('.badge--synthetic').first()).toHaveText('Synthetic')
})

test('the alert page shows steps, the evidence graph and citations', async ({ page }) => {
  await mockApi(page)
  await page.goto('/alerts')
  await expect(page.getByTestId('alert-list')).toContainText('Synthetic scenario')
  await page.getByRole('link', { name: /^Synthetic scenario/ }).click()
  await expect(page.getByTestId('alert-headline')).toHaveText(alert.headline)
  await expect(page.getByTestId('explanation-steps').locator('li')).toHaveCount(4)
  await expect(page.getByTestId('graph-canvas').locator('canvas').first()).toBeVisible()
  await expect(page.getByTestId('citations')).toContainText('Professional Money Laundering')
  await page.getByTestId('explanation-steps').getByRole('button').first().click()
  await expect(page.getByTestId('explanation-steps').getByRole('button').first()).toHaveAttribute(
    'aria-pressed',
    'true',
  )
})

for (const width of [1280, 390]) {
  test(`no page scrolls sideways at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await mockApi(page)
    for (const path of ['/', '/alerts', `/alerts/${alert.alert_id}`, '/entities/syn-co-0003']) {
      await page.goto(path)
      await expect(page.getByTestId('standing-disclaimer')).toBeVisible()
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      expect(overflow, path).toBeLessThanOrEqual(0)
    }
  })
}
