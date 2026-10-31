# Screenshot gallery

Every screen of Zitatdatenbank, taken by the docs tour (`e2e/docs/tour.spec.ts`) against a
throwaway stack with ~100 sample quotes (`e2e/docs/fixtures/`). The UI is English except for the
first image. The language link in the navigation bar (`EN` / `DE`) switches the language for the session.
Regenerate them all with `scripts/docs-screenshots.sh` (see the README, "Screenshots").

## Home (German)

The start page in the default language: a random quote with its author and tags, **Neues Zitat**
for another one, the totals, and shortcuts to browse quotes, authors and tags.

<img src="public-home.de.png" alt="German home page with a random quote, totals and shortcuts" width="800">

## Home

The same page in English. Every visit (or **New Quote**) picks another quote at random.

<img src="public-home.png" alt="English home page with a random quote, totals and shortcuts" width="800">

## Home on a phone

The layout is responsive: on narrow screens the navigation bar collapses into the menu button and
the cards stack.

<img src="public-home.mobile.png" alt="Home page on a 390 px wide phone screen" width="390">

## Browse

All quotes, newest first, 20 per page by default (**Settings → Quotes per Page**). Authors and
tags link to filtered lists. The sort menu re-sorts the list: newest or oldest first, author A-Z
or Z-A.

<img src="public-browse.png" alt="Browse page: list of quotes with authors, tags and the sort menu" width="800">

## Browse by tag

A tag or author link filters the list. The badge shows the active filter, **Clear** removes it.

<img src="public-browse-tag.png" alt="Browse page filtered by the tag humor" width="800">

## Authors

Every author with the number of quotes, alphabetically, with a letter bar to jump to an initial.

<img src="public-authors.png" alt="Author list with quote counts and the A-Z letter bar" width="800">

## Tags

Every tag with the number of quotes, most used first (equally used ones alphabetically).

<img src="public-tags.png" alt="Tag list with quote counts" width="800">

## Search

The search field in the navigation bar searches quote text, authors and tag names.

<img src="public-search.png" alt="Search results for the word life" width="800">

## Search without results

<img src="public-search-empty.png" alt="Search page saying no results were found" width="800">

## Quote detail

One quote with its tags and number, plus more quotes by the same author.

<img src="public-quote.png" alt="Quote detail page with tags and more quotes by Oscar Wilde" width="800">

## Credits & License

Where the quotes come from and their licenses (CC BY-SA 3.0 for the German, CC0 for the English
quotes). Linked from the footer.

<img src="public-credits.png" alt="Credits and license page" width="800">

## Page not found

<img src="error-404.png" alt="404 page not found" width="800">

## Login

The admin login (**Login** in the navigation bar). The account comes from `ADMIN_USERNAME` /
`ADMIN_PASSWORD`.

<img src="auth-login.png" alt="Login form with username and password" width="800">

## Admin dashboard

Totals, quick actions and the most recently added quotes.

<img src="admin-dashboard.png" alt="Admin dashboard with totals, quick actions and recent quotes" width="800">

## Manage quotes

All quotes, 50 per page, with search, **Add Quote**, edit and delete.

<img src="admin-quotes.png" alt="Admin quote list with search, edit and delete buttons" width="800">

## Edit quote

Text (`//` becomes a line break), author and comma-separated tags. Missing tags are created on save.

<img src="admin-quote-edit.png" alt="Edit form for a Mark Twain quote with text, author and tags" width="800">

## Manage tags

Add a tag, filter the list, delete a tag (its quotes stay, only the tag is removed).

<img src="admin-tags.png" alt="Admin tag list with quote counts, add and delete" width="800">

## Settings: General

Site name (shown in the navigation bar and page titles) and quotes per page (5-100).

<img src="admin-settings.png" alt="General settings: site name and quotes per page" width="800">

## Settings: Themes

Click one of the 14 themes (animated ones are marked with sparkles) or **Custom Colors** and save.
Then the 11 colors and, for animated themes, typing speed and particle count of the active theme
can be changed with the color pickers or as hex values and saved. **Reset to Defaults** drops the
active theme's changes.

<img src="admin-settings-themes.png" alt="Theme settings: theme picker and the color fields" width="800">

## Backup

**Create Backup** writes a `mysqldump` of the quotes and tags to `/backups` (the `./backups` mount).
Each backup can be downloaded, restored or deleted. The log lists every run.

<img src="admin-backup.png" alt="Backup page with one backup and its log entry" width="800">

## Themes

The same quote page in every theme. Animated themes type the quote letter by letter and some add
particles (bubbles, stars, embers). The screenshots are taken with reduced motion, so they show
the finished text without particles in flight.

### Klassisch (default)
<img src="theme-klassisch.png" alt="Quote detail in the Klassisch theme" width="800">

### Modern
<img src="theme-modern.png" alt="Quote detail in the Modern theme" width="800">

### Dunkel
<img src="theme-dunkel.png" alt="Quote detail in the Dunkel theme" width="800">

### Wald
<img src="theme-wald.png" alt="Quote detail in the Wald theme" width="800">

### Ozean
<img src="theme-ozean.png" alt="Quote detail in the Ozean theme" width="800">

### Hacker Terminal (animated)
<img src="theme-hacker.png" alt="Quote detail in the animated Hacker Terminal theme" width="800">

### Schreibmaschine (animated)
<img src="theme-typewriter.png" alt="Quote detail in the animated Schreibmaschine theme" width="800">

### Neon Glow (animated)
<img src="theme-neon.png" alt="Quote detail in the animated Neon Glow theme" width="800">

### Pergament (animated)
<img src="theme-pergament.png" alt="Quote detail in the animated Pergament theme" width="800">

### Vaporwave (animated)
<img src="theme-vaporwave.png" alt="Quote detail in the animated Vaporwave theme" width="800">

### Nordlichter (animated)
<img src="theme-aurora.png" alt="Quote detail in the animated Nordlichter theme" width="800">

### Unterwasser (animated)
<img src="theme-unterwasser.png" alt="Quote detail in the animated Unterwasser theme" width="800">

### Kosmos (animated)
<img src="theme-kosmos.png" alt="Quote detail in the animated Kosmos theme" width="800">

### Feuer (animated)
<img src="theme-feuer.png" alt="Quote detail in the animated Feuer theme" width="800">
