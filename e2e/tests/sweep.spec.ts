import { addQuotes, expect, heading, test, toast, uid, unlimited } from './support'
import type { Page } from '@playwright/test'

/* Breadth: every page route (flask routes; the JSON ones are in api.spec.ts)
 * as guest and as admin, in German and English. Each page must show its own
 * heading or landmark; the fixture fails on page errors, console errors (CSP)
 * and 5xx. Guests get a 302 to the login page for every admin route (checked
 * without following it: /login is rate-limited, auth.spec.ts follows one). */

const L = {
  de: {
    random: 'Zufallszitat', browse: 'Zitate durchsuchen', authors: /^Alle Autoren/, tags: /^Alle Tags/,
    search: 'Suche', results: /^Suchergebnisse für/, notFound: 'Keine Zitate gefunden.', more: /^Weitere Zitate von/,
    credits: 'Credits & Lizenzinformationen', user: 'Benutzername', dashboard: 'Admin-Dashboard',
    quotes: 'Zitate verwalten', add: 'Zitat hinzufügen', edit: /^Zitat bearbeiten #\d+/, missing: 'Zitat nicht gefunden.',
    adminTags: 'Tags verwalten', settings: 'Einstellungen', backup: 'Backup', author: 'Autor',
  },
  en: {
    random: 'Random Quote', browse: 'Browse Quotes', authors: /^All Authors/, tags: /^All Tags/,
    search: 'Search', results: /^Search results for/, notFound: 'No quotes found.', more: /^More quotes by/,
    credits: 'Credits & License Information', user: 'Username', dashboard: 'Admin Dashboard',
    quotes: 'Manage Quotes', add: 'Add Quote', edit: /^Edit Quote #\d+/, missing: 'Quote not found.',
    adminTags: 'Manage Tags', settings: 'Settings', backup: 'Backup', author: 'Author',
  },
}
type Labels = (typeof L)['de']

const PUBLIC: [string, (p: Page, l: Labels) => Promise<void>][] = [
  ['/', (p, l) => expect(p.getByText(l.random)).toBeVisible()],
  ['/browse', (p, l) => heading(p, l.browse)],
  ['/browse?sort=author_az&page=2', (p, l) => heading(p, l.browse)],
  ['/browse?author=Oscar Wilde', (p, l) => expect(p.getByText(`${l.author}: Oscar Wilde`)).toBeVisible()],
  ['/browse?tag=humor', (p) => expect(p.getByText('Tag: humor')).toBeVisible()],
  ['/browse/authors', (p, l) => heading(p, l.authors)],
  ['/browse/authors?letter=J', (p) => expect(p.getByRole('link', { name: /Johann Wolfgang von Goethe/ })).toBeVisible()],
  ['/browse/tags', (p, l) => heading(p, l.tags)],
  ['/browse/tags?page=2', (p, l) => heading(p, l.tags)],
  ['/search', (p, l) => heading(p, l.search)],
  ['/search?q=life', (p, l) => heading(p, l.results)],
  ['/quote/{id}', (p, l) => heading(p, l.more)],
  ['/quote/999999999', (p, l) => expect(p.getByText(l.notFound)).toBeVisible()],
  ['/credits', (p, l) => heading(p, l.credits)],
  ['/no-such-page', (p) => heading(p, '404')],
]

const ADMIN: [string, (p: Page, l: Labels) => Promise<void>][] = [
  ['/login', (p, l) => heading(p, l.dashboard)], // signed in: straight on to the dashboard
  ['/admin/', (p, l) => heading(p, l.dashboard)],
  ['/admin/quotes', (p, l) => heading(p, l.quotes)],
  ['/admin/quotes?q=Wilde', (p, l) => heading(p, l.quotes)],
  ['/admin/quotes/add', (p, l) => heading(p, l.add)],
  ['/admin/quotes/{id}/edit', (p, l) => heading(p, l.edit)],
  ['/admin/quotes/999999999/edit', (p, l) => expect(toast(p)).toContainText(l.missing)],
  ['/admin/tags', (p, l) => heading(p, l.adminTags)],
  ['/admin/tags?q=humor', (p, l) => heading(p, l.adminTags)],
  ['/admin/settings', (p, l) => heading(p, l.settings)],
  ['/admin/backup', (p, l) => heading(p, l.backup)],
]

const LIMITED = /^\/(login|search)\b/

async function visit(page: Page, path: string, check: () => Promise<void>): Promise<void> {
  const go = async () => {
    const res = await page.goto(path)
    expect(res!.status(), path).toBeLessThan(500)
  }
  if (LIMITED.test(path)) await unlimited(page, go)
  else await go()
  await check()
}

for (const lang of ['de', 'en'] as const) {
  const l = L[lang]

  test(`guest (${lang}): every public page renders, admin routes redirect to the login`, async ({ page, adminPage }) => {
    const [id] = await addQuotes(adminPage, [{ text: `Sweep ${uid()}`, author: 'Oscar Wilde' }])
    if (lang === 'en') await page.goto('/set-lang/en')
    for (const [path, check] of PUBLIC) await visit(page, path.replace('{id}', String(id)), () => check(page, l))
    await visit(page, '/login', () => expect(page.getByLabel(l.user)).toBeVisible())
    await visit(page, '/logout', () => expect(page.getByText(l.random)).toBeVisible())

    for (const [path] of ADMIN.slice(1)) {
      const res = await page.request.get(path.replace('{id}', String(id)), { maxRedirects: 0 })
      expect(res.status(), path).toBe(302)
      expect(res.headers().location, path).toMatch(/\/login\?next=/)
    }
  })

  test(`admin (${lang}): every page renders, public ones too`, async ({ adminPage: page }) => {
    const [id] = await addQuotes(page, [{ text: `Sweep ${uid()}`, author: 'Oscar Wilde' }])
    if (lang === 'en') await page.goto('/set-lang/en')
    for (const [path, check] of [...PUBLIC, ...ADMIN]) {
      await visit(page, path.replace('{id}', String(id)), () => check(page, l))
    }
    await page.goto('/logout')
    await expect(page.getByRole('link', { name: lang === 'de' ? 'Anmelden' : 'Login' })).toBeVisible()
  })
}
