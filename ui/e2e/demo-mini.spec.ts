// The synthetic demo end to end (PHASE-1.md M1.9e): the UI, the API and Neo4j that
// `make demo-mini` (or `make demo-dev`) started, loaded with data/fixtures/demo-mini and one
// detection run. Nothing is mocked. The company searched for is read from the fixture, so a
// regenerated fixture needs no change here.
import { readdirSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

const REPO = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const FIXTURE_DIR = resolve(REPO, 'data/fixtures/demo-mini')
const wording = (id: string) =>
  readFileSync(resolve(REPO, `contracts/wording/${id}.txt`), 'utf-8').replace(/\n+$/, '')

interface FtmRecord {
  id: string
  schema: string
  properties: Record<string, string[] | undefined>
}

/** The first Company in the demo-mini record files, taking the files and their lines in order. */
function firstCompany(): { id: string; name: string } {
  const files = readdirSync(FIXTURE_DIR)
    .filter((file) => file.endsWith('.ftm.jsonl'))
    .sort()
  for (const file of files) {
    for (const line of readFileSync(resolve(FIXTURE_DIR, file), 'utf-8').split('\n')) {
      if (!line.trim()) continue
      const record = JSON.parse(line) as FtmRecord
      const name = record.properties.name?.[0]
      if (record.schema === 'Company' && name) return { id: record.id, name }
    }
  }
  throw new Error(`no Company record in ${FIXTURE_DIR}`)
}

const company = firstCompany()
const [firstWord = company.name] = company.name.split(/\s+/)
const SYNTHETIC_SCENARIO = /^Synthetic scenario/

// Every page must work under the UI server's Content-Security-Policy (ui/nginx.conf); the
// browser reports each blocked script, style or request on the console.
let policyViolations: string[] = []

test.beforeEach(({ page }) => {
  policyViolations = []
  page.on('console', (message) => {
    if (/Content Security Policy/i.test(message.text())) policyViolations.push(message.text())
  })
})

test.afterEach(() => {
  expect(policyViolations).toEqual([])
})

test('the standing disclaimer and the synthetic demo notice are visible', async ({
  page,
  baseURL,
}) => {
  const own = new URL(baseURL ?? 'http://localhost').hostname
  const external: string[] = []
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (url.protocol !== 'data:' && url.hostname !== own) external.push(request.url())
  })
  for (const path of ['/', '/alerts', `/entities/${company.id}`]) {
    await page.goto(path)
    const standing = page.getByTestId('standing-disclaimer')
    const notice = page.getByTestId('data-notice')
    await expect(standing).toBeVisible()
    await expect(standing).toHaveText(wording('standing-v1'))
    await expect(notice).toBeVisible()
    await expect(notice).toHaveAttribute('data-notice-kind', 'synthetic_demo')
    await expect(notice).toHaveText(wording('synthetic-demo-v1'))
  }
  expect(external).toEqual([])
})

test(`searching for "${firstWord}" finds ${company.name}`, async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('search-input').fill(firstWord)
  await page.getByRole('button', { name: 'Search' }).click()
  const hit = page
    .getByTestId('search-results')
    .getByRole('link', { name: company.name, exact: true })
  await expect(hit).toBeVisible()
  await hit.click()
  await expect(page).toHaveURL(new RegExp(`/entities/${company.id}$`))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(company.name)
})

test('the alerts page lists a synthetic scenario', async ({ page }) => {
  await page.goto('/alerts')
  const alerts = page.getByTestId('alert-list').getByRole('link', { name: SYNTHETIC_SCENARIO })
  await expect(alerts.first()).toBeVisible()
})

test('an alert page shows its explanation steps and the evidence graph', async ({ page }) => {
  await page.goto('/alerts')
  const link = page
    .getByTestId('alert-list')
    .getByRole('link', { name: SYNTHETIC_SCENARIO })
    .first()
  const headline = ((await link.textContent()) ?? '').trim()
  await link.click()
  await expect(page).toHaveURL(/\/alerts\/[^/]+$/)
  await expect(page.getByTestId('alert-headline')).toHaveText(headline)
  const steps = page.getByTestId('explanation-steps').getByRole('listitem')
  await expect(steps.first()).toBeVisible()
  expect(await steps.count()).toBeGreaterThanOrEqual(2)
  const evidence = page.getByRole('region', { name: 'Evidence', exact: true })
  await expect(evidence.getByTestId('graph-canvas').locator('canvas').first()).toBeVisible()
  await expect(evidence.locator('figcaption')).toContainText(/^\s*[1-9]\d* nodes/)
})

test(`the entity page of ${company.name} shows its network`, async ({ page }) => {
  // Opened by its address, so the UI server's fallback to index.html is exercised too.
  await page.goto(`/entities/${company.id}`)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(company.name)
  const network = page.getByRole('region', { name: 'Network', exact: true })
  await expect(network.getByTestId('graph-canvas').locator('canvas').first()).toBeVisible()
  await expect(network.locator('figcaption')).toContainText(/^\s*([2-9]|\d{2,}) nodes/)
})
