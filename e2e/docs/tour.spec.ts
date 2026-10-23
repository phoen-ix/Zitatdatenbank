import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, test, type Browser, type BrowserContext, type Page, type TestInfo } from '@playwright/test'

import { ADMIN_PASSWORD, ADMIN_USERNAME, apiQuotes, backdateBackups, seedQuotes } from './seed'

/* The docs tour: one screenshot per screen (docs/screenshots/README.md is the
 * gallery) of the demo database in ./seed.ts, English UI plus a German hero.
 * Run it through scripts/docs-screenshots.sh.
 *
 * It is ALSO a render check: every test asserts something page-specific
 * before it shoots, and a page that throws fails the test.
 *
 * Determinism: the home page's random quote comes from the docs stack's seeded
 * gunicorn worker (e2e/docs/gunicorn_seed.py): the 3rd-5th home-page visits
 * below show the quotes the seed was picked for. Keep that order (new visits
 * go after them). The animated
 * themes type their quotes with setTimeout and place particles with
 * Math.random: every page runs on Playwright's clock (fast-forwarded before
 * the shot) and a seeded Math.random. */

const OUT = path.resolve(
  process.env.DOCS_SCREENSHOT_DIR ?? fileURLToPath(new URL('../../docs/screenshots', import.meta.url)),
)
mkdirSync(OUT, { recursive: true })

const FIXED_TIME = new Date('2026-06-15T10:00:00+02:00')
const THEMES = [
  'klassisch', 'modern', 'dunkel', 'wald', 'ozean',
  'hacker', 'typewriter', 'neon', 'pergament', 'vaporwave', 'aurora', 'unterwasser', 'kosmos', 'feuer',
]

let guest: BrowserContext
let guestDe: BrowserContext
let admin: BrowserContext
let pageErrors: Error[] = []
const opened: Page[] = []
let wildeId: number
let twainId: number

