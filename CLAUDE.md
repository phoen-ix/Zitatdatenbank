# Zitatdatenbank - CLAUDE.md

Bilingual (DE/EN) Flask app for browsing, searching and managing ~516k quotes (24.6k German from the
datenbörse.net MySQL dump `zitate.sql`, 500k English from the Kaggle `quotes.csv`). Flask 3.1 +
SQLAlchemy/Login/WTF/Limiter/Migrate, MariaDB 12.3 (SQLite in tests), Bootstrap 5.3 + Bootstrap Icons
self-hosted, gunicorn in Docker. README.md (German first, then English) is the user doc.

## Commands
```bash
python3 -m pytest                       # tests (conftest sets FLASK_TESTING, SQLite in-memory)
# local dev server, run in app/ (SQLite in instance/dev.db, admin admin/admin)
export SECRET_KEY=dev-secret SQLALCHEMY_DATABASE_URI=sqlite:///dev.db
flask create-admin --username admin --password admin   # CLI commands create the tables
flask import-csv ../e2e/docs/fixtures/quotes-en.csv --default-tags "English,Englisch,Source: Kaggle"
flask run
# docs screenshots: throwaway stack + Playwright tour (needs `npm ci` + chromium in e2e/)
scripts/docs-screenshots.sh [outdir]    # default docs/screenshots; PORT_BASE=25600
# e2e suite (e2e/tests, inventory e2e/COVERAGE.md): throwaway stack zitatdatenbank_e2e + Playwright
scripts/e2e.sh [playwright args]        # e.g. --grep backup; ARTIFACTS=dir keeps report/traces
```
CLI (in `app/`, or `docker compose exec web flask …`): `import-quotes <sql>`,
`import-csv <csv> --default-tags "a,b"` (columns quote, author, category; category = comma-separated
tags), `cleanup-quotes`, `create-admin --username X --password Y` (also resets an existing password).

## Invariants
- **No `app/__init__.py`:** with it the `flask` script imports `app.app` without `app/` on sys.path
  (`No module named 'extensions'`). Modules import each other flat (`from extensions import db`).
- **Importing app.py runs the startup sequence** in server processes (gunicorn, `python app.py`):
  create_all, admin from env, auto-import (`/data/zitate.sql`, `/data/quotes.csv` if the quote table is
  empty), versioned cleanup, one-time tag migration, FULLTEXT indexes. `flask …` commands (`flask run`
  too; Flask sets `FLASK_RUN_FROM_CLI`) only run create_all; `FLASK_TESTING=1` skips both.
- **Tag migration** (`_auto_migrate_tags`) runs whenever quotes exist and the `tags_migrated` Setting
  is unset (fresh install, after restoring a backup without any tags). It only touches quotes *without*
  tags (the SQL import creates German quotes untagged): Deutsch/German/Quelle: Zitatdatenbank + their
  `category`. Never let it replace existing tags again: that re-tagged the English CSV import as German.
- **CSP blocks inline event handlers:** `script-src 'self' 'nonce-…'`, no `unsafe-hashes`. Never write
  `onclick=`/`onchange=`… (tests/test_routes.py fails on them): use a `<script nonce="{{ csp_nonce }}">`
  block with addEventListener, or base.html's delegated `data-confirm` / `data-autosubmit` attributes.
- **Redirect targets from the request** (`?next=`, the Referer) only via `helpers.local_path()` /
  `same_site_referrer()`: browsers read `/\x`, `///x` and `/<tab>/x` as host x, urlparse does not.
- **Secure session cookies** whenever `FLASK_TESTING != 1`: over plain HTTP, login/CSRF/language switch
  work only on localhost.
- After any write to quotes, tags or settings call `invalidate_stats_cache()` (in-process cache, 5-min TTL,
  one gunicorn worker).
- Every UI string goes through `_('key')` with both `de` and `en` in translations.py; default language `de`.
- Theme overrides live in Setting `theme_{name}_{field}`; switching themes deletes the new theme's stale
  overrides, colors are saved only when customizing the current theme. Validate colors (hex) and effects (int).
