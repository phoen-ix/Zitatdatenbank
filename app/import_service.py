from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Category values that indicate a source type (proverbs, tongue twisters, ad slogans, etc.)
SOURCE_KEYWORDS = (
    'Sprichw', 'Zungenbrecher', 'Werbespr', 'Bauernregel',
    'Kinderreim', 'Abzählreim', 'Volksmund', 'Redewendung',
)


def parse_sql_inserts(sql_text: str) -> list[tuple[int, str, str]]:
    """Parse INSERT statements from the SQL dump, returning (id, zitat, autor_herkunft_thema) tuples."""
    rows: list[tuple[int, str, str]] = []
    length = len(sql_text)

    # Only parse after VALUES keywords to avoid matching CREATE TABLE etc.
    search_start = 0
    while True:
        values_idx = sql_text.find('VALUES', search_start)
        if values_idx == -1:
            values_idx = sql_text.find('values', search_start)
        if values_idx == -1:
            break

        i = values_idx + 6  # skip past "VALUES"

        while i < length:
            # Find start of a row tuple
            idx = sql_text.find('(', i)
            if idx == -1:
                break

            after_paren = idx + 1
            while after_paren < length and sql_text[after_paren] in ' \t\n\r':
                after_paren += 1

            if after_paren >= length or not sql_text[after_paren].isdigit():
                i = idx + 1
                continue

            # Parse the id
            num_start = after_paren
            while after_paren < length and sql_text[after_paren].isdigit():
                after_paren += 1
            # Must be followed by comma to be a data row
            rest = sql_text[after_paren:after_paren + 5].lstrip()
            if not rest.startswith(','):
                i = idx + 1
                continue
            row_id = int(sql_text[num_start:after_paren])

            # Skip to first quote (the zitat field)
            quote_start = sql_text.find("'", after_paren)
            if quote_start == -1:
                i = after_paren
                break

            zitat, end_pos = _parse_sql_string(sql_text, quote_start)
            if zitat is None:
                i = after_paren
                continue

            # Skip to next quote (the autor_herkunft_thema field)
            quote_start2 = sql_text.find("'", end_pos)
            if quote_start2 == -1:
                i = end_pos
                break

            category, end_pos2 = _parse_sql_string(sql_text, quote_start2)
            if category is None:
                i = end_pos
                continue

            rows.append((row_id, zitat, category))
            i = end_pos2

            # Check if this INSERT statement ended (semicolon after closing paren)
            tail = sql_text[end_pos2:end_pos2 + 10].lstrip()
            if tail.startswith(';'):
                break

        search_start = i if i > values_idx + 6 else values_idx + 6

    return rows


def _parse_sql_string(sql_text: str, start: int) -> tuple[str | None, int]:
    """Parse a SQL single-quoted string starting at position start. Returns (string, end_position)."""
    if sql_text[start] != "'":
        return None, start

    i = start + 1
    length = len(sql_text)
    chars: list[str] = []

    while i < length:
        ch = sql_text[i]
        if ch == "'":
            # Check for escaped quote ''
            if i + 1 < length and sql_text[i + 1] == "'":
                chars.append("'")
                i += 2
            else:
                # End of string
                return ''.join(chars), i + 1
        elif ch == '\\':
            # Handle backslash escapes
            if i + 1 < length:
                next_ch = sql_text[i + 1]
                if next_ch == "'":
                    chars.append("'")
                elif next_ch == '\\':
                    chars.append('\\')
                elif next_ch == 'n':
                    chars.append('\n')
                elif next_ch == 'r':
                    chars.append('\r')
                elif next_ch == 't':
                    chars.append('\t')
                else:
                    chars.append(next_ch)
                i += 2
            else:
                chars.append(ch)
                i += 1
        else:
            chars.append(ch)
            i += 1

    return None, i


def classify_and_extract(zitat: str, category: str) -> tuple[str, str]:
    """Classify the category field and extract the best author.

    Returns (author, category).
    """
    category = category.strip()

    if not category:
        author = _extract_author_from_text(zitat)
        return (author, '')

    # Check if category is a source keyword (proverb, tongue twister, etc.)
    for kw in SOURCE_KEYWORDS:
        if kw.lower() in category.lower():
            return (category, category)

    # Check if category text appears in the quote text as attribution (after " - ")
    author_from_text = _extract_author_from_text(zitat)

    # If the category is a single word and doesn't look like an author name,
    # it's likely a topic keyword
    words = category.split()
    if len(words) == 1:
        # Single word - likely a topic. Try to get author from text.
        if author_from_text:
            return (author_from_text, category)
        return ('', category)

    # Multi-word: check if it appears in the attribution part
    if author_from_text and _fuzzy_match(category, author_from_text):
        return (category, category)

    # Multi-word that's not in attribution: assume it's an author name
    return (category, category)


