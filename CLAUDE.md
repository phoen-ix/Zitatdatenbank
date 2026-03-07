# Zitatdatenbank - CLAUDE.md

## Project Overview
Multilingual (DE/EN) Flask web application for browsing, searching, and managing ~516k quotes (24.6k German + 500k English, after dedup). German quotes from MySQL dump (`zitate.sql`), English quotes from Kaggle CSV (`quotes.csv`).

## Tech Stack
- Flask 3.1 with SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter, Flask-Migrate
- MariaDB 11 (production), SQLite in-memory (tests)
- Bootstrap 5.3 self-hosted, Bootstrap Icons
- Docker + docker-compose

## Running Tests
```bash
FLASK_TESTING=1 python3 -m pytest tests/ -v
```

## Running Locally
```bash
export FLASK_TESTING=1
export SECRET_KEY=dev-secret
export SQLALCHEMY_DATABASE_URI=sqlite:///dev.db
cd app && flask run
```

## Docker
```bash
cp .env.example .env  # Edit with real values
docker compose build && docker compose up -d
```

## Project Structure
- `app/app.py` - Flask app, CLI commands, startup logic, `|nlbr` template filter, tag migration
- `app/extensions.py` - Shared Flask extensions (db, csrf, migrate, limiter, login_manager)
- `app/config.py` - 14 theme definitions (5 static + 9 animated), COLOR_KEYS, EFFECT_KEYS, constants
- `app/translations.py` - DE/EN translation dictionaries
- `app/models.py` - Quote, Tag, quote_tags, AdminUser, Setting, BackupLog
- `app/helpers.py` - Settings CRUD, translation helper, theme utilities, per-theme override loading, stats/result caching, FastPagination
- `app/import_service.py` - SQL parser + data import logic
- `app/backup_service.py` - Backup create/restore/prune
- `app/cleanup_service.py` - Quote data cleanup (wiki markup, truncated authors, dedup)
- `app/routes/` - main.py (public + credits + REST API), admin.py (admin CRUD + tags + per-theme settings), auth.py (login/logout)
- `app/templates/` - Jinja2 templates (tags.html, credits.html, admin/tags.html)
- `app/static/css/animations.css` - Animated theme styles, typing cursor, particle containers
- `app/templates/errors/` - Custom 404/500 error pages
- `tests/` - pytest test suite (264 tests)

## CLI Commands
- `flask import-quotes <path>` - Import quotes from SQL dump
- `flask import-csv <path> --default-tags "tag1,tag2"` - Import quotes from CSV (columns: quote, author, category)
- `flask cleanup-quotes` - Fix wiki markup, truncated authors/categories, non-Latin scripts, deduplication
- `flask create-admin --username X --password Y` - Create admin user

## Key Patterns
- Translation: `_('key')` function, language set via session
- Tags: Many-to-many (Quote ↔ Tag via quote_tags). Replaces old category field. Admin-managed, public-filterable. German quotes tagged "Deutsch", "German", "Quelle: Zitatdatenbank". English quotes tagged "English", "Englisch", "Source: Kaggle". Categories auto-migrated to tags on first startup (`tags_migrated` Setting).
- Themes: 14 themes (5 static, 9 animated with particles/typing effects), all customizable per-theme via admin settings
- Theme overrides stored in Setting table as `theme_{name}_{field}`, merged with defaults at load time
- 11 color fields + 2 effect fields (typing_speed, particle_count) per theme
- CSS variables in `:root` for all theme colors, no `is_dark` conditionals
- `|nlbr` filter converts `//` in quote text to `<br>` tags (1,561 quotes affected)
- Typing animation on animated themes processes all `.quote-text` elements, handles `<br>` nodes
- Auth: Flask-Login with AdminUser model, env var auto-creation. Login rate-limited (10/min). Open redirect prevention on `next` param. Session: 8h timeout, HttpOnly, SameSite=Lax cookies.
- Auto-import: Quotes imported on first startup if table is empty
- Data files: Distributed as `data/data.tar.gz` (53MB), auto-extracted by entrypoint.sh on first start. Contains `zitate.sql` (German) and `quotes.csv` (English).
- Auto-cleanup: Versioned (CLEANUP_VERSION in cleanup_service.py, `cleanup_version` Setting), re-runs on version bump. Handles wiki markup, truncated authors, non-Latin scripts, sentence-like garbage authors, deduplication (CRC32-indexed text_hash column on MariaDB). All deletions (dedup, non-Latin, garbage) delete quote_tags FK entries first.
- Auto-tag-migration: One-time migration of category → tags + default tags, gated by `tags_migrated` Setting
- Credits page: `/credits` route with CC BY-SA 3.0 (datenbörse.net) + CC0 (Kaggle) license info, linked from footer
- Theme switching: On theme change, stale per-theme overrides are cleared; color overrides only saved when customizing the current theme (not when switching)
- Performance: In-memory cache (`_stats_cache` in helpers.py, 5-min TTL) for stats, theme, tags, settings. `invalidate_stats_cache()` clears all caches on data/settings changes. `FastPagination` skips COUNT queries. Keyset pagination on browse (cursor param). `selectinload(Quote.tags)` for batch tag loading. FULLTEXT MATCH for search on MariaDB.
- REST API: `/api/random`, `/api/quotes` (browse/search/filter), `/api/quotes/<id>`. Rate-limited (30/min browse, 60/min detail). Returns JSON with id, text, author, tags. `X-RateLimit-*` headers on all responses.
- Security headers: CSP with nonce-based script-src, X-Frame-Options: DENY, X-Content-Type-Options: nosniff. CSRF on all forms.
- Input validation: quotes_per_page (int 5-100), site_name (max 100 chars), color inputs (hex format), backup filenames (strict regex), page/per_page clamped to valid ranges. Cursor values < 1 ignored. FULLTEXT boolean operators sanitized. LIKE wildcards escaped.
- Error handling: Custom 404/500 handlers. JSON responses for `/api/` routes, HTML templates for browser requests.
- Backup: SQL dump excludes app state tables (setting, admin_user, backup_log, alembic_version). Restore validates tar members and rejects symlinks. Filename whitelist on download/restore/delete.
- Atomicity: `set_setting(commit=False)` for batch operations, single commit per settings save. IntegrityError handling on tag creation.
- Session: SESSION_COOKIE_SECURE in production, HttpOnly, SameSite=Lax, 8h timeout.
- DB integrity: ON DELETE CASCADE on quote_tags FKs, index on tag_id.
- Tests: SQLite in-memory, CSRF disabled, rate limiter disabled, session-scoped app fixture. Cache invalidated between tests in conftest.py `clean_db` fixture.
