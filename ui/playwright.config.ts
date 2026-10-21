import process from 'node:process'
import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end tests against a NeonRadar stack that is already running (PHASE-1.md M1.9e), so
 * there is no webServer block: `make demo-mini` serves the UI on http://localhost:8080 (the
 * default), `make demo-dev` on http://localhost:5173 (`make e2e E2E_BASE_URL=...`).
 * Chromium only, always headless. See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  expect: { timeout: 10 * 1000 },
  /* Fail on CI if test.only was left in the source. */
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  /* The HTML report is written to playwright-report/ (CI uploads it on failure), never opened. */
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080',
    headless: true,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
