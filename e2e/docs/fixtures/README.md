# Demo quotes for the docs tour

`e2e/docs/seed.ts` imports these into the throwaway docs stack with `flask import-csv`
(columns `quote,author,category`; the category is a comma-separated tag list). They are a small
sample of the app's own data in `data/data.tar.gz`, with the same tags a production install gives
them:

| File | Rows | Source | License | Default tags |
|------|------|--------|---------|--------------|
| `quotes-de.csv` | 44 | `zitate.sql`, Zitatdatenbank on datenbörse.net (category = its topic) | CC BY-SA 3.0 | Deutsch, German, Quelle: Zitatdatenbank |
| `quotes-en.csv` | 59 | `quotes.csv`, Quotes 500K on Kaggle (a few common topic tags kept) | CC0 | English, Englisch, Source: Kaggle |

Keep the whole set under 200 rows. The tour looks up some rows by author and opening words
(Oscar Wilde "To live is the rarest thing…", Mark Twain "Good friends, good books…"), and the
screenshots show them.
