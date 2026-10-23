# Zitatdatenbank - CLAUDE.md

Bilingual (DE/EN) Flask app for browsing, searching and managing ~516k quotes (24.6k German from the
datenbörse.net MySQL dump `zitate.sql`, 500k English from the Kaggle `quotes.csv`). Flask 3.1 +
SQLAlchemy/Login/WTF/Limiter/Migrate, MariaDB 12.3 (SQLite in tests), Bootstrap 5.3 + Bootstrap Icons
self-hosted, gunicorn in Docker. README.md (German first, then English) is the user doc.

## Commands
```bash
python3 -m pytest                       # tests (conftest sets FLASK_TESTING, SQLite in-memory)
# local dev server, run in app/ (SQLite in instance/dev.db, admin admin/admin)
export SECRET_KEY=dev-secret SQLALCHEMY_DATABASE_URI=sqlite:///dev.db ADMIN_PASSWORD=admin
python -m flask import-csv ../e2e/docs/fixtures/quotes-en.csv --default-tags "English,Englisch,Source: Kaggle"
python -m flask run
# docs screenshots: throwaway stack + Playwright tour (needs `npm ci` + chromium in e2e/)
scripts/docs-screenshots.sh [outdir]    # default docs/screenshots; PORT_BASE=25600
```
CLI (in `app/`, or `docker compose exec web python -m flask …`): `import-quotes <sql>`,
`import-csv <csv> --default-tags "a,b"` (columns quote, author, category; category = comma-separated
tags), `cleanup-quotes`, `create-admin --username X --password Y` (also resets an existing password).

## Invariants
- **`python -m flask`, never `flask`.** `app/__init__.py` makes the `flask` script import `app.app`
  without `app/` on sys.path → `No module named 'extensions'`. Same inside the container (/app).
- **Importing app.py runs the startup sequence** unless `FLASK_TESTING=1`: create_all, admin from env,
  auto-import (`/data/zitate.sql`, `/data/quotes.csv` if the quote table is empty), versioned cleanup,
  one-time tag migration, FULLTEXT indexes. That includes every CLI command.
- **Tag-migration trap:** `_auto_migrate_tags` runs whenever quotes exist and the `tags_migrated`
  Setting is unset, and *replaces* every quote's tags with Deutsch/German/Quelle: Zitatdatenbank +
  its `category`. CSV-imported quotes have no category, so they lose their tags. That hits a fresh
  install (the English quotes the same startup just imported) and any restore (restore clears
  `tags_migrated`). Import CSVs into a fresh DB with `FLASK_TESTING=1` (as e2e/docs/seed.ts does).
- **CSP blocks inline event handlers:** `script-src 'self' 'nonce-…'`, no `unsafe-hashes`. Write JS in a
  `<script nonce="{{ csp_nonce }}">` block with addEventListener. The existing `onclick`/`oninput`
  (admin/settings.html) and `onchange` (browse.html sort select) attributes never run.
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
- `e2e/` - own Node package: docs tour (`docs/tour.spec.ts`, `docs/seed.ts`), `playwright.docs.config.ts`

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
- Backups exclude setting/admin_user/backup_log/alembic_version; restore resets `cleanup_version` and
  `tags_migrated`.
- `|nlbr` turns `//` in quote text into `<br>`; the typing animation keeps those breaks.
- Startup logs numbered steps [1/6]–[6/6] (`docker compose logs -f web`).
