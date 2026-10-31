import { randomInt } from 'node:crypto'
import path from 'node:path'

import { expect, test as base, type APIRequestContext, type APIResponse, type BrowserContext, type Page } from '@playwright/test'

import { ADMIN_PASSWORD, ADMIN_USERNAME } from '../docs/seed'

export { expect, ADMIN_PASSWORD, ADMIN_USERNAME }

/** The admin's signed-in browser state, written by auth.setup.ts. */
export const ADMIN_STATE = path.join(import.meta.dirname, '../.auth/admin.json')

/** A word only this test uses: letters and digits, so MariaDB's FULLTEXT index finds it. */
export const uid = (): string => `zq${Date.now().toString(36)}${randomInt(36 ** 5).toString(36)}`

export const RATE_LIMITED = /Zu viele Anfragen|Too many requests/

/** Every page of a test is watched: an uncaught error, a console error (CSP
 * violations land there), a 5xx response or a failed subresource fails the
 * test. The console's "Failed to load resource" lines are the responses. */
function watch(context: BrowserContext, problems: string[]): void {
  const page = (p: Page) => {
    p.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`))
    p.on('console', (m) => {
      if (m.type() === 'error' && !m.text().startsWith('Failed to load resource')) problems.push(`console: ${m.text()}`)
    })
    p.on('response', (r) => {
      // 4xx only for what a page loads itself (CSS, JS, fonts, icons): a test may well ask for a 404 page.
      if (r.status() >= 500 || (r.status() >= 400 && r.request().resourceType() !== 'document'))
        problems.push(`HTTP ${r.status()} ${r.url()}`)
    })
  }
  context.pages().forEach(page)
  context.on('page', page)
}

export const test = base.extend<{ problems: string[]; adminPage: Page }>({
  problems: [
    async ({ context }, use) => {
      const problems: string[] = []
      watch(context, problems)
      await use(problems)
      expect(problems).toEqual([])
    },
    { auto: true },
  ],
  /** A second, signed-in browser next to the test's guest `page`. */
  adminPage: async ({ browser, baseURL, problems }, use) => {
    const ctx = await browser.newContext({ baseURL, storageState: ADMIN_STATE })
    watch(ctx, problems)
    await use(await ctx.newPage())
    await ctx.close()
  },
})

/** /login (10 a minute) and /search (30 a minute) are rate-limited per IP, and
 * every browser of the run shares one. A limited request lands on another page
 * with the "too many requests" toast: wait the window out and run `action` again. */
export async function unlimited(page: Page, action: () => Promise<unknown>): Promise<void> {
  await expect(async () => {
    await action()
    await notLimited(page)
  }).toPass({ intervals: [5_000], timeout: 90_000 })
}

/** Inside an unlimited() action: give up this try at once if the last request was limited. */
export const notLimited = (page: Page) => expect(page.locator('#toastContainer')).not.toContainText(RATE_LIMITED, { timeout: 100 })

/** Sign in on the login page `page` is about to open (`url`, or a protected page that redirects there). */
export async function login(page: Page, url = '/login', password = ADMIN_PASSWORD): Promise<void> {
  await unlimited(page, async () => {
    await page.goto(url)
    await notLimited(page)
    await page.getByLabel('Benutzername').fill(ADMIN_USERNAME)
    await page.getByLabel('Passwort').fill(password)
    await page.getByRole('button', { name: 'Anmelden' }).click()
  })
}

export interface NewQuote {
  text: string
  author?: string
  tags?: string
}

/** Adds quotes through the admin form's own POST (CSRF token from the page),
 * from a signed-in page. Returns their ids, found by the admin search for the
 * text's uid() word (NaN for a text without one). */
export async function addQuotes(admin: Page, quotes: NewQuote[]): Promise<number[]> {
  await admin.goto('/admin/quotes/add')
  return admin.evaluate(async (quotes) => {
    const token = document.querySelector<HTMLMetaElement>('meta[name=csrf-token]')!.content
    const ids: number[] = []
    for (const q of quotes) {
      const body = new URLSearchParams({ csrf_token: token, text: q.text, author: q.author ?? '', tags: q.tags ?? '' })
      const res = await fetch('/admin/quotes/add', { method: 'POST', body })
      if (!res.ok || !res.url.endsWith('/admin/quotes')) throw new Error(`add quote: HTTP ${res.status} ${res.url}`)
      const word = q.text.split(/\s+/).find((w) => /^zq[a-z0-9]+$/.test(w))
      if (!word) {
        ids.push(NaN)
        continue
      }
      const list = new DOMParser().parseFromString(await (await fetch(`/admin/quotes?q=${word}`)).text(), 'text/html')
      ids.push(Number(list.querySelector('tbody tr td')!.textContent))
    }
    return ids
  }, quotes)
}

/** GET a rate-limited API route (30 a minute per IP), waiting a 429 out like a polite client. */
export async function apiGet(request: APIRequestContext, url: string, params?: Record<string, string>): Promise<APIResponse> {
  let res!: APIResponse
  await expect(async () => {
    res = await request.get(url, { params })
    expect(res.status()).not.toBe(429)
  }).toPass({ intervals: [5_000], timeout: 90_000 })
  return res
}

export const heading = (page: Page, name: string | RegExp) =>
  expect(page.getByRole('heading', { name }).first()).toBeVisible()

export const toast = (page: Page) => page.locator('#toastContainer')
