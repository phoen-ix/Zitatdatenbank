# E2E coverage

Inventory of every user-facing route, feature, form, action and error state, and the test that covers it
(`<spec> › [<describe> ›] <title>` for `e2e/tests/<spec>.spec.ts`; `sweep › guest/admin` = the four sweep tests; run with `scripts/e2e.sh`). ❌ rows give one reason: (a) needs hardware or an
external account, (b) irreversible external effect, (c) covered at another layer (test cited), (d) cannot be
driven, (e) time-box overrun.

Extracted 2026-10-31 from:
- routes: `cd app && FLASK_TESTING=1 flask routes` (29 rules)
- forms, buttons, confirms, menus: `grep -rnE '<form|<button|data-confirm|data-autosubmit|data-bs-toggle' app/templates`
- messages and error states: `grep -nE "flash\(|errorhandler|abort\(" app/app.py app/routes/*.py`

**122 items (55 route × role cells, 67 features, forms, actions and error states): 115 ✅, 7 ❌, all (c).** Roles: guest (not signed in) and admin (the only account type).
Languages: German (default) and English.

## Routes × roles (breadth: `sweep.spec.ts`)

Every page as guest and admin, in German and English: own heading or landmark, no page error, no console
error (CSP), no 5xx, no failed CSS/JS/font/icon request. Guests' admin routes are checked as 302 to
`/login?next=…` (one followed in full: `auth.spec.ts › a guest who opens an admin page is asked to sign in`).

| Route | Methods | Guest | Admin |
|---|---|---|---|
| `/` | GET | ✅ sweep › guest (de/en) | ✅ sweep › admin (de/en) |
| `/browse` (+ `sort`, `page`, `author`, `tag`) | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/browse/authors` (+ `letter`) | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/browse/tags` (+ `page`) | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/search` (empty, `q`) | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/quote/<id>` (known, unknown) | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/credits` | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/login` | GET | ✅ sweep › guest | ✅ sweep › admin (on to the dashboard) |
| `/login` | POST | ✅ auth › the admin signs in from the navbar and out again | — (signed in: redirect, swept) |
| `/logout` | GET | ✅ sweep › guest | ✅ sweep › admin |
| `/set-lang/<lang>` | GET | ✅ public › the language switch keeps the page and lasts for the session | ✅ sweep › admin (en) |
| `/admin/` | GET | ✅ sweep › guest (302) | ✅ sweep › admin |
| `/admin/quotes` (+ `q`, `cursor`) | GET | ✅ sweep › guest (302) | ✅ sweep › admin |
| `/admin/quotes/add` | GET, POST | ✅ sweep › guest (302) | ✅ admin › quotes › add a quote with author and tags; it shows in the list and on the site |
| `/admin/quotes/<id>/edit` | GET, POST | ✅ sweep › guest (302) | ✅ admin › quotes › edit a quote: new text, author and tags; a blank text keeps the old one |
| `/admin/quotes/<id>/delete` | POST | ✅ auth › a guest cannot change anything by posting to an admin action | ✅ admin › quotes › delete a quote after one confirmation; dismissing it keeps the quote |
| `/admin/tags` (+ `q`, `page`) | GET | ✅ sweep › guest (302) | ✅ sweep › admin |
| `/admin/tags/add` | POST | ✅ (same `before_request` guard as every admin route; auth › a guest cannot change anything by posting to an admin action) | ✅ admin › tags › add a tag; a duplicate is refused; the filter finds it; delete it |
| `/admin/tags/<id>/delete` | POST | ✅ (guard, see above) | ✅ admin › tags › add a tag; a duplicate is refused; the filter finds it; delete it |
| `/admin/settings` | GET, POST | ✅ sweep › guest (302) | ✅ global › site name and quotes per page apply to every visitor; an empty name falls back |
| `/admin/backup` | GET | ✅ sweep › guest (302) | ✅ sweep › admin |
| `/admin/backup/create` | POST | ✅ (guard, see above) | ✅ global › backup › create a backup, download it, restore it (later changes are gone), delete it |
| `/admin/backup/<f>/download` | GET | ✅ (guard, see above) | ✅ global › backup › create a backup, download it, restore it (later changes are gone), delete it |
| `/admin/backup/<f>/restore` | POST | ✅ (guard, see above) | ✅ global › backup › create a backup, download it, restore it (later changes are gone), delete it |
| `/admin/backup/<f>/delete` | POST | ✅ (guard, see above) | ✅ global › backup › create a backup, download it, restore it (later changes are gone), delete it |
| `/api/random` | GET | ✅ api › GET /api/random returns one quote, with rate-limit headers and no CSP | — (same for everyone) |
| `/api/quotes` | GET | ✅ api › GET /api/quotes filters by author, tag and text, pages, and caps per_page | — |
| `/api/quotes/<id>` | GET | ✅ api › GET /api/quotes/<id> returns the quote; unknown ids and routes are JSON 404s | — |
| `/health` | GET | ✅ api › GET /health reports the database | — |
| `/static/<path>` | GET | ✅ every test (failed subresources fail the test, `support.ts`) | ✅ |