def _extract_author_from_text(text: str) -> str:
    """Try to extract author from the quote text (typically after ' - ')."""
    # Look for attribution pattern: " - Author Name"
    # The dash pattern commonly used in these quotes
    match = re.search(r'" - ([^"]+?)(?:\.|,|$)', text)
    if match:
        author_part = match.group(1).strip()
        # Take just the author name (before any work title or source reference)
        # Common patterns: "Author, Work Title" or "Author: Work"
        for sep in [',', ':', ';', '.']:
            if sep in author_part:
                candidate = author_part.split(sep)[0].strip()
                if len(candidate) > 2:
                    return candidate
        return author_part[:200] if len(author_part) > 200 else author_part
    return ''


def _fuzzy_match(a: str, b: str) -> bool:
    """Check if string a is roughly contained in string b or vice versa."""
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    return a_lower in b_lower or b_lower in a_lower


def import_quotes_from_csv(csv_path: str, default_tag_names: list[str] | None = None) -> int:
    """Import quotes from a CSV file (columns: quote, author, category).

    category is treated as comma-separated tags. default_tag_names are added to every quote.
    Returns count of imported quotes.
    """
    import csv
    from extensions import db
    from models import Quote, Tag

    # Get or create default tags
    default_tags = []
    for name in (default_tag_names or []):
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        default_tags.append(tag)

    # Build tag cache
    tag_cache: dict[str, Tag] = {t.name: t for t in Tag.query.all()}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header
        logger.info('CSV header: %s', header)

        count = 0
        batch_size = 1000
        for row in reader:
            if len(row) < 2:
                continue
            text = row[0].strip()
            if not text:
                continue

            author = row[1].strip() if len(row) > 1 else ''
            # Clean author: remove work title after comma if present
            # e.g. "Author Name, Book Title" -> "Author Name"
            if ', ' in author:
                parts = author.split(', ', 1)
                # If the part after comma starts with uppercase and looks like a title
                # (contains spaces or >20 chars), strip it
                if len(parts[1]) > 15 or parts[1][0:1].isupper():
                    author = parts[0]
            # Truncate overly long authors (malformed CSV rows)
            if len(author) > 200:
                author = author[:200]

            cat_str = row[2].strip() if len(row) > 2 else ''

            quote = Quote(text=text, author=author)
            db.session.add(quote)
            db.session.flush()

            # Assign default tags
            quote.tags = list(default_tags)

            # Parse category tags
            if cat_str:
                for tag_name in cat_str.split(', '):
                    tag_name = tag_name.strip()
                    if not tag_name or len(tag_name) > 100:
                        continue
                    if tag_name not in tag_cache:
                        # Check DB (case-insensitive for MariaDB compat)
                        existing = Tag.query.filter_by(name=tag_name).first()
                        if existing:
                            tag_cache[tag_name] = existing
                        else:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                            db.session.flush()
                            tag_cache[tag_name] = tag
                    if tag_cache[tag_name] not in quote.tags:
                        quote.tags.append(tag_cache[tag_name])

            count += 1
            if count % batch_size == 0:
                db.session.commit()
                logger.info('       Imported %d CSV quotes...', count)

    db.session.commit()
    logger.info('       CSV import complete: %d quotes.', count)
    return count


def import_quotes_from_sql(sql_path: str) -> int:
    """Parse the SQL file and import quotes into the database. Returns count of imported quotes."""
    from extensions import db
    from models import Quote

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_text = f.read()

    rows = parse_sql_inserts(sql_text)
    logger.info('Parsed %d rows from SQL file', len(rows))

    count = 0
    batch_size = 500
    for i, (row_id, zitat, cat) in enumerate(rows):
        author, category = classify_and_extract(zitat, cat)
        quote = Quote(
            id=row_id,
            text=zitat,
            author=author,
            category=category,
        )
        db.session.add(quote)
        count += 1

        if (i + 1) % batch_size == 0:
            db.session.commit()
            logger.info('       Imported %d / %d SQL quotes...', i + 1, len(rows))

    db.session.commit()
    logger.info('       SQL import complete: %d quotes.', count)
    return count
