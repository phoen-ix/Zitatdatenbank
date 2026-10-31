import { addQuotes, ADMIN_PASSWORD, expect, heading, login, notLimited, test, toast, uid, unlimited } from './support'

/* Sign-in, sign-out and what a guest may not do. /login allows 10 requests a
 * minute per IP (page views count): login() waits a full window out. */

test('the admin signs in from the navbar and out again', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('link', { name: 'Anmelden' })).toHaveAttribute('href', '/login')
  await login(page)
  await heading(page, 'Admin-Dashboard')
  await expect(page.getByRole('link', { name: 'Verwaltung' })).toBeVisible()
  await page.getByRole('link', { name: 'Abmelden' }).click()
  await expect(page.getByText('Zufallszitat')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Anmelden' })).toBeVisible()
  const res = await page.request.get('/admin/', { maxRedirects: 0 })
  expect(res.status()).toBe(302)
})

test('a wrong password or an unknown user is refused with one message', async ({ page }) => {
  for (const [user, password] of [['admin', 'wrong-password'], [`nobody-${uid()}`, ADMIN_PASSWORD]]) {
    await unlimited(page, async () => {
      await page.goto('/login')
      await notLimited(page)
      await page.getByLabel('Benutzername').fill(user)
      await page.getByLabel('Passwort').fill(password)
      await page.getByRole('button', { name: 'Anmelden' }).click()
    })
    await expect(page).toHaveURL(/\/login$/)
    await expect(toast(page)).toContainText('Ungültiger Benutzername oder Passwort.')
    await expect(page.getByRole('link', { name: 'Verwaltung' })).toBeHidden()
  }
})

test('a guest sent to the login page lands on the page they asked for', async ({ page }) => {
  await login(page, '/admin/tags?q=humor')
  await heading(page, 'Tags verwalten')
  await expect(page).toHaveURL(/\/admin\/tags\?q=humor$/)
})

test('a guest who opens an admin page is asked to sign in', async ({ page }) => {
  await unlimited(page, () => page.goto('/admin/settings'))
  await expect(page).toHaveURL(/\/login\?next=/)
  await expect(toast(page)).toContainText('Bitte melden Sie sich an.')
  await expect(page.getByLabel('Benutzername')).toBeFocused()
})

test('a guest cannot change anything by posting to an admin action', async ({ page, adminPage }) => {
  const w = uid()
  const [id] = await addQuotes(adminPage, [{ text: `Guarded ${w}` }])
  await page.goto('/')
  const status = await page.evaluate(async (id) => {
    const token = document.querySelector<HTMLMetaElement>('meta[name=csrf-token]')!.content
    const res = await fetch(`/admin/quotes/${id}/delete`, { method: 'POST', body: new URLSearchParams({ csrf_token: token }), redirect: 'manual' })
    return res.type
  }, id)
  expect(status).toBe('opaqueredirect') // to the login page
  await page.goto(`/quote/${id}`)
  await expect(page.locator('.quote-text')).toHaveText(`Guarded ${w}`)
})

test('a form posted with an expired CSRF token is reloaded with a message, nothing saved', async ({ adminPage: page }) => {
  const w = uid()
  await page.goto('/admin/quotes/add')
  await page.locator('input[name=csrf_token]').evaluate((el: HTMLInputElement) => (el.value = 'expired'))
  await page.getByLabel('Zitattext').fill(`Forged ${w}`)
  await page.getByRole('button', { name: 'Speichern' }).click()
  await expect(toast(page)).toContainText('Das Formular war abgelaufen. Bitte noch einmal absenden.')
  await heading(page, 'Zitat hinzufügen')
  await page.goto(`/admin/quotes?q=${w}`)
  await expect(page.locator('tbody tr')).toHaveCount(0)
})
