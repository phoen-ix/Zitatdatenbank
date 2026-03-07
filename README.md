# Zitatdatenbank

A multilingual (DE/EN) web application for browsing, searching, and managing a collection of ~516,000 quotes (24.6k German + 500k English).

## Features

- **Browse** quotes with pagination, filtering by author/tag, and sorting
- **Search** full-text across quotes, authors, and tags
- **Author & Tag** listings with quote counts and alphabetical navigation
- **Random Quote** on the landing page with one-click refresh
- **Admin Panel** with quote CRUD, tag management, settings, and backup/restore
- **14 Themes** - 5 static (Klassisch, Modern, Dunkel, Wald, Ozean) + 9 animated (Hacker Terminal, Schreibmaschine, Neon Glow, Pergament, Vaporwave, Nordlichter, Unterwasser, Kosmos, Feuer)
- **Per-theme customization** - all 11 colors and 2 effect values (typing speed, particle count) editable per theme in admin settings
- **Typing animation** on animated themes with per-theme cursor styles and configurable speed
- **Particle effects** - bubbles, stars, embers etc. with configurable count
- **Line break rendering** - `//` in quote text displayed as proper line breaks
- **Bilingual** German/English UI with one-click language switching
- **REST API** for quotes with filtering, search, and pagination

## Performance

Optimized for 500k+ quotes with:

- **Keyset (cursor-based) pagination** — browse pages load in constant time at any depth (page 26100 = 25ms, same as page 1)
- **In-memory caching** (5-min TTL) for stats, theme, tags, settings — eliminates 15+ DB queries per request
- **FastPagination** — skips expensive COUNT queries using N+1 fetch
- **FULLTEXT indexes** on text and author columns (MariaDB)
- **selectinload** for tags — batches N+1 tag queries into a single IN query
- **Cached tag name→ID map** — search finds matching tags in microseconds instead of SQL ILIKE scan

| Route | Response Time |
|-------|--------------|
| Index | 7ms |
| Browse | 87ms |
| Browse deep (page 25000+) | 25ms |
| Authors | 20ms |
| Tags | 3ms |
| Search | 33–100ms |
| Quote detail | 16ms |

## Quick Start with Docker

```bash
cp .env.example .env
# Edit .env with your values (SECRET_KEY, passwords)

docker compose up -d
```

The data files (`data/data.tar.gz`) are extracted automatically on first startup. The app then auto-imports ~24.6k German quotes from `zitate.sql` and ~500k English quotes from `quotes.csv`, runs versioned data cleanup (wiki markup, truncated authors, non-Latin scripts, deduplication via CRC32-indexed hashing), and creates an admin user from environment variables.

## Development

```bash
pip install -r requirements.txt

# Run tests
FLASK_TESTING=1 python3 -m pytest tests/ -v

# Run locally
export SECRET_KEY=dev-secret FLASK_TESTING=1 SQLALCHEMY_DATABASE_URI=sqlite:///dev.db
cd app && flask run
```

## CLI Commands

- `flask import-quotes <path>` — Import quotes from SQL dump
- `flask import-csv <path> --default-tags "tag1,tag2"` — Import quotes from CSV (columns: quote, author, category)
- `flask cleanup-quotes` — Fix wiki markup, truncated authors/categories, non-Latin scripts, deduplication
- `flask create-admin --username X --password Y` — Create admin user

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

## Security

- **CSP** with nonce-based script-src, `frame-ancestors 'none'`, `object-src 'none'`
- **X-Frame-Options: DENY**, **X-Content-Type-Options: nosniff**
- **CSRF** protection on all forms (Flask-WTF)
- **Rate limiting** on login (10/min) and API endpoints (30–60/min) with `X-RateLimit-*` headers
- **Session security** — HttpOnly, SameSite=Lax cookies, 8h timeout
- **Input validation** — numeric bounds, hex color format, filename whitelist, page clamping
- **Open redirect prevention** on login `next` parameter
- **Safe backup restore** — tar member whitelist, no credentials in backup files

## API

All endpoints return JSON and are rate-limited. Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) are included in every response.

### `GET /api/random`

Returns a random quote (30 requests/minute).

```json
{"id": 42, "text": "The only way...", "author": "Albert Einstein", "tags": ["Deutsch", "Philosophie"]}
```

### `GET /api/quotes`

Browse and search quotes with pagination (30 requests/minute).

| Parameter | Description | Default |
|-----------|-------------|---------|
| `page` | Page number | 1 |
| `per_page` | Results per page (1–100) | 20 |
| `author` | Filter by exact author name | — |
| `tag` | Filter by tag name | — |
| `q` | Full-text search in text and author | — |

```json
{"quotes": [...], "page": 1, "per_page": 20, "has_next": true, "has_prev": false}
```

### `GET /api/quotes/<id>`

Returns a single quote by ID (60 requests/minute).

```json
{"id": 42, "text": "The only way...", "author": "Albert Einstein", "tags": ["Deutsch", "Philosophie"]}
```
