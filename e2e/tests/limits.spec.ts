import { expect, RATE_LIMITED, test, toast } from './support'

/* The per-IP rate limits, run into on purpose. Last project (`limits`): it
 * leaves /login, /search and /api/random blocked for up to a minute. */

test.describe.configure({ mode: 'serial' })

test('too many sign-in attempts end on a page that says so', async ({ page }) => {
  await page.goto('/login')
  await expect(async () => {
    if (!page.url().endsWith('/login')) await page.goto('/login')
    await page.getByLabel('Benutzername').fill('admin')
    await page.getByLabel('Passwort').fill('wrong-password')
    await page.getByRole('button', { name: 'Anmelden' }).click()
    await expect(toast(page)).toContainText(RATE_LIMITED, { timeout: 1 })
  }).toPass({ intervals: [100], timeout: 60_000 })
  await expect(page.getByText('Zufallszitat')).toBeVisible() // a working page, not a redirect loop
})

test('too many searches end on a page that says so', async ({ page }) => {
  await page.goto('/search?q=life')
  await expect(async () => {
    const form = page.locator('.main-content form')
    if (!(await form.isVisible())) await page.goto('/search?q=life')
    await form.getByRole('searchbox').fill('love')
    await form.getByRole('button', { name: 'Suchen' }).click()
    await expect(toast(page)).toContainText(RATE_LIMITED, { timeout: 1 })
  }).toPass({ intervals: [100], timeout: 60_000 })
  await expect(page.getByText('Zufallszitat')).toBeVisible()
})

test('the API answers 429 with JSON once the limit is used up', async ({ request }) => {
  let res = await request.get('/api/random')
  for (let i = 0; i < 31 && res.status() === 200; i++) res = await request.get('/api/random')
  expect(res.status()).toBe(429)
  expect(await res.json()).toMatchObject({ status: 'error', detail: '30 per 1 minute' })
  expect(res.headers()['x-ratelimit-remaining']).toBe('0')
  expect(Number(res.headers()['retry-after'])).toBeGreaterThan(0)
})
