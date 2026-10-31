import { seedQuotes } from '../docs/seed'
import { ADMIN_STATE, expect, login, test } from './support'

/* Once per run: the demo quotes (the docs tour's, see docs/seed.ts) and the
 * admin's session, which the other projects reuse (login is rate-limited). */
test('seed the demo quotes and sign the admin in', async ({ page, baseURL }) => {
  await seedQuotes(baseURL!)
  await login(page)
  await expect(page).toHaveURL(/\/admin\/$/)
  await page.context().storageState({ path: ADMIN_STATE })
})