test.beforeAll(async ({ browser }, info) => {
  const baseURL = info.project.use.baseURL!
  await seedQuotes(baseURL)
  const [wilde] = (await apiQuotes(baseURL, { author: 'Oscar Wilde', per_page: '100' }))
    .filter((q) => q.text.startsWith('To live is the rarest thing'))
  const [twain] = (await apiQuotes(baseURL, { author: 'Mark Twain', per_page: '100' }))
    .filter((q) => q.text.startsWith('Good friends, good books'))
  wildeId = wilde.id
  twainId = twain.id

  guestDe = await newContext(browser, info.project.use)
  guest = await newContext(browser, info.project.use)
  admin = await newContext(browser, info.project.use)
  for (const ctx of [guest, admin]) {
    const page = await ctx.newPage()
    await page.goto('/set-lang/en')
    await expect(page.getByRole('link', { name: 'Browse', exact: true })).toBeVisible()
    await page.close()
  }
  const page = await admin.newPage()
  await page.goto('/login')
  await page.fill('#username', ADMIN_USERNAME)
  await page.fill('#password', ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Login', exact: true }).click()
  await expect(page).toHaveURL(/\/admin\/$/)
  await page.close()
})

test.afterAll(async () => {
  await setTheme('klassisch')
  for (const ctx of [guest, guestDe, admin]) await ctx.close()
})

test.beforeEach(() => {
  pageErrors = []
})

test.afterEach(async () => {
  for (const p of opened.splice(0)) await p.close()
  expect(pageErrors.map((e) => e.message)).toEqual([])
})

async function newContext(
  browser: Browser,
  u: TestInfo['project']['use'],
  viewport = u.viewport,
): Promise<BrowserContext> {
  const ctx = await browser.newContext({
    baseURL: u.baseURL,
    viewport,
    deviceScaleFactor: u.deviceScaleFactor,
    locale: u.locale,
    timezoneId: u.timezoneId,
    userAgent: u.userAgent,
    ...u.contextOptions,
  })
  // Seeded Math.random (mulberry32) for the particle themes.
  await ctx.addInitScript(() => {
    let s = 20260615
    Math.random = () => {
      s = (s + 0x6d2b79f5) | 0
      let t = Math.imul(s ^ (s >>> 15), 1 | s)
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296
    }
  })
  // The clock is the context's; every page shares it.
  await ctx.clock.install({ time: FIXED_TIME })
  return ctx
}

/** A page in that context. */
async function open(ctx: BrowserContext, url: string): Promise<Page> {
  const page = await ctx.newPage()
  opened.push(page)
  page.on('pageerror', (e) => pageErrors.push(e))
  await page.goto(url)
  return page
}

/** `clipAbove`: the page from the top down to just above that element.
 * `fit`: the viewport down to just above the first of these elements that the
 * viewport's bottom edge cuts. `fullPage` stops at 2400 CSS px. `clipX`: only that element's width (+8 px
 * each side) - keeps the gradient-heavy theme shots under 400 KB. */
async function shoot(
  page: Page,
  name: string,
  opts: { fullPage?: boolean; clipAbove?: string; fit?: string; clipX?: string } = {},
): Promise<void> {
  // Finishes the typing animation and lets toasts time out.
  await page.clock.runFor(60_000)
  await page.evaluate(() => document.fonts.ready)
  await expect(page.locator('.toast.show, .toast.showing')).toHaveCount(0)
  await expect(page.locator('.typing-cursor:visible')).toHaveCount(0)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.mouse.move(0, 0)
  const width = page.viewportSize()!.width
  let clip: { x: number; y: number; width: number; height: number } | undefined
  if (opts.clipAbove) {
    const box = await page.locator(opts.clipAbove).first().boundingBox()
    if (!box) throw new Error(`[docs] ${opts.clipAbove} is not on the page`)
    clip = { x: 0, y: 0, width, height: Math.min(2400, Math.floor(box.y) - 8) }
  } else if (opts.fit) {
    const vh = page.viewportSize()!.height
    const tops = await page.locator(opts.fit).evaluateAll(
      (els, vh) => els.map((e) => e.getBoundingClientRect()).filter((r) => r.bottom > vh).map((r) => r.top),
      vh,
    )
    clip = { x: 0, y: 0, width, height: Math.floor(Math.min(vh, ...tops)) }
  } else if (opts.fullPage) {
    const height = await page.evaluate(() => document.documentElement.scrollHeight)
    clip = { x: 0, y: 0, width, height: Math.min(2400, height) }
  }
  if (clip && opts.clipX) {
    const box = await page.locator(opts.clipX).first().boundingBox()
    if (!box) throw new Error(`[docs] ${opts.clipX} is not on the page`)
    clip.x = Math.max(0, Math.floor(box.x) - 8)
    clip.width = Math.min(width - clip.x, Math.ceil(box.width) + 16)
  }
  await page.screenshot({
    path: path.join(OUT, `${name}.png`),
    animations: 'disabled',
    caret: 'hide',
    fullPage: Boolean(clip),
    clip,
  })
}

const heading = (page: Page, name: string | RegExp) =>
  expect(page.getByRole('heading', { name }).first()).toBeVisible()

/* --- public pages ------------------------------------------------------- */

test('home (German hero)', async () => {
  const page = await open(guestDe, '/')
  await expect(page.getByText('Zufallszitat')).toBeVisible()
  await expect(page.locator('.quote-text')).toContainText('Alles wiederholt sich im Leben')
  await shoot(page, 'public-home.de')
})

test('home', async () => {
  const page = await open(guest, '/')
  await expect(page.getByText('Random Quote')).toBeVisible()
  await expect(page.locator('.quote-text')).toContainText('Life is like riding a bicycle')
  await shoot(page, 'public-home')
})

test('home on a phone', async ({ browser }, info) => {
  const ctx = await newContext(browser, info.project.use, { width: 390, height: 844 })
  try {
    const page = await open(ctx, '/set-lang/en')
    await expect(page.getByText('Random Quote')).toBeVisible()
    await expect(page.locator('.navbar-toggler')).toBeVisible()
    await expect(page.locator('.quote-text')).toContainText('Instead of cursing the darkness')
    await shoot(page, 'public-home.mobile', { fullPage: true })
  } finally {
    await ctx.close()
  }
})

test('browse', async () => {
  const page = await open(guest, '/browse')
  await heading(page, 'Browse Quotes')
  await expect(page.locator('.quote-text').first()).toBeVisible()
  await shoot(page, 'public-browse', { fit: '.card' })
})

test('browse by tag', async () => {
  const page = await open(guest, '/browse?tag=humor')
  await heading(page, 'Browse Quotes')
  await expect(page.locator('.quote-text').first()).toBeVisible()
  await shoot(page, 'public-browse-tag', { clipAbove: 'body > footer' })
})

test('authors', async () => {
  const page = await open(guest, '/browse/authors')
  await heading(page, /All Authors/)
  await expect(page.getByRole('link', { name: /Johann Wolfgang von Goethe/ })).toBeVisible()
  await shoot(page, 'public-authors')
})

test('tags', async () => {
  const page = await open(guest, '/browse/tags')
  await heading(page, /All Tags/)
  await expect(page.getByRole('link', { name: /inspirational/ }).first()).toBeVisible()
  await shoot(page, 'public-tags')
})

test('search', async () => {
  const page = await open(guest, '/search?q=life')
  await heading(page, /Search results for/)
  await expect(page.locator('.quote-text').first()).toBeVisible()
  await shoot(page, 'public-search', { fit: '.card' })
})

test('search without results', async () => {
  const page = await open(guest, '/search?q=xylophone')
  await expect(page.getByText('No results found.')).toBeVisible()
  await shoot(page, 'public-search-empty', { clipAbove: 'body > footer' })
})

test('quote detail', async () => {
  const page = await open(guest, `/quote/${wildeId}`)
  await heading(page, 'More quotes by Oscar Wilde')
  await shoot(page, 'public-quote')
})

test('credits', async () => {
  const page = await open(guest, '/credits')
  await heading(page, 'Credits & License Information')
  await shoot(page, 'public-credits', { fullPage: true })
})

test('page not found', async () => {
  const page = await open(guest, '/no-such-page')
  await heading(page, '404')
  await shoot(page, 'error-404', { clipAbove: 'body > footer' })
})

test('login', async () => {
  const page = await open(guest, '/login')
  await expect(page.locator('#username')).toBeVisible()
  await shoot(page, 'auth-login', { clipAbove: 'body > footer' })
})

/* --- admin -------------------------------------------------------------- */

test('admin dashboard', async () => {
  const page = await open(admin, '/admin/')
  await heading(page, 'Admin Dashboard')
  await shoot(page, 'admin-dashboard', { fullPage: true })
})

test('admin quotes', async () => {
  const page = await open(admin, '/admin/quotes')
  await heading(page, 'Manage Quotes')
  await expect(page.locator('table tbody tr').first()).toBeVisible()
  await shoot(page, 'admin-quotes', { fit: 'tbody tr' })
})

test('admin edit quote', async () => {
  const page = await open(admin, `/admin/quotes/${twainId}/edit`)
  await heading(page, `Edit Quote #${twainId}`)
  await expect(page.locator('#text')).toHaveValue(/Good friends, good books/)
  await shoot(page, 'admin-quote-edit', { clipAbove: 'body > footer' })
})

test('admin tags', async () => {
  const page = await open(admin, '/admin/tags')
  await heading(page, 'Manage Tags')
  await shoot(page, 'admin-tags', { fit: 'tbody tr' })
})

test('admin settings', async () => {
  const page = await open(admin, '/admin/settings')
  await heading(page, 'Settings')
  await expect(page.locator('#site_name')).toHaveValue('Zitatdatenbank')
  await shoot(page, 'admin-settings', { clipAbove: 'body > footer' })
})

test('admin settings: themes', async () => {
  const page = await open(admin, '/admin/settings')
  await page.getByRole('tab', { name: 'Themes' }).click()
  await expect(page.locator('#theme_klassisch')).toBeChecked()
  await expect(page.locator('#color_navbar')).toHaveValue('#6b4c3b')
  await shoot(page, 'admin-settings-themes', { fullPage: true })
})

test('admin backup', async () => {
  const page = await open(admin, '/admin/backup')
  await heading(page, 'Backup')
  if (await page.getByText('No backups available.').isVisible()) {
    await page.getByRole('button', { name: 'Create Backup' }).click()
    await expect(page.locator('table code').first()).toBeVisible()
  }
  backdateBackups()
  await page.goto('/admin/backup')
  await expect(page.getByText('zitate_backup_2026_06_15_08-00-00.tar.gz').first()).toBeVisible()
  await shoot(page, 'admin-backup', { clipAbove: 'body > footer' })
})

/* --- theme gallery (last: it switches the site's theme) ------------------ */

async function setTheme(key: string): Promise<void> {
  const page = await open(admin, '/admin/settings')
  await page.getByRole('tab', { name: 'Themes' }).click()
  await page.locator(`#theme_${key}`).check()
  await page.locator('#themeForm button[type=submit]').click()
  await expect(page.locator('#toastContainer')).toContainText('Settings saved.')
}

for (const key of THEMES) {
  test(`theme: ${key}`, async () => {
    await setTheme(key)
    const page = await open(guest, `/quote/${wildeId}`)
    await heading(page, 'More quotes by Oscar Wilde')
    if (THEMES.indexOf(key) >= 5) await expect(page.locator('body')).toHaveClass(`theme-${key}`)
    // Navbar and the quote card: enough to show the theme, small enough for 14 PNGs.
    await shoot(page, `theme-${key}`, { clipAbove: 'h4', clipX: '.main-content > .card' })
  })
}
