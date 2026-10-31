import { execFileSync } from 'node:child_process'

import { addQuotes, ADMIN_STATE, expect, heading, test, toast, uid } from './support'
import type { Page } from '@playwright/test'

/* Site-wide state: settings, themes, backup and restore. Runs after `main`,
 * alone (project `global`), and puts every setting back. */

test.use({ storageState: ADMIN_STATE })
test.describe.configure({ mode: 'serial' })

async function saveGeneral(page: Page, siteName: string, perPage: string): Promise<void> {
  await page.goto('/admin/settings')
  await page.getByLabel('Seitenname').fill(siteName)
  await page.getByLabel('Zitate pro Seite').fill(perPage)
  await page.getByRole('button', { name: 'Speichern' }).first().click()
  await expect(toast(page)).toContainText('Einstellungen gespeichert.')
}

async function themesTab(page: Page): Promise<void> {
  await page.goto('/admin/settings')
  await page.getByRole('tab', { name: 'Themen' }).click()
  await expect(page.getByRole('heading', { name: 'Thema auswählen' })).toBeVisible()
}

async function saveTheme(page: Page): Promise<void> {
  await page.locator('#themeForm').getByRole('button', { name: 'Speichern' }).click()
  await expect(toast(page)).toContainText('Einstellungen gespeichert.')
}

const css = (page: Page, selector: string, prop: string) =>
  page.locator(selector).first().evaluate((el, prop) => getComputedStyle(el).getPropertyValue(prop), prop)

test('site name and quotes per page apply to every visitor; an empty name falls back', async ({ page, browser, baseURL }) => {
  await saveGeneral(page, 'Sprüche-Archiv', '5')
  const guest = await (await browser.newContext({ baseURL })).newPage()
  await guest.goto('/browse')
  await expect(guest.locator('.navbar-brand')).toHaveText('Sprüche-Archiv')
  await expect(guest).toHaveTitle('Zitate durchsuchen - Sprüche-Archiv')
  await expect(guest.locator('.main-content .card')).toHaveCount(5)
  await guest.goto(`/search?q=Wilde`)
  await expect(guest.locator('.main-content .card').first()).toBeVisible()
  expect(await guest.locator('.main-content .card').count()).toBeLessThanOrEqual(5)

  await saveGeneral(page, '', '20')
  await expect(page.getByLabel('Seitenname')).toHaveValue('Zitatdatenbank')
  await guest.goto('/browse')
  await expect(guest.locator('.navbar-brand')).toHaveText('Zitatdatenbank')
  await expect(guest.locator('.main-content .card')).toHaveCount(20)
  await guest.context().close()
})

test('quotes per page outside 5-100 is blocked by the form', async ({ page }) => {
  await page.goto('/admin/settings')
  await page.getByLabel('Zitate pro Seite').fill('500')
  await page.getByRole('button', { name: 'Speichern' }).first().click()
  await expect(page.getByLabel('Zitate pro Seite')).toHaveJSProperty('validity.rangeOverflow', true)
  await expect(page.locator('#toastContainer .toast')).toHaveCount(0)
})

test('a static theme recolours the site; a dark one keeps text readable', async ({ page }) => {
  await themesTab(page)
  await expect(page.getByLabel('Klassisch')).toBeChecked()
  await page.locator('.theme-card[data-theme=dunkel] > div').first().click() // the preview, not the radio
  await expect(page.getByLabel('Dunkel')).toBeChecked()
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#1e1e2e')
  await expect(page.locator('#effectsSection')).toBeHidden()
  await saveTheme(page)
  await page.goto('/browse')
  expect(await css(page, 'body', 'background-color')).toBe('rgb(24, 24, 37)')
  expect(await css(page, '.card', 'color')).toBe('rgb(205, 214, 244)')
  await expect(page.locator('meta[name=theme-color]')).toHaveAttribute('content', '#1e1e2e')
})

test('an animated theme adds its effects, which can be tuned', async ({ page }) => {
  await themesTab(page)
  await page.getByLabel('Hacker').check()
  await expect(page.locator('#effectsSection')).toBeVisible()
  await saveTheme(page) // switching themes saves no colours or effects
  await page.goto('/browse')
  await expect(page.locator('body')).toHaveClass('theme-hacker')
  await expect(page.locator('.typing-cursor').first()).toBeAttached() // the quotes type themselves

  await themesTab(page)
  await expect(page.getByLabel('Tippgeschwindigkeit')).not.toHaveValue('0')
  await page.getByLabel('Tippgeschwindigkeit').fill('0')
  await saveTheme(page)
  await page.goto('/browse')
  await expect(page.locator('.quote-text').first()).toBeVisible()
  await expect(page.locator('.typing-cursor')).toHaveCount(0)
  await themesTab(page)
  await expect(page.getByLabel('Tippgeschwindigkeit')).toHaveValue('0')

  await page.getByLabel('Kosmos').check()
  await saveTheme(page)
  await page.goto('/')
  await expect(page.locator('.stars-container .star')).toHaveCount(80)
  await themesTab(page)
  await page.getByLabel('Partikelanzahl').fill('7')
  await saveTheme(page)
  await page.goto('/')
  await expect(page.locator('.stars-container .star')).toHaveCount(7)
})

