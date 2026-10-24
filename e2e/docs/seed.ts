import { execFileSync } from 'node:child_process'

/* The demo database the docs tour photographs: ~100 quotes from the two real
 * sources (fixtures/quotes-de.csv and quotes-en.csv, see fixtures/README.md),
 * imported with the app's own `flask import-csv` and tagged like a production
 * install (the default tags the startup auto-import uses).
 *
 * IDEMPOTENT: it imports only into an empty database. */

export const ADMIN_USERNAME = process.env.DOCS_ADMIN_USERNAME ?? 'admin'
export const ADMIN_PASSWORD = process.env.DOCS_ADMIN_PASSWORD ?? 'docs-admin-not-a-secret'
const WEB = process.env.DOCS_WEB_CONTAINER ?? 'zitatdatenbank_docs-web'
const DB = process.env.DOCS_DB_CONTAINER ?? 'zitatdatenbank_docs-db'

const IMPORTS = [
  ['/fixtures/quotes-de.csv', 'Deutsch,German,Quelle: Zitatdatenbank'],
  ['/fixtures/quotes-en.csv', 'English,Englisch,Source: Kaggle'],
]

export interface ApiQuote {
  id: number
  text: string
  author: string
  tags: string[]
}

export async function apiQuotes(baseURL: string, params: Record<string, string>): Promise<ApiQuote[]> {
  const res = await fetch(new URL(`/api/quotes?${new URLSearchParams(params)}`, baseURL))
  if (!res.ok) throw new Error(`[seed] /api/quotes: HTTP ${res.status}`)
  return (await res.json()).quotes
}

export async function seedQuotes(baseURL: string): Promise<void> {
  if ((await apiQuotes(baseURL, { per_page: '1' })).length) return
  for (const [csv, tags] of IMPORTS) {
    execFileSync('docker', ['exec', '-u', 'appuser', WEB,
      'flask', 'import-csv', csv, '--default-tags', tags], { stdio: 'inherit' })
  }
}

/** The backup page shows the file's name and mtime and the log's timestamp,
 * all from the server clock: move them to a fixed date. */
export const BACKUP_NAME = 'zitate_backup_2026_06_15_08-00-00.tar.gz'
export function backdateBackups(): void {
  execFileSync('docker', ['exec', WEB, 'sh', '-c',
    `cd /backups && for f in zitate_backup_*.tar.gz; do [ "$f" = ${BACKUP_NAME} ] || mv "$f" ${BACKUP_NAME}; done && ` +
    `touch -d '2026-06-15 08:00:00' ${BACKUP_NAME}`])
  const sql = `UPDATE backup_log SET ran_at = '2026-06-15 08:00:00', message = 'Backup created: ${BACKUP_NAME}'`
  execFileSync('docker', ['exec', DB, 'sh', '-c',
    `mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -e "${sql}"`])
}
