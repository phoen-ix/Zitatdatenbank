import { addQuotes, expect, heading, notLimited, test, uid, unlimited } from './support'
import type { Page } from '@playwright/test'

/* Journeys through the public pages, as a guest in the default German UI
 * (the language switch has its own test). Quotes a test needs are added by
 * an admin next to it and carry a uid() word. */

const cards = (page: Page) => page.locator('.main-content .card')
const authorsOnPage = async (page: Page) =>
  (await page.locator('.main-content .card .quote-author').allInnerTexts()).map((a) => a.trim())
const pageInfo = (page: Page) => page.getByRole('navigation', { name: 'Seitennavigation' })

async function search(page: Page, q: string): Promise<void> {
  await unlimited(page, async () => {
    await page.goto('/')
    await page.getByRole('searchbox').fill(q)
    await page.getByRole('searchbox').press('Enter')
  })
}

test.describe('home', () => {
  test('the random quote card links to its detail page, author and tags', async ({ page }) => {
    // Quotes added by other tests may lack an author or tags: draw until one has both.
    await expect(async () => {
      await page.goto('/')
      await expect(page.locator('a.quote-author')).toBeVisible({ timeout: 1 })
      await expect(page.locator('.card-body a.badge').first()).toBeVisible({ timeout: 1 })
    }).toPass()
    const text = await page.locator('.quote-text').innerText()
    const author = (await page.locator('.quote-author').innerText()).trim()
    const tag = (await page.locator('.card-body a.badge').first().innerText()).trim()
    // The page draws a new quote on every load: follow its links by their targets.
    const authorUrl = await page.locator('.quote-author').getAttribute('href')
    const tagUrl = await page.locator('.card-body a.badge').first().getAttribute('href')

    await page.getByRole('link', { name: 'Zitatdetails' }).click()
    await expect(page).toHaveURL(/\/quote\/\d+$/)
    await expect(page.locator('.quote-text')).toHaveText(text, { useInnerText: true })
    await page.goto(authorUrl!)
    await expect(page.getByText(`Autor: ${author}`)).toBeVisible()
    await page.goto(tagUrl!)
    await expect(page.getByText(`Tag: ${tag}`)).toBeVisible()
  })

  test('"Neues Zitat" loads the page again, never from the cache', async ({ page }) => {
    const res = await page.goto('/')
    expect(res!.headers()['cache-control']).toBe('no-store')
    const reload = page.waitForResponse((r) => new URL(r.url()).pathname === '/' && r.status() === 200)
    await page.getByRole('link', { name: 'Neues Zitat' }).click()
    await reload
    await expect(page.locator('.quote-text')).not.toBeEmpty()
  })

  test('the totals count a new quote, author and tag at once', async ({ page, adminPage }) => {
    const total = async (label: string) => {
      const row = page.locator('.card-body .d-flex', { hasText: label })
      return Number((await row.locator('strong').innerText()).replace(/,/g, ''))
    }
    await page.goto('/')
    const before = [await total('Zitate gesamt'), await total('Autoren'), await total('Tags')]
    const w = uid()
    await addQuotes(adminPage, [{ text: `Totals ${w}`, author: `Author ${w}`, tags: `tag-${w}` }])
    await page.goto('/')
    expect(await total('Zitate gesamt')).toBeGreaterThan(before[0])
    expect(await total('Autoren')).toBeGreaterThan(before[1])
    expect(await total('Tags')).toBeGreaterThan(before[2])
  })

  test('the navigation, the quick links and the footer reach every section', async ({ page }) => {
    await page.goto('/credits')
    const nav = page.getByRole('navigation').first()
    for (const [link, check] of [
      ['Durchsuchen', () => heading(page, 'Zitate durchsuchen')],
      ['Autoren', () => heading(page, /^Alle Autoren/)],
      ['Tags', () => heading(page, /^Alle Tags/)],
      ['Startseite', () => expect(page.getByText('Zufallszitat')).toBeVisible()],
    ] as const) {
      await nav.getByRole('link', { name: link, exact: true }).click()
      await check()
    }
    await page.getByRole('link', { name: 'Zitate durchsuchen' }).click()
    await heading(page, 'Zitate durchsuchen')
    await page.goto('/')
    await page.getByRole('link', { name: 'Alle Autoren' }).click()
    await heading(page, /^Alle Autoren/)
    await page.goto('/')
    await page.getByRole('link', { name: 'Alle Tags' }).click()
    await heading(page, /^Alle Tags/)
    await page.getByRole('link', { name: 'Credits & Lizenz' }).click()
    await heading(page, 'Credits & Lizenzinformationen')
    await page.getByRole('link', { name: /Zitatdatenbank/ }).first().click() // the brand
    await expect(page.getByText('Zufallszitat')).toBeVisible()
  })

  test('on a phone the menu folds into the toggler', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/')
    const browse = page.getByRole('link', { name: 'Durchsuchen', exact: true })
    await expect(browse).toBeHidden()
    await page.getByRole('button', { name: 'Navigation umschalten' }).click()
    await browse.click()
    await heading(page, 'Zitate durchsuchen')
  })
})