test('customising the current theme overrides a colour; "Zurücksetzen" restores it', async ({ page }) => {
  await themesTab(page)
  await page.getByLabel('Klassisch').check()
  await saveTheme(page) // switching themes saves no colours
  await themesTab(page)
  await page.locator('.color-hex[data-for=color_navbar]').fill('#12345')
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#6b4c3b') // incomplete: ignored
  await page.locator('.color-hex[data-for=color_navbar]').fill('#123456')
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#123456')
  await saveTheme(page)
  await page.goto('/')
  expect(await css(page, '.navbar', 'background-color')).toBe('rgb(18, 52, 86)')

  await themesTab(page)
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#123456')
  await page.getByRole('button', { name: 'Zurücksetzen' }).click()
  await expect(toast(page)).toContainText('Einstellungen gespeichert.')
  await page.getByRole('tab', { name: 'Themen' }).click()
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#6b4c3b')
  expect(await css(page, '.navbar', 'background-color')).toBe('rgb(107, 76, 59)')
})

test('switching to a theme drops the colours once saved for it', async ({ page }) => {
  await themesTab(page)
  await page.getByLabel('Wald').check()
  await saveTheme(page)
  await themesTab(page)
  const wald = await page.getByLabel('Navigationsleiste').inputValue()
  await page.locator('.color-hex[data-for=color_navbar]').fill('#abcdef')
  await saveTheme(page)
  await themesTab(page)
  await page.getByLabel('Klassisch').check()
  await saveTheme(page)
  await themesTab(page)
  await page.getByLabel('Wald').check()
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#abcdef') // still stored
  await saveTheme(page)
  await themesTab(page)
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue(wald)
})

test('"Eigene Farben" builds a theme from the colour fields', async ({ page }) => {
  await themesTab(page)
  await page.getByLabel('Eigene Farben').check()
  await expect(page.getByRole('button', { name: 'Zurücksetzen' })).toBeHidden()
  await expect(page.locator('#effectsSection')).toBeHidden()
  await page.locator('.color-hex[data-for=color_navbar]').fill('#0a7d3c')
  await page.locator('.color-hex[data-for=color_bg]').fill('#fdfae8')
  await saveTheme(page)
  await page.goto('/')
  expect(await css(page, '.navbar', 'background-color')).toBe('rgb(10, 125, 60)')
  expect(await css(page, 'body', 'background-color')).toBe('rgb(253, 250, 232)')
  await themesTab(page)
  await expect(page.getByLabel('Eigene Farben')).toBeChecked()
  await expect(page.getByLabel('Navigationsleiste')).toHaveValue('#0a7d3c')

  await page.getByLabel('Klassisch').check()
  await saveTheme(page)
  await page.goto('/')
  expect(await css(page, '.navbar', 'background-color')).toBe('rgb(107, 76, 59)')
})

