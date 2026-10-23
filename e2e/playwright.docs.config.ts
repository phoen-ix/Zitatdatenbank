import { defineConfig, devices } from '@playwright/test'

/* The docs tour (./docs): the README screenshots of a seeded demo database,
 * and a render check of every page it visits.
 *
 *   npx playwright test -c playwright.docs.config.ts
 *
 * Screenshots land in ../docs/screenshots (DOCS_SCREENSHOT_DIR overrides).
 * scripts/docs-screenshots.sh runs it against a fresh stack. */
export default defineConfig({
  testDir: './docs',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:25600',
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
    locale: 'en-GB',
    launchOptions: {
      args: ['--lang=en-GB'],
      env: { ...process.env, LANG: 'en_GB.UTF-8', LANGUAGE: 'en_GB:en', LC_ALL: 'en_GB.UTF-8' },
    },
    timezoneId: 'Europe/Vienna',
    contextOptions: { reducedMotion: 'reduce' },
    screenshot: 'only-on-failure',
    trace: 'off',
  },
})