- `data/data.tar.gz` (~53 MB, Git LFS, `.dockerignore`d) reaches the container only via the `./data`
  bind mount; entrypoint.sh extracts it and exits with a hint if it is an LFS pointer.
- **Docs/e2e stacks:** compose project `zitatdatenbank_docs` (tour) / `zitatdatenbank_e2e`, never the
  default `zitatdatenbank` (fixed `container_name`s of a local instance). Port block 25600, bound to
  127.0.0.1. `docker-compose.e2e.yml` drops every bind mount (no `data.tar.gz` import, anonymous DB volume,
  `.env` ignored via `--env-file /dev/null`); `docker-compose.docs.yml` seeds the gunicorn worker's RNG so
  the home page's random quote is reproducible. Teardown `down -v --remove-orphans --rmi local`.
- **E2E suite** (`e2e/playwright.config.ts`): projects `setup` (imports the fixtures, saves the admin
  session to `e2e/.auth/`) → `main` (2 workers; every test adds its own quotes/tags with a `uid()` word)
  → `global` (settings, themes, backup/restore; 1 worker) → `limits` (runs into the rate limits, last).
  Limits are per IP and every browser of a run shares one: `/login` (10/min, page views count) and
  `/search` go through `unlimited()` in `e2e/tests/support.ts`, guests' admin routes are checked as 302s.
- Demo data = `e2e/docs/fixtures/*.csv` (≤200 rows, sampled from the two real sources, see its README);
  `*.csv` is gitignored everywhere else. Screenshot names are stable once committed; the gallery is
  `docs/screenshots/README.md`.
- This VM also runs live stacks (`phytotron-*`, `vib-*`): never touch them or their project names.

## Layout
- `app/app.py` - app factory-less setup, security headers, error handlers, CLI, startup sequence
- `app/config.py` - THEMES (5 static + 9 animated), COLOR_KEYS (11), EFFECT_KEYS (typing_speed, particle_count)
- `app/helpers.py` - settings, `_()`, active theme + overrides, caches, FastPagination
- `app/import_service.py` (SQL/CSV import), `cleanup_service.py` (CLEANUP_VERSION, author/text fixes, dedup),
  `backup_service.py` (mysqldump tar.gz in /backups)
- `app/routes/` - main.py (public pages, `/api/*`, `/health`, `/set-lang/<lang>`), admin.py, auth.py
- `app/templates/`, `app/static/css/animations.css` (animated themes; honours prefers-reduced-motion)
- `e2e/` - own Node package: docs tour (`docs/tour.spec.ts`, `docs/seed.ts`, `playwright.docs.config.ts`),
  e2e suite (`tests/`, `playwright.config.ts`, `COVERAGE.md`)

## Key patterns
- Tags: many-to-many via `quote_tags` (ON DELETE CASCADE); German quotes carry Deutsch/German/
  Quelle: Zitatdatenbank, English ones English/Englisch/Source: Kaggle.
- Random quote: COUNT + random OFFSET (uniform; `>= rand_id` was biased by ID gaps); index sends
  `Cache-Control: no-store`.
- Performance: keyset pagination (cursor) on browse/admin lists, FastPagination (no COUNT),
  `selectinload(Quote.tags)`, FULLTEXT MATCH on MariaDB (boolean operators stripped), cached tag-name map.
- Security: CSRF on all forms, login 10/min, search, `/api/random` and `/api/quotes` 30/min, `/api/quotes/<id>` 60/min,
  `X-RateLimit-*` headers, `next` must be a relative path, Referer redirects same-host only, backup
  filenames whitelisted, restore extracts only `dump.sql` and rejects links.
- Backups exclude setting/admin_user/backup_log/alembic_version; restore resets `cleanup_version`, and
  `tags_migrated` only when the restored data has no tags.
- `|nlbr` turns `//` in quote text into `<br>`; the typing animation keeps those breaks.
- Startup logs numbered steps [1/6]–[6/6] (`docker compose logs -f web`).