test.describe('backup', () => {
  test('create a backup, download it, restore it (later changes are gone), delete it', async ({ page }) => {
    await page.goto('/admin/backup')
    await heading(page, 'Backup')
    await page.getByRole('button', { name: 'Backup erstellen' }).click()
    await expect(toast(page)).toContainText('Backup erstellt.')
    const file = (await page.locator('tbody code').first().innerText()).trim()
    expect(file).toMatch(/^zitate_backup_\d{4}_\d\d_\d\d_\d\d-\d\d-\d\d\.tar\.gz$/)
    const backup = page.locator('tbody tr', { has: page.locator('code', { hasText: file }) }) // not the log's rows
    await expect(page.locator('table').last()).toContainText(`Backup created: ${file}`)

    const download = page.waitForEvent('download')
    await backup.getByRole('link', { name: 'Herunterladen' }).click()
    const dl = await download
    expect(dl.suggestedFilename()).toBe(file)
    const head = (await import('node:fs')).readFileSync(await dl.path()).subarray(0, 2)
    expect([...head]).toEqual([0x1f, 0x8b]) // gzip

    const w = uid()
    const [id] = await addQuotes(page, [{ text: `After the backup ${w}` }])
    await page.goto('/admin/backup')
    page.once('dialog', (d) => d.dismiss())
    await backup.getByRole('button', { name: 'Backup wiederherstellen' }).click()
    await expect(page.locator('#toastContainer .toast')).toHaveCount(0)
    expect((await page.goto(`/quote/${id}`))!.status()).toBe(200)

    await page.goto('/admin/backup')
    page.once('dialog', (d) => {
      expect(d.message()).toBe('Wirklich wiederherstellen? Alle aktuellen Daten werden überschrieben!')
      return d.accept()
    })
    await backup.getByRole('button', { name: 'Backup wiederherstellen' }).click()
    await expect(toast(page)).toContainText('Backup wiederhergestellt.')
    await expect(page.locator('table').last()).toContainText(`Restored from: ${file}`)
    expect((await page.goto(`/quote/${id}`))!.status()).toBe(404)
    await page.goto('/browse?author=Oscar Wilde')
    await expect(page.locator('.main-content .card').first()).toBeVisible()

    await page.goto('/admin/backup')
    page.once('dialog', (d) => d.accept())
    await backup.getByRole('button', { name: 'Backup löschen' }).click()
    await expect(toast(page)).toContainText('Backup gelöscht.')
    await expect(backup).toHaveCount(0)
    await expect(page.locator('table').last()).toContainText(`Deleted backup: ${file}`)
  })

  test('a backup or restore that fails says why', async ({ page }) => {
    const web = process.env.DOCS_WEB_CONTAINER ?? 'zitatdatenbank_e2e-web'
    const bogus = 'zitate_backup_2001_01_01_00-00-00.tar.gz'
    execFileSync('docker', ['exec', '-u', 'root', web, 'chmod', '555', '/backups'])
    try {
      await page.goto('/admin/backup')
      await page.getByRole('button', { name: 'Backup erstellen' }).click()
      await expect(toast(page)).toContainText(/^\s*Backup fehlgeschlagen: .*Permission denied/)
      await expect(page.locator('table').last().locator('tr', { hasText: 'Permission denied' }).first()).toContainText('ERROR')
    } finally {
      execFileSync('docker', ['exec', '-u', 'root', web, 'chmod', '755', '/backups'])
    }
    execFileSync('docker', ['exec', web, 'sh', '-c', `echo not-a-tarball > /backups/${bogus}`])
    await page.goto('/admin/backup')
    page.once('dialog', (d) => d.accept())
    await page.locator('tbody tr', { hasText: bogus }).getByRole('button', { name: 'Backup wiederherstellen' }).click()
    await expect(toast(page)).toContainText('Wiederherstellung fehlgeschlagen: ')
    page.once('dialog', (d) => d.accept())
    await page.locator('tbody tr', { hasText: bogus }).getByRole('button', { name: 'Backup löschen' }).click()
    await expect(toast(page)).toContainText('Backup gelöscht.')
  })

  test('unknown or malformed backup names are 404s', async ({ page }) => {
    for (const name of ['zitate_backup_2000_01_01_00-00-00.tar.gz', 'not-a-backup.tar.gz', '..%2Fapp.py']) {
      expect((await page.request.get(`/admin/backup/${name}/download`)).status(), name).toBe(404)
    }
    await page.goto('/admin/backup')
    const status = await page.evaluate(async () => {
      const token = document.querySelector<HTMLMetaElement>('meta[name=csrf-token]')!.content
      const res = await fetch('/admin/backup/zitate_backup_2000_01_01_00-00-00.tar.gz/delete', {
        method: 'POST', body: new URLSearchParams({ csrf_token: token }),
      })
      return [res.status, new URL(res.url).pathname, (await res.text()).includes('Backup nicht gefunden.')]
    })
    expect(status).toEqual([200, '/admin/backup', true])
  })
})

test('with the database down, pages show the error page and /health reports it', async ({ browser, baseURL, request }) => {
  const db = process.env.DOCS_DB_CONTAINER ?? 'zitatdatenbank_e2e-db'
  const page = await (await browser.newContext({ baseURL })).newPage() // unwatched: 5xx expected
  execFileSync('docker', ['stop', db])
  try {
    const res = await page.goto('/browse')
    expect(res!.status()).toBe(500)
    await expect(page.getByRole('heading', { name: '500' })).toBeVisible()
    await expect(page.getByText('Ein interner Fehler ist aufgetreten.')).toBeVisible()
    await page.getByRole('link', { name: 'Startseite' }).click()
    await expect(page.getByRole('heading', { name: '500' })).toBeVisible() // still down: the same page
    const health = await request.get('/health')
    expect(health.status()).toBe(503)
    expect(await health.json()).toEqual({ status: 'error', checks: { database: 'error' } })
  } finally {
    execFileSync('docker', ['start', db])
    await expect.poll(async () => (await request.get('/health')).status(), { timeout: 90_000 }).toBe(200)
    await page.context().close()
  }
})
