# Zitatdatenbank

A multilingual (DE/EN) web application for browsing, searching, and managing a collection of ~24,623 German quotes.

## Features

- **Browse** quotes with pagination, filtering by author/category, and sorting
- **Search** full-text across quotes, authors, and categories
- **Author & Category** listings with quote counts and alphabetical navigation
- **Random Quote** on the landing page with one-click refresh
- **Admin Panel** with quote CRUD, settings management, and backup/restore
- **14 Themes** - 5 static (Klassisch, Modern, Dunkel, Wald, Ozean) + 9 animated (Hacker Terminal, Schreibmaschine, Neon Glow, Pergament, Vaporwave, Nordlichter, Unterwasser, Kosmos, Feuer)
- **Per-theme customization** - all 11 colors and 2 effect values (typing speed, particle count) editable per theme in admin settings
- **Typing animation** on animated themes with per-theme cursor styles and configurable speed
- **Particle effects** - bubbles, stars, embers etc. with configurable count
- **Line break rendering** - `//` in quote text displayed as proper line breaks
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

## Themes

| Static | Animated |
|--------|----------|
| Klassisch | Hacker Terminal |
| Modern | Schreibmaschine |
| Dunkel | Neon Glow |
| Wald | Pergament |
| Ozean | Vaporwave |
| | Nordlichter |
| | Unterwasser |
| | Kosmos |
| | Feuer |

All theme colors and effects are customizable per-theme through the admin settings UI. Animated themes include typing animations and particle effects (bubbles, stars, embers) with configurable speed and count.
