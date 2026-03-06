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
# Set environment variables
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
- `app/app.py` - Flask app factory, CLI commands, startup logic
- `app/extensions.py` - Shared Flask extensions (db, csrf, migrate, limiter, login_manager)
- `app/config.py` - Theme definitions, constants
- `app/translations.py` - DE/EN translation dictionaries
- `app/models.py` - Quote, AdminUser, Setting, BackupLog
- `app/helpers.py` - Settings CRUD, translation helper, theme utilities
- `app/import_service.py` - SQL parser + data import logic
- `app/backup_service.py` - Backup create/restore/prune
- `app/routes/` - main.py (public), admin.py (admin CRUD), auth.py (login/logout)
- `app/templates/` - Jinja2 templates
- `tests/` - pytest test suite (58 tests)

## CLI Commands
- `flask import-quotes <path>` - Import quotes from SQL dump
- `flask create-admin --username X --password Y` - Create admin user

## Key Patterns
- Translation: `_('key')` function, language set via session
- Theme: CSS variables from Setting table, 5 presets + custom
- Auth: Flask-Login with AdminUser model, env var auto-creation
- Auto-import: Quotes imported on first startup if table is empty
- Tests: SQLite in-memory, CSRF disabled, session-scoped app fixture
