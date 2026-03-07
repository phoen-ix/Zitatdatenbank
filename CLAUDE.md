# Zitatdatenbank - CLAUDE.md

## Project Overview
Multilingual (DE/EN) Flask web application for browsing, searching, and managing ~524k quotes (24.6k German + 500k English). German quotes from MySQL dump (`zitate.sql`), English quotes from Kaggle CSV (`quotes.csv`).

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
- `app/helpers.py` - Settings CRUD, translation helper, theme utilities, per-theme override loading
- `app/import_service.py` - SQL parser + data import logic
- `app/backup_service.py` - Backup create/restore/prune
- `app/cleanup_service.py` - Quote data cleanup (wiki markup, truncated authors, dedup)
- `app/routes/` - main.py (public + credits), admin.py (admin CRUD + tags + per-theme settings), auth.py (login/logout)
- `app/templates/` - Jinja2 templates (tags.html, credits.html, admin/tags.html)
- `app/static/css/animations.css` - Animated theme styles, typing cursor, particle containers
- `tests/` - pytest test suite (228 tests)

## CLI Commands
- `flask import-quotes <path>` - Import quotes from SQL dump
- `flask import-csv <path> --default-tags "tag1,tag2"` - Import quotes from CSV (columns: quote, author, category)
- `flask cleanup-quotes` - Fix wiki markup, truncated authors/categories, remove duplicates
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
- Auth: Flask-Login with AdminUser model, env var auto-creation
- Auto-import: Quotes imported on first startup if table is empty
- Auto-cleanup: Versioned (CLEANUP_VERSION=16 in cleanup_service.py, `cleanup_version` Setting), re-runs on version bump
- Auto-tag-migration: One-time migration of category → tags + default tags, gated by `tags_migrated` Setting
- Credits page: `/credits` route with CC BY-SA 3.0 (datenbörse.net) + CC0 (Kaggle) license info, linked from footer
- Theme switching: On theme change, stale per-theme overrides are cleared; color overrides only saved when customizing the current theme (not when switching)
- Tests: SQLite in-memory, CSRF disabled, session-scoped app fixture
