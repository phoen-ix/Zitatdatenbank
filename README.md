# Zitatdatenbank

A multilingual (DE/EN) web application for browsing, searching, and managing a collection of ~24,623 German quotes.

## Features

- **Browse** quotes with pagination, filtering by author/category, and sorting
- **Search** full-text across quotes, authors, and categories
- **Author & Category** listings with quote counts and alphabetical navigation
- **Random Quote** on the landing page with one-click refresh
- **Admin Panel** with quote CRUD, settings management, and backup/restore
- **5 Themes** (Klassisch, Modern, Dunkel, Wald, Ozean) + custom colors
- **Bilingual** German/English UI with one-click language switching
- **REST API** for random quotes (`/api/random`)

## Quick Start with Docker

```bash
cp .env.example .env
# Edit .env with your values (SECRET_KEY, passwords)

# Place zitate.sql in data/ directory
docker compose up -d
```

The app auto-imports quotes on first startup and creates an admin user from environment variables.

## Development

```bash
pip install -r requirements.txt

# Run tests
FLASK_TESTING=1 python3 -m pytest tests/ -v

# Run locally
export SECRET_KEY=dev-secret FLASK_TESTING=1 SQLALCHEMY_DATABASE_URI=sqlite:///dev.db
cd app && flask run
```

## Admin Access

Default credentials are set via `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables. Access the admin panel at `/admin`.