## Public pages (depth: `public.spec.ts`, guest, German)

| Feature | Test |
|---|---|
| Home: random quote card, its detail, author and tag links | ✅ public › home › the random quote card links to its detail page, author and tags |
| Home: "Neues Zitat", `Cache-Control: no-store` | ✅ public › home › "Neues Zitat" loads the page again, never from the cache |
| Home: totals (quotes, authors, tags), cache invalidated on writes | ✅ public › home › the totals count a new quote, author and tag at once |
| Home: empty database ("Keine Zitate gefunden.") | ❌ (c) `tests/test_routes.py::test_index_page`, `::test_api_random_empty` (the e2e database is shared, never empty) |
| Navbar links, brand, quick links, footer credits link | ✅ public › home › the navigation, the quick links and the footer reach every section |
| Phone layout: menu folds into the toggler | ✅ public › home › on a phone the menu folds into the toggler |
| Browse: sort menu (4 orders, auto-submit, keeps the filter) | ✅ public › browse › the sort menu orders newest, oldest, author A-Z and Z-A, keeping the tag filter |
| Browse: author filter, tag filter, filter badge, "Filter aufheben", total count | ✅ public › browse › author and tag filters narrow the list; "Filter aufheben" clears them |
| Browse: no matches | ✅ public › browse › a filter without matches says so |
| Browse: cursor pages (Weiter, Zurück, page x / n, "Gehe zu Seite") | ✅ public › browse › all quotes page with Weiter, Zurück and "Gehe zu Seite" (cursor pages) |
| Browse: "Älteste zuerst" cursor pages | ✅ public › browse › "Älteste zuerst" pages forward from the oldest quote |
| Browse: numbered pages of a filtered list | ✅ public › browse › a filtered list pages with numbered links |
| Authors: letter bar, "Alle", count, author → their quotes | ✅ public › authors and tags › the letter bar filters the authors; "Alle" shows them all; an author opens their quotes |
| Authors: pages (Weiter, Zurück, "Gehe zu Seite", letter kept) | ✅ public › authors and tags › more than 50 authors under one letter page with Weiter and "Gehe zu Seite" |
| Tags: counts (most used first), pages, "Gehe zu Seite", tag → its quotes | ✅ public › authors and tags › the tag index counts quotes per tag, pages, and opens a tag |
| Search: navbar search by text word, author, tag; query kept in the box | ✅ public › search › the navbar search finds a quote by a word of its text, its author or its tag |
| Search page: own form, empty query, no results | ✅ public › search › the search page has its own form; no hits and an empty query say so |
| Search: numbered pages, only to pages that exist | ✅ public › search › more than 20 hits page with numbered links, and only to pages that exist |
| Search: FULLTEXT operators, `%`/`_`, markup in the query | ✅ public › search › FULLTEXT operators and markup in a query are plain text |
| Quote detail: text, `//` line break, author, tags, number, more by the author, back link | ✅ public › quote detail › shows text, author, tags, number, more quotes by the author, and a way back |
| Quote detail: no author ("Unbekannt"), markup stays text | ✅ public › quote detail › a quote without author says "Unbekannt"; markup in a quote stays text |
| Quote detail: unknown number (404 + message) | ✅ public › quote detail › an unknown quote number is a 404 with a message |
| Unknown page: 404 page with a way home | ✅ public › an unknown page is a 404 with a way home |
| Credits: both sources, licences, external links (`_blank`, `noopener`) | ✅ public › credits name both sources and licences, links open in a new tab |
| Language switch DE/EN (keeps the page, session-wide, unknown language ignored, `<html lang>`) | ✅ public › the language switch keeps the page and lasts for the session |
| Language switch: foreign Referer not followed | ❌ (c) `tests/test_routes.py::test_set_lang_no_open_redirect` |

