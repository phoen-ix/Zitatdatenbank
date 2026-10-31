import { addQuotes, apiGet, expect, test, uid } from './support'

/* The JSON API and the health check, against the real MariaDB (FULLTEXT search).
 * /api/random and /api/quotes allow 30 calls a minute per IP: this file makes
 * about a dozen (apiGet waits a 429 out); limits.spec.ts runs one into its limit. */

test('GET /health reports the database', async ({ request }) => {
  const res = await request.get('/health')
  expect(res.status()).toBe(200)
  expect(await res.json()).toEqual({ status: 'ok', checks: { database: 'ok' } })
})

test('GET /api/random returns one quote, with rate-limit headers and no CSP', async ({ request }) => {
  const res = await apiGet(request, '/api/random')
  expect(res.status()).toBe(200)
  const q = await res.json()
  expect(Object.keys(q).sort()).toEqual(['author', 'id', 'tags', 'text'])
  expect(q.text).not.toBe('')
  expect(res.headers()['x-ratelimit-limit']).toBe('30')
  expect(Number(res.headers()['x-ratelimit-remaining'])).toBeLessThan(30)
  expect(res.headers()['content-security-policy']).toBeUndefined()
  expect(res.headers()['x-content-type-options']).toBe('nosniff')
})

test('GET /api/quotes filters by author, tag and text, pages, and caps per_page', async ({ request, adminPage }) => {
  const w = uid()
  const word = uid()
  const ids = await addQuotes(adminPage, [
    { text: `Api one ${w} ${word}`, author: `Api ${w}`, tags: `api-${w}, second-${w}` },
    { text: `Api two ${uid()}`, author: `Api ${w}`, tags: `api-${w}` },
    { text: `Api three ${uid()}`, author: `Api ${w}` },
  ])
  const get = async (params: Record<string, string>) => {
    const res = await apiGet(request, '/api/quotes', params)
    expect(res.status()).toBe(200)
    return res.json()
  }

  const byAuthor = await get({ author: `Api ${w}` })
  expect(byAuthor.quotes.map((q: { id: number }) => q.id)).toEqual([...ids].reverse()) // newest first
  expect(byAuthor).toMatchObject({ page: 1, per_page: 20, has_next: false, has_prev: false })
  expect(byAuthor.quotes[2]).toEqual({ id: ids[0], text: `Api one ${w} ${word}`, author: `Api ${w}`, tags: [`api-${w}`, `second-${w}`] })

  expect((await get({ tag: `api-${w}` })).quotes).toHaveLength(2)
  expect((await get({ q: word })).quotes.map((q: { id: number }) => q.id)).toEqual([ids[0]])
  expect((await get({ q: w })).quotes).toHaveLength(3) // the author matches too

  const paged = await get({ author: `Api ${w}`, per_page: '2', page: '2' })
  expect(paged).toMatchObject({ page: 2, per_page: 2, has_next: false, has_prev: true })
  expect(paged.quotes.map((q: { id: number }) => q.id)).toEqual([ids[0]])
  expect((await get({ author: `Api ${w}`, per_page: '2' })).has_next).toBe(true)

  expect((await get({ per_page: '500' })).per_page).toBe(100)
})

test('GET /api/quotes/<id> returns the quote; unknown ids and routes are JSON 404s', async ({ request, adminPage }) => {
  const w = uid()
  const [id] = await addQuotes(adminPage, [{ text: `Single ${w}`, author: `One ${w}` }])
  const res = await apiGet(request, `/api/quotes/${id}`)
  expect(res.status()).toBe(200)
  expect(await res.json()).toEqual({ id, text: `Single ${w}`, author: `One ${w}`, tags: [] })
  expect(res.headers()['x-ratelimit-limit']).toBe('60')

  const missing = await apiGet(request, '/api/quotes/999999999')
  expect(missing.status()).toBe(404)
  expect(await missing.json()).toEqual({ error: 'Quote not found' })

  const unknown = await request.get('/api/nothing-here')
  expect(unknown.status()).toBe(404)
  expect(await unknown.json()).toEqual({ status: 'error', detail: 'Not found' })
})