test.describe('browse', () => {
  test('the sort menu orders newest, oldest, author A-Z and Z-A, keeping the tag filter', async ({ page, adminPage }) => {
    const w = uid()
    await addQuotes(adminPage, [
      { text: `Sort one ${w}`, author: `Mmm ${w}`, tags: w },
      { text: `Sort two ${w}`, author: `Aaa ${w}`, tags: w },
      { text: `Sort three ${w}`, author: `Zzz ${w}`, tags: w },
    ])
    await page.goto(`/browse?tag=${w}`)
    const sort = page.getByRole('combobox', { name: 'Sortieren nach' })
    await expect(sort).toHaveValue('newest')
    expect(await authorsOnPage(page)).toEqual([`Zzz ${w}`, `Aaa ${w}`, `Mmm ${w}`])
    for (const [value, order] of [
      ['oldest', ['Mmm', 'Aaa', 'Zzz']],
      ['author_az', ['Aaa', 'Mmm', 'Zzz']],
      ['author_za', ['Zzz', 'Mmm', 'Aaa']],
    ] as const) {
      await sort.selectOption(value)
      await expect(page).toHaveURL(new RegExp(`sort=${value}`))
      await expect(page).toHaveURL(new RegExp(`tag=${w}`))
      await expect(page.getByText(`Tag: ${w}`)).toBeVisible()
      expect(await authorsOnPage(page)).toEqual(order.map((a) => `${a} ${w}`))
    }
  })

  test('author and tag filters narrow the list; "Filter aufheben" clears them', async ({ page, adminPage }) => {
    const w = uid()
    await addQuotes(adminPage, [
      { text: `Filter one ${w}`, author: `Filtered ${w}`, tags: `ft-${w}, other-${w}` },
      { text: `Filter two ${w}`, author: `Filtered ${w}` },
      { text: `Filter three ${w}`, author: `Someone ${w}`, tags: `ft-${w}` },
    ])
    await page.goto(`/search?q=${w}`)
    await page.getByRole('link', { name: `Filtered ${w}` }).first().click()
    await expect(page.getByText(`Autor: Filtered ${w}`)).toBeVisible()
    await expect(cards(page)).toHaveCount(2)
    await page.getByRole('link', { name: `ft-${w}` }).click()
    await expect(page.getByText(`Tag: ft-${w}`)).toBeVisible()
    await expect(cards(page)).toHaveCount(2)
    expect(await authorsOnPage(page)).toEqual([`Someone ${w}`, `Filtered ${w}`])
    await page.getByRole('link', { name: 'Filter aufheben' }).click()
    await expect(page).toHaveURL(/\/browse$/)
    await expect(page.getByText(`Tag: ft-${w}`)).toBeHidden()
    await expect(page.getByText(/^\d+ Zitate$/)).toBeVisible()
  })

  test('a filter without matches says so', async ({ page }) => {
    await page.goto(`/browse?tag=${uid()}`)
    await expect(page.getByText('Keine Zitate gefunden.')).toBeVisible()
  })

  test('all quotes page with Weiter, Zurück and "Gehe zu Seite" (cursor pages)', async ({ page }) => {
    await page.goto('/browse')
    await expect(pageInfo(page)).toContainText(/Seite 1 \/ \d+/)
    const firstIds = await quoteIds(page)
    expect(firstIds).toHaveLength(20)
    await pageInfo(page).getByRole('link', { name: /Weiter/ }).click()
    await expect(pageInfo(page)).toContainText(/Seite 2 \/ \d+/)
    await expect(page).toHaveURL(/cursor=\d+/)
    const secondIds = await quoteIds(page)
    expect(Math.max(...secondIds)).toBeLessThan(Math.min(...firstIds))
    await pageInfo(page).getByRole('link', { name: /Zurück/ }).click()
    await expect(pageInfo(page)).toContainText(/Seite 1 \/ \d+/)
    expect(Math.min(...(await quoteIds(page)))).toBeGreaterThan(Math.max(...secondIds))
    await page.getByLabel('Gehe zu Seite').fill('3')
    await page.getByRole('button', { name: 'Los' }).click()
    await expect(pageInfo(page)).toContainText(/Seite 3 \/ \d+/)
    await expect(cards(page)).toHaveCount(20)
  })

  test('"Älteste zuerst" pages forward from the oldest quote', async ({ page }) => {
    await page.goto('/browse?sort=oldest')
    const firstIds = await quoteIds(page)
    expect(firstIds).toEqual([...firstIds].sort((a, b) => a - b))
    await pageInfo(page).getByRole('link', { name: /Weiter/ }).click()
    await expect(pageInfo(page)).toContainText(/Seite 2/)
    expect(Math.min(...(await quoteIds(page)))).toBeGreaterThan(Math.max(...firstIds))
  })

  test('a filtered list pages with numbered links', async ({ page }) => {
    await page.goto('/browse?tag=English')
    const nav = pageInfo(page)
    await expect(nav.getByRole('link', { name: '1', exact: true })).toBeVisible()
    const firstIds = await quoteIds(page)
    await nav.getByRole('link', { name: '2', exact: true }).click()
    await expect(page).toHaveURL(/page=2/)
    await expect(page).toHaveURL(/tag=English/)
    expect(Math.max(...(await quoteIds(page)))).toBeLessThan(Math.min(...firstIds))
    await nav.getByRole('link', { name: /Weiter/ }).click()
    await expect(page).toHaveURL(/page=3/)
    await nav.getByRole('link', { name: /Zurück/ }).click()
    await expect(page).toHaveURL(/page=2/)
  })
})