## Sign-in (`auth.spec.ts`)

| Feature | Test |
|---|---|
| Sign in from the navbar, admin links, sign out | ✅ auth › the admin signs in from the navbar and out again |
| Wrong password, unknown user (one message) | ✅ auth › a wrong password or an unknown user is refused with one message |
| Protected page → login → back to that page (`next`) | ✅ auth › a guest sent to the login page lands on the page they asked for |
| Protected page as guest: "Bitte melden Sie sich an.", focus on the username | ✅ auth › a guest who opens an admin page is asked to sign in |
| `next` pointing elsewhere (`https://…`, `javascript:`) is ignored | ❌ (c) `tests/test_admin.py::test_login_open_redirect_blocked`, `tests/test_routes.py::test_login_javascript_redirect_blocked` |
| Guest posting to an admin action | ✅ auth › a guest cannot change anything by posting to an admin action |
| Expired/invalid CSRF token | ✅ auth › a form posted with an expired CSRF token is reloaded with a message, nothing saved |

## Admin: quotes and tags (`admin.spec.ts`, German)

| Feature | Test |
|---|---|
| Dashboard: totals, quick actions (5 links), recent quotes → editor, "Verwaltung" link | ✅ admin › the dashboard counts quotes, authors and tags and links to every admin page |
| Add quote (text, author, tags incl. repeated/blank ones) → list + public page | ✅ admin › quotes › add a quote with author and tags; it shows in the list and on the site |
| Add quote: empty text blocked by the form, blank text refused, other fields kept | ✅ admin › quotes › a quote needs its text: empty is blocked, blank is refused and the form keeps the rest |
| Edit quote (text, author, tags added/removed); blank text refused | ✅ admin › quotes › edit a quote: new text, author and tags; a blank text keeps the old one |
| "Abbrechen" | ✅ admin › quotes › "Abbrechen" leaves a quote as it was |
| Delete quote: one confirmation, dismissed / accepted | ✅ admin › quotes › delete a quote after one confirmation; dismissing it keeps the quote |
| Admin search (text, author, tag), numbered pages of 50 | ✅ admin › quotes › the admin search finds text, authors and tags and pages 50 at a time |
| All quotes: cursor pages of 50, count | ✅ admin › quotes › all quotes page 50 at a time with Weiter and Zurück (cursor pages) |
| Edit an unknown quote number | ✅ admin › quotes › an unknown quote number sends the editor back to the list |
| Add tag, duplicate tag, tag filter, count column, delete tag | ✅ admin › tags › add a tag; a duplicate is refused; the filter finds it; delete it |
| Deleting a tag in use removes it from its quotes | ✅ admin › tags › deleting a tag in use takes it off its quotes |
| Over-long tag name, tag and author (form maxlength, server cut) | ✅ admin › tags › over-long tag names and authors are cut to their column size, not a server error |
| Admin tag list pages | ✅ admin › tags › the tag list pages 50 at a time |
| Toasts: close button, auto-hide after 4 s | ✅ admin › a toast closes with its button and on its own after four seconds |

