# Zitatdatenbank - CLAUDE.md

## Project Overview
Multilingual (DE/EN) Flask web application for browsing, searching, and managing ~24,623 German quotes. Data imported from MySQL dump (`zitate.sql`).

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
- `app/app.py` - Flask app, CLI commands, startup logic, `|nlbr` template filter
- `app/extensions.py` - Shared Flask extensions (db, csrf, migrate, limiter, login_manager)
- `app/config.py` - 14 theme definitions (5 static + 9 animated), COLOR_KEYS, EFFECT_KEYS, constants
- `app/translations.py` - DE/EN translation dictionaries
- `app/models.py` - Quote, AdminUser, Setting, BackupLog
- `app/helpers.py` - Settings CRUD, translation helper, theme utilities, per-theme override loading
- `app/import_service.py` - SQL parser + data import logic
- `app/backup_service.py` - Backup create/restore/prune
- `app/routes/` - main.py (public), admin.py (admin CRUD + per-theme settings), auth.py (login/logout)
- `app/templates/` - Jinja2 templates
- `app/static/css/animations.css` - Animated theme styles, typing cursor, particle containers
- `app/cleanup_service.py` - Quote data cleanup (wiki markup, truncated authors, dedup)
- `tests/` - pytest test suite (219 tests)

## CLI Commands
- `flask import-quotes <path>` - Import quotes from SQL dump
- `flask cleanup-quotes` - Fix wiki markup, truncated authors/categories, remove duplicates
- `flask create-admin --username X --password Y` - Create admin user

## Key Patterns
- Translation: `_('key')` function, language set via session
- Themes: 14 themes (5 static, 9 animated with particles/typing effects), all customizable per-theme via admin settings
- Theme overrides stored in Setting table as `theme_{name}_{field}`, merged with defaults at load time
- 11 color fields + 2 effect fields (typing_speed, particle_count) per theme
- CSS variables in `:root` for all theme colors, no `is_dark` conditionals
- `|nlbr` filter converts `//` in quote text to `<br>` tags (1,561 quotes affected)
- Typing animation on animated themes processes all `.quote-text` elements, handles `<br>` nodes
- Auth: Flask-Login with AdminUser model, env var auto-creation
- Auto-import: Quotes imported on first startup if table is empty
- Auto-cleanup: Versioned (CLEANUP_VERSION=16 in cleanup_service.py, `cleanup_version` Setting), re-runs on version bump. Fixes wiki markup, truncated Sprichwort/Werbespruch authors, "Aus Country" → "Sprichwort aus Country", garbage authors (numeric/single-char/fragments), truncated parentheticals, encoding fixes, Bible/source book references, disambiguation pages, work/film titles, company names, deduplicates quotes
- Theme switching: On theme change, stale per-theme overrides are cleared; color overrides only saved when customizing the current theme (not when switching)
- Tests: SQLite in-memory, CSRF disabled, session-scoped app fixture
