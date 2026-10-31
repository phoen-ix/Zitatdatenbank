import { addQuotes, ADMIN_STATE, expect, heading, test, toast, uid } from './support'
import type { Page } from '@playwright/test'

/* The admin's quote and tag management (German UI). Settings, themes and
 * backups change the whole site: global.spec.ts. */

test.use({ storageState: ADMIN_STATE })

const row = (page: Page, text: string | RegExp) => page.locator('tbody tr', { hasText: text })
const pageNav = (page: Page) => page.getByRole('navigation', { name: 'Seitennavigation' })
const main = (page: Page) => page.locator('.main-content')

test('the dashboard counts quotes, authors and tags and links to every admin page', async ({ page }) => {
  const w = uid()
  await addQuotes(page, [{ text: `Recent ${w}` }])
  await page.goto('/admin/')
  await heading(page, 'Admin-Dashboard')
  for (const label of ['Zitate gesamt', 'Autoren', 'Tags']) {
    await expect(page.locator('.card', { hasText: label }).getByRole('heading')).toHaveText(/^[\d,]+$/)
  }
  await page.getByRole('link', { name: new RegExp(`Recent ${w}`) }).click()
  await heading(page, /^Zitat bearbeiten #\d+/)
  for (const [link, title] of [
    ['Zitat hinzufügen', 'Zitat hinzufügen'],
    ['Zitate verwalten', 'Zitate verwalten'],
    ['Tags verwalten', 'Tags verwalten'],
    ['Einstellungen', 'Einstellungen'],
    ['Backup', 'Backup'],
  ]) {
    await page.goto('/admin/')
    await page.getByRole('link', { name: link, exact: true }).click()
    await heading(page, title)
  }
  await page.getByRole('link', { name: 'Verwaltung' }).click()
  await heading(page, 'Admin-Dashboard')
})

test.describe('quotes', () => {
  test('add a quote with author and tags; it shows in the list and on the site', async ({ page }) => {
    const w = uid()
    await page.goto('/admin/quotes')
    await page.getByRole('link', { name: 'Zitat hinzufügen' }).click()
    await heading(page, 'Zitat hinzufügen')
    await page.getByLabel('Zitattext').fill(`Added in the form ${w}`)
    await page.getByLabel('Autor').fill(`Former ${w}`)
    await page.getByLabel('Tags').fill(` one-${w},two-${w} , one-${w},, `)
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(page).toHaveURL(/\/admin\/quotes$/)
    await expect(toast(page)).toContainText('Gespeichert.')
    const r = row(page, `Added in the form ${w}`)
    await expect(r).toContainText(`Former ${w}`)
    await expect(r.locator('.badge')).toHaveText([`one-${w}`, `two-${w}`])
    const id = await r.locator('td').first().innerText()
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.quote-text')).toHaveText(`Added in the form ${w}`)
    await expect(page.locator('.card-body a.badge')).toHaveText([`one-${w}`, `two-${w}`])
  })

  test('a quote needs its text: empty is blocked, blank is refused and the form keeps the rest', async ({ page }) => {
    const w = uid()
    await page.goto('/admin/quotes/add')
    await page.getByLabel('Autor').fill(`Kept ${w}`)
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(page.getByLabel('Zitattext')).toHaveJSProperty('validity.valueMissing', true)
    await expect(page).toHaveURL(/\/admin\/quotes\/add$/)

    await page.getByLabel('Zitattext').fill('   ')
    await page.getByLabel('Tags').fill(`kept-${w}`)
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(toast(page)).toContainText('Der Zitattext fehlt.')
    await expect(page.getByLabel('Autor')).toHaveValue(`Kept ${w}`)
    await expect(page.getByLabel('Tags')).toHaveValue(`kept-${w}`)
    await page.goto(`/admin/quotes?q=Kept ${w}`)
    await expect(page.locator('tbody tr')).toHaveCount(0)
  })

  test('edit a quote: new text, author and tags; a blank text keeps the old one', async ({ page }) => {
    const w = uid()
    const [id] = await addQuotes(page, [{ text: `Before ${w}`, author: `Old ${w}`, tags: `keep-${w}, drop-${w}` }])
    await page.goto(`/admin/quotes?q=${w}`)
    await row(page, `Before ${w}`).getByRole('link', { name: 'Bearbeiten' }).click()
    await heading(page, `Zitat bearbeiten #${id}`)
    await expect(page.getByLabel('Tags')).toHaveValue(`keep-${w}, drop-${w}`)

    await page.getByLabel('Zitattext').fill(' ')
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(toast(page)).toContainText('Der Zitattext fehlt.')

    await page.getByLabel('Zitattext').fill(`After ${w}`)
    await page.getByLabel('Autor').fill(`New ${w}`)
    await page.getByLabel('Tags').fill(`keep-${w}, add-${w}`)
    await page.getByRole('button', { name: 'Speichern' }).click()
    await expect(toast(page)).toContainText('Gespeichert.')
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.quote-text')).toHaveText(`After ${w}`)
    await expect(page.locator('.quote-author')).toHaveText(`New ${w}`)
    await expect(page.locator('.card-body a.badge')).toHaveText([`keep-${w}`, `add-${w}`])
  })

  test('"Abbrechen" leaves a quote as it was', async ({ page }) => {
    const w = uid()
    const [id] = await addQuotes(page, [{ text: `Untouched ${w}` }])
    await page.goto(`/admin/quotes/${id}/edit`)
    await page.getByLabel('Zitattext').fill(`Changed ${w}`)
    await page.getByRole('link', { name: 'Abbrechen' }).click()
    await heading(page, 'Zitate verwalten')
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.quote-text')).toHaveText(`Untouched ${w}`)
  })

  test('delete a quote after one confirmation; dismissing it keeps the quote', async ({ page }) => {
    const w = uid()
    const [id] = await addQuotes(page, [{ text: `Doomed ${w}` }])
    await page.goto(`/admin/quotes?q=${w}`)
    const dialogs: string[] = []
    page.on('dialog', (d) => {
      dialogs.push(d.message())
      return dialogs.length === 1 ? d.dismiss() : d.accept()
    })
    await row(page, w).getByRole('button', { name: 'Löschen' }).click()
    await expect(row(page, w)).toBeVisible()
    expect(dialogs).toEqual(['Wirklich löschen?'])

    await row(page, w).getByRole('button', { name: 'Löschen' }).click()
    await expect(toast(page)).toContainText('Zitat gelöscht.')
    expect(dialogs).toHaveLength(2) // once per click
    expect((await page.goto(`/quote/${id}`))!.status()).toBe(404)
  })

  test('the admin search finds text, authors and tags and pages 50 at a time', async ({ page }) => {
    const w = uid()
    const t = uid()
    await addQuotes(page, [
      ...Array.from({ length: 50 }, (_, i) => ({ text: `Bulk ${i} ${w}` })),
      { text: `By author ${uid()}`, author: `Bulk ${w}` },
      { text: `By tag ${uid()}`, tags: t },
    ])
    await page.goto('/admin/quotes')
    await main(page).getByRole('searchbox').fill(w)
    await main(page).getByRole('button', { name: 'Suchen' }).click()
    await expect(page).toHaveURL(new RegExp(`q=${w}`))
    await expect(page.locator('tbody tr')).toHaveCount(50)
    await expect(page.locator('tbody tr').first()).toContainText(`Bulk ${w}`) // newest first: the author match
    const nav = pageNav(page)
    await expect(nav.getByRole('link')).toHaveText([/Zurück/, '1', '2', /Weiter/])
    await nav.getByRole('link', { name: '2', exact: true }).click()
    await expect(page.locator('tbody tr')).toHaveCount(1)
    await expect(page.locator('tbody tr')).toContainText(`Bulk 0 ${w}`)
    await expect(main(page).getByRole('searchbox')).toHaveValue(w)

    await main(page).getByRole('searchbox').fill(t)
    await main(page).getByRole('button', { name: 'Suchen' }).click()
    await expect(page.locator('tbody tr')).toHaveCount(1)
    await expect(page.locator('tbody tr')).toContainText('By tag')
  })

  test('all quotes page 50 at a time with Weiter and Zurück (cursor pages)', async ({ page }) => {
    await page.goto('/admin/quotes')
    const ids = async () => (await page.locator('tbody tr td:first-child').allInnerTexts()).map(Number)
    await expect(page.getByText(/^\d+ Zitate$/)).toBeVisible()
    const first = await ids()
    expect(first).toHaveLength(50)
    await pageNav(page).getByRole('link', { name: /Weiter/ }).click()
    await expect(pageNav(page)).toContainText(/Seite 2 \/ \d+/)
    const second = await ids()
    expect(Math.max(...second)).toBeLessThan(Math.min(...first))
    await pageNav(page).getByRole('link', { name: /Zurück/ }).click()
    await expect(pageNav(page)).toContainText(/Seite 1 \/ \d+/)
    expect(Math.min(...(await ids()))).toBeGreaterThan(Math.max(...second))
  })

  test('an unknown quote number sends the editor back to the list', async ({ page }) => {
    await page.goto('/admin/quotes/999999999/edit')
    await heading(page, 'Zitate verwalten')
    await expect(toast(page)).toContainText('Zitat nicht gefunden.')
  })
})

test.describe('tags', () => {
  test('add a tag; a duplicate is refused; the filter finds it; delete it', async ({ page }) => {
    const name = `tag-${uid()}`
    await page.goto('/admin/tags')
    await page.getByLabel('Tag-Name').fill(name)
    await page.getByRole('button', { name: 'Tag hinzufügen' }).click()
    await expect(toast(page)).toContainText('Gespeichert.')
    await page.getByLabel('Tag-Name').fill(name)
    await page.getByRole('button', { name: 'Tag hinzufügen' }).click()
    await expect(toast(page)).toContainText('Tag existiert bereits.')

    await page.getByPlaceholder('Tags suchen...').fill(name)
    await main(page).getByRole('button', { name: 'Suchen' }).click()
    await expect(page.getByText(/^1 Tags$/)).toBeVisible()
    await expect(row(page, name).locator('td').nth(2)).toHaveText('0')

    page.once('dialog', (d) => d.accept())
    await row(page, name).getByRole('button', { name: 'Löschen' }).click()
    await expect(toast(page)).toContainText('Tag gelöscht.')
    await page.goto(`/admin/tags?q=${name}`)
    await expect(page.locator('tbody tr')).toHaveCount(0)
  })

  test('deleting a tag in use takes it off its quotes', async ({ page }) => {
    const w = uid()
    const [id] = await addQuotes(page, [{ text: `Tagged ${w}`, tags: `gone-${w}, stays-${w}` }])
    await page.goto(`/admin/tags?q=${w}`)
    await expect(row(page, `gone-${w}`).locator('td').nth(2)).toHaveText('1')
    page.once('dialog', (d) => d.accept())
    await row(page, `gone-${w}`).getByRole('button', { name: 'Löschen' }).click()
    await expect(toast(page)).toContainText('Tag gelöscht.')
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.card-body a.badge')).toHaveText([`stays-${w}`])
  })

  test('over-long tag names and authors are cut to their column size, not a server error', async ({ page }) => {
    const w = uid()
    const long = `long-${w}-`.padEnd(250, 'x')
    await page.goto('/admin/tags')
    await page.getByLabel('Tag-Name').fill(long)
    await expect(page.getByLabel('Tag-Name')).toHaveValue(long.slice(0, 200)) // maxlength
    await page.getByRole('button', { name: 'Tag hinzufügen' }).click()
    await expect(toast(page)).toContainText('Gespeichert.')
    await page.goto(`/admin/tags?q=${w}`)
    await expect(row(page, w).locator('td').nth(1)).toHaveText(long.slice(0, 200))

    // The form's own POST without the browser's maxlength: tags field and author.
    const tag = `t${w}`.padEnd(250, 'y')
    const [id] = await addQuotes(page, [{ text: `Long ${w}`, author: 'A'.repeat(600), tags: tag }])
    await page.goto(`/quote/${id}`)
    await expect(page.locator('.quote-author')).toHaveText('A'.repeat(500))
    await expect(page.locator('.card-body a.badge')).toHaveText(tag.slice(0, 200))
  })

  test('the tag list pages 50 at a time', async ({ page }) => {
    await page.goto('/admin/tags')
    await expect(page.locator('tbody tr')).toHaveCount(50)
    const nav = page.locator('nav .pagination')
    await nav.getByRole('link', { name: '2', exact: true }).click()
    await expect(page).toHaveURL(/page=2/)
    await expect(nav.locator('.active')).toHaveText('2')
    await nav.getByRole('link', { name: 'Zurück' }).click()
    await expect(nav.locator('.active')).toHaveText('1')
  })
})

test('a toast closes with its button and on its own after four seconds', async ({ page }) => {
  await page.clock.install()
  await page.goto('/admin/quotes/999999999/edit')
  const t = page.locator('.toast')
  await expect(t).toBeVisible()
  await page.clock.runFor(4_500)
  await expect(t).toBeHidden()
  await page.goto('/admin/quotes/999999999/edit')
  await expect(t).toBeVisible()
  await t.getByRole('button', { name: 'Schließen' }).click()
  await expect(t).toBeHidden()
})