async function quoteIds(page: Page): Promise<number[]> {
  const hrefs = await page.locator('.main-content .card a[href^="/quote/"]').evaluateAll((as) => as.map((a) => a.getAttribute('href')!))
  return hrefs.map((h) => Number(h.split('/').pop()))
}

test.describe('authors and tags', () => {
  test('the letter bar filters the authors; "Alle" shows them all; an author opens their quotes', async ({ page }) => {
    await page.goto('/browse/authors')
    const total = Number((await page.getByRole('heading', { name: /^Alle Autoren/ }).innerText()).match(/\((\d+)\)/)![1])
    await page.getByRole('link', { name: 'G', exact: true }).click()
    await expect(page).toHaveURL(/letter=G/)
    const names = await page.locator('.list-group-item').allInnerTexts()
    expect(names.length).toBeGreaterThan(0)
    for (const n of names) expect(n.trim()).toMatch(/^G/i)
    expect(names.length).toBeLessThan(total)
    await page.getByRole('link', { name: 'Alle', exact: true }).click()
    await expect(page.getByRole('heading', { name: `Alle Autoren (${total})` })).toBeVisible()
    await page.getByRole('link', { name: /Johann Wolfgang von Goethe/ }).click()
    await expect(page.getByText('Autor: Johann Wolfgang von Goethe')).toBeVisible()
  })

  test('more than 50 authors under one letter page with Weiter and "Gehe zu Seite"', async ({ page, adminPage }) => {
    const w = uid()
    await addQuotes(adminPage, Array.from({ length: 51 }, (_, i) => ({ text: `Pager ${i}`, author: `Q${w} ${String(i).padStart(2, '0')}` })))
    await page.goto('/browse/authors?letter=Q')
    const nav = pageInfo(page)
    await expect(nav).toContainText(/Seite 1 \/ [2-9]/)
    await expect(page.locator('.list-group-item')).toHaveCount(50)
    await nav.getByRole('link', { name: /Weiter/ }).click()
    await expect(nav).toContainText(/Seite 2 \//)
    await expect(page).toHaveURL(/letter=Q/)
    await nav.getByRole('link', { name: /Zurück/ }).click()
    await expect(nav).toContainText(/Seite 1 \//)
    await page.getByLabel('Gehe zu Seite').fill('2')
    await page.getByRole('button', { name: 'Los' }).click()
    await expect(nav).toContainText(/Seite 2 \//)
    await expect(page).toHaveURL(/letter=Q/)
  })

  test('the tag index counts quotes per tag, pages, and opens a tag', async ({ page }) => {
    await page.goto('/browse/tags')
    const nav = pageInfo(page)
    await expect(nav).toContainText(/Seite 1 \/ \d+/)
    const counts = (await page.locator('.list-group-item .badge').allInnerTexts()).map(Number)
    expect(counts).toEqual([...counts].sort((a, b) => b - a)) // most-used first
    await nav.getByRole('link', { name: /Weiter/ }).click()
    await expect(nav).toContainText(/Seite 2 \//)
    await page.getByLabel('Gehe zu Seite').fill('1')
    await page.getByRole('button', { name: 'Los' }).click()
    await expect(nav).toContainText(/Seite 1 \//)
    const humor = page.locator('.list-group-item', { hasText: /^\s*humor\s/ })
    const n = Number(await humor.locator('.badge').innerText())
    await humor.click()
    await expect(page.getByText('Tag: humor')).toBeVisible()
    await expect(cards(page)).toHaveCount(Math.min(n, 20))
  })
})

test.describe('search', () => {
  test('the navbar search finds a quote by a word of its text, its author or its tag', async ({ page, adminPage }) => {
    const w = uid()
    const a = uid()
    const t = uid()
    await addQuotes(adminPage, [
      { text: `Searchable text ${w}`, author: `Writer ${a}` },
      { text: `Tagged one ${uid()}`, tags: t },
    ])
    await search(page, w)
    await heading(page, `Suchergebnisse für "${w}"`)
    await expect(page.getByRole('searchbox').first()).toHaveValue(w) // the navbar keeps the query
    await expect(page.locator('.quote-text')).toHaveText(`Searchable text ${w}`)
    await search(page, a)
    await expect(page.locator('.quote-author')).toHaveText(`Writer ${a}`)
    await search(page, t)
    await expect(page.locator('.quote-text')).toContainText('Tagged one')
  })

  test('the search page has its own form; no hits and an empty query say so', async ({ page }) => {
    const form = page.locator('.main-content form')
    await unlimited(page, async () => {
      await page.goto('/search')
      await notLimited(page)
      await heading(page, 'Suche')
      await expect(page.locator('.alert')).toBeHidden()
      await form.getByRole('searchbox').fill(uid())
      await form.getByRole('button', { name: 'Suchen' }).click()
    })
    await expect(page.getByText('Keine Ergebnisse gefunden.')).toBeVisible()
  })

  test('more than 20 hits page with numbered links, and only to pages that exist', async ({ page, adminPage }) => {
    const w = uid()
    await addQuotes(adminPage, Array.from({ length: 21 }, (_, i) => ({ text: `Many hits ${i} ${w}` })))
    await search(page, w)
    await expect(cards(page)).toHaveCount(20)
    await expect(page.locator('.quote-text').first()).toHaveText(`Many hits 0 ${w}`) // oldest first
    const nav = pageInfo(page)
    await expect(nav.getByRole('link')).toHaveText([/Zurück/, '1', '2', /Weiter/])
    const second = await nav.getByRole('link', { name: '2', exact: true }).getAttribute('href')
    await unlimited(page, () => page.goto(second!))
    await expect(cards(page)).toHaveCount(1)
    await expect(page.locator('.quote-text')).toHaveText(`Many hits 20 ${w}`)
    await expect(nav.getByRole('link')).toHaveText([/Zurück/, '1', '2', /Weiter/])
  })

  test('FULLTEXT operators and markup in a query are plain text', async ({ page, adminPage }) => {
    const w = uid()
    await addQuotes(adminPage, [{ text: `Operators ${w}` }])
    await search(page, `+${w}* -"(nothing)" ~@<>`)
    await expect(page.locator('.quote-text', { hasText: w })).toHaveText(`Operators ${w}`)
    await search(page, '<img src=x onerror=alert(1)>')
    await heading(page, 'Suchergebnisse für "<img src=x onerror=alert(1)>"')
    await search(page, '%_')
    await expect(page.getByText('Keine Ergebnisse gefunden.')).toBeVisible()
  })
})

test.describe('quote detail', () => {
  test('shows text, author, tags, number, more quotes by the author, and a way back', async ({ page, adminPage }) => {
    const w = uid()
    const [first, second] = await addQuotes(adminPage, [
      { text: `First line ${w} // second line`, author: `Detail ${w}`, tags: `dt-${w}` },
      { text: `Another one ${uid()}`, author: `Detail ${w}` },
    ])
    await page.goto(`/quote/${first}`)
    await expect(page.locator('.quote-text')).toHaveText(`First line ${w}\nsecond line`, { useInnerText: true })
    await expect(page.locator('.quote-text br')).toHaveCount(1) // ` // ` is a line break
    await expect(page.getByText(`Nr. ${first}`)).toBeVisible()
    await heading(page, `Weitere Zitate von Detail ${w}`)
    await page.getByRole('link', { name: /^Another one/ }).click()
    await expect(page).toHaveURL(new RegExp(`/quote/${second}$`))
    await page.getByRole('link', { name: `Detail ${w}` }).click()
    await expect(page.getByText(`Autor: Detail ${w}`)).toBeVisible()
    await page.goto(`/quote/${first}`)
    await page.getByRole('link', { name: `dt-${w}` }).click()
    await expect(page.getByText(`Tag: dt-${w}`)).toBeVisible()
    await page.goto(`/quote/${first}`)
    await page.getByRole('link', { name: 'Zurück zur Übersicht' }).click()
    await heading(page, 'Zitate durchsuchen')
  })

  test('a quote without author says "Unbekannt"; markup in a quote stays text', async ({ page, adminPage }) => {
    const w = uid()
    const [id] = await addQuotes(adminPage, [{ text: `<b>bold</b> <script>alert(1)</script> ${w}` }])
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.quote-author')).toHaveText('Unbekannt')
    await expect(page.locator('.quote-text')).toHaveText(`<b>bold</b> <script>alert(1)</script> ${w}`)
    await expect(page.locator('.quote-text b')).toHaveCount(0)
  })

  test('an unknown quote number is a 404 with a message', async ({ page }) => {
    const res = await page.goto('/quote/999999999')
    expect(res!.status()).toBe(404)
    await expect(page.getByText('Keine Zitate gefunden.')).toBeVisible()
  })
})

test('credits name both sources and licences, links open in a new tab', async ({ page }) => {
  await page.goto('/credits')
  await heading(page, 'Credits & Lizenzinformationen')
  await expect(page.getByText('Zitate mit den Tags "English", "Englisch", "Source: Kaggle"')).toBeVisible()
  for (const name of [/datenbörse\.net/, /kaggle\.com/, /Creative Commons BY-SA 3\.0/, /CC0 1\.0 Universal/]) {
    const link = page.getByRole('link', { name })
    await expect(link).toHaveAttribute('target', '_blank')
    await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  }
})

test('an unknown page is a 404 with a way home', async ({ page }) => {
  const res = await page.goto('/no-such-page')
  expect(res!.status()).toBe(404)
  await expect(page.getByText('Seite nicht gefunden.')).toBeVisible()
  await page.getByRole('link', { name: 'Startseite' }).last().click()
  await expect(page.getByText('Zufallszitat')).toBeVisible()
})

test('the language switch keeps the page and lasts for the session', async ({ page }) => {
  await page.goto('/browse/authors')
  await expect(page.locator('html')).toHaveAttribute('lang', 'de')
  await page.getByRole('link', { name: 'EN', exact: true }).click()
  await expect(page).toHaveURL(/\/browse\/authors$/)
  await heading(page, /^All Authors/)
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
  await page.getByRole('link', { name: 'Browse', exact: true }).click()
  await heading(page, 'Browse Quotes')
  await page.goto('/credits')
  await expect(page.getByText('Quotes tagged with "English", "Englisch", "Source: Kaggle"')).toBeVisible()
  await page.getByRole('link', { name: 'DE', exact: true }).click()
  await heading(page, 'Credits & Lizenzinformationen')
  await page.goto('/set-lang/fr')
  await expect(page.locator('html')).toHaveAttribute('lang', 'de') // unknown languages are ignored
})