## Site-wide settings, themes, backups (`global.spec.ts`, runs alone after `main`)

| Feature | Test |
|---|---|
| Site name (navbar, `<title>`, empty → default), quotes per page (browse, search) | ✅ global › site name and quotes per page apply to every visitor; an empty name falls back |
| Quotes per page out of range | ✅ global › quotes per page outside 5-100 is blocked by the form (form); server clamp (500 → 100, 1 → 5, "abc" → 20) ❌ (c) `tests/test_admin.py::test_admin_settings_invalid_quotes_per_page` |
| Settings tabs "Allgemein"/"Themen" | ✅ global › the settings tabs switch between "Allgemein" and "Themen" |
| Static theme via the card preview; dark theme colours (body, cards, `theme-color`) | ✅ global › a static theme recolours the site; a dark one keeps text readable |
| Animated theme: body class, typing animation, typing speed, particle count | ✅ global › an animated theme adds its effects, which can be tuned |
| Colour override of the current theme (picker ↔ hex field, invalid hex ignored), "Zurücksetzen" | ✅ global › customising the current theme overrides a colour; "Zurücksetzen" restores it |
| Invalid colour or effect values posted directly | ❌ (c) `tests/test_admin.py::test_admin_theme_override_validates_color`, `tests/test_admin.py::test_admin_theme_override_validates_effects` |
| Switching themes drops the new theme's stale overrides | ✅ global › switching to a theme drops the colours once saved for it |
| "Eigene Farben" (custom theme) | ✅ global › "Eigene Farben" builds a theme from the colour fields |
| Backup: create, log, download (gzip), restore (confirm dismissed/accepted, later quote gone), delete | ✅ global › backup › create a backup, download it, restore it (later changes are gone), delete it |
| Backup fails (unwritable `/backups`), restore fails (broken archive) | ✅ global › backup › a backup or restore that fails says why |
| Unknown/malformed backup names (download 404, delete "Backup nicht gefunden.") | ✅ global › backup › unknown or malformed backup names are 404s |
| Restore re-runs cleanup / tag migration only for pre-tag backups | ❌ (c) `tests/test_admin.py::test_restore_reruns_tag_migration_only_for_pre_tag_backups` (asserts `cleanup_version` reset and `tags_migrated`) |
| Database down: 500 page, `/health` 503 | ✅ global › with the database down, pages show the error page and /health reports it |

## Rate limits (`limits.spec.ts`, runs last)

| Feature | Test |
|---|---|
| Sign-in 10/min → message on a working page | ✅ limits › too many sign-in attempts end on a page that says so |
| Search 30/min → message on a working page | ✅ limits › too many searches end on a page that says so |
| API 30/min → JSON 429, `X-RateLimit-*`, `Retry-After` | ✅ limits › the API answers 429 with JSON once the limit is used up |

## Not in the browser

| Item | |
|---|---|
| CLI `import-csv` | ✅ auth.setup › seed the demo quotes and sign the admin in (imports the fixtures through it, `docs/seed.ts`) |
| CLI `import-quotes`, `cleanup-quotes`, `create-admin` (new and password reset), startup auto-import, `entrypoint.sh` extracting `data/data.tar.gz` | ❌ (c) `tests/test_startup.py::test_cli_import_quotes_and_create_admin`, `tests/test_cleanup.py::TestRunFullCleanup::test_cli_command`, `tests/test_startup.py::test_flask_script_runs_cli_commands`, `tests/test_startup.py::test_auto_import_loads_both_sources_into_an_empty_table`, `tests/test_startup.py::test_entrypoint_extracts_the_data_archive`, `tests/test_startup.py::test_entrypoint_stops_on_an_lfs_pointer` (the e2e stack has no `/data` on purpose: the 516k-quote import takes minutes) |
