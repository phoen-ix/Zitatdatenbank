import { defineConfig, devices } from '@playwright/test'

/* The e2e suite (./tests, inventory in COVERAGE.md). Run it through
 * scripts/e2e.sh, which starts the stack; by hand against a running one:
 *
 *   E2E_BASE_URL=http://localhost:25600 DOCS_WEB_CONTAINER=zitatdatenbank_e2e-web npx playwright test
 *
 * `setup` imports the demo quotes and signs the admin in once (.auth/admin.json).
 * `main` runs in parallel; every test owns its quotes and tags (unique words).
 * `global` changes site-wide state (settings, theme, backup/restore), so it runs
 * afterwards, alone. `limits` exhausts the per-IP rate limits, so it runs last. */
export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  workers: 2,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:25600',
    viewport: { width: 1280, height: 800 },
    locale: 'de-AT',
    launchOptions: {
      args: ['--lang=de-AT'],
      env: { ...process.env, LANG: 'de_AT.UTF-8', LANGUAGE: 'de_AT:de', LC_ALL: 'de_AT.UTF-8' },
    },
    timezoneId: 'Europe/Vienna',
    actionTimeout: 15_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    { name: 'main', testIgnore: /(global|limits)\.spec\.ts|\.setup\.ts/, dependencies: ['setup'] },
    { name: 'global', testMatch: /global\.spec\.ts/, dependencies: ['main'], workers: 1 },
    { name: 'limits', testMatch: /limits\.spec\.ts/, dependencies: ['global'], workers: 1 },
  ],
})
