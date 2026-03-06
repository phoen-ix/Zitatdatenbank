from __future__ import annotations

import logging
import re
from collections import Counter

from extensions import db
from models import Quote

logger = logging.getLogger(__name__)

# Map truncated "X Sprichw" -> full "X Sprichwort" with correct gender
# The original VARCHAR(255) truncated these nationality-proverb labels.
SPRICHW_MAP = {
    'Afrikanische Sprichw': 'Afrikanisches Sprichwort',
    'Altägyptisches Sprichw': 'Altägyptisches Sprichwort',
    'Arabisches Sprichw': 'Arabisches Sprichwort',
    'Argentinische Sprichw': 'Argentinisches Sprichwort',
    'Armenisches Sprichw': 'Armenisches Sprichwort',
    'Bosnische Sprichw': 'Bosnisches Sprichwort',
    'Brasilianische Sprichw': 'Brasilianisches Sprichwort',
    'Chinesische Sprichw': 'Chinesisches Sprichwort',
    'Chinesisches Sprichw': 'Chinesisches Sprichwort',
    'Deutsche Sprichw': 'Deutsches Sprichwort',
    'Deutsches Sprichw': 'Deutsches Sprichwort',
    'Eifeler Sprichw': 'Eifeler Sprichwort',
    'Englische Sprichw': 'Englisches Sprichwort',
    'Estnische Sprichw': 'Estnisches Sprichwort',
    'Fernöstliches Sprichw': 'Fernöstliches Sprichwort',
    'Finnische Sprichw': 'Finnisches Sprichwort',
    'Georgische Sprichw': 'Georgisches Sprichwort',
    'Griechische Sprichw': 'Griechisches Sprichwort',
    'Griechisches Sprichw': 'Griechisches Sprichwort',
    'Indianische Sprichw': 'Indianisches Sprichwort',
    'Indianisches Sprichw': 'Indianisches Sprichwort',
    'Indische Sprichw': 'Indisches Sprichwort',
    'Iranische Sprichw': 'Iranisches Sprichwort',
    'Iranisches Sprichw': 'Iranisches Sprichwort',
    'Italienische Sprichw': 'Italienisches Sprichwort',
    'Jamaikanische Sprichw': 'Jamaikanisches Sprichwort',
    'Japanische Sprichw': 'Japanisches Sprichwort',
    'Jiddische Sprichw': 'Jiddisches Sprichwort',
    'Jiddisches Sprichw': 'Jiddisches Sprichwort',
    'Klingonisches Sprichw': 'Klingonisches Sprichwort',
    'Koreanische Sprichw': 'Koreanisches Sprichwort',
    'Kroatische Sprichw': 'Kroatisches Sprichwort',
    'Kurdische Sprichw': 'Kurdisches Sprichwort',
    'Kurdisches Sprichw': 'Kurdisches Sprichwort',
    'Lateinische Sprichw': 'Lateinisches Sprichwort',
    'Lateinisches Sprichw': 'Lateinisches Sprichwort',
    'Niederländisches Sprichw': 'Niederländisches Sprichwort',
    'Polnische Sprichw': 'Polnisches Sprichwort',
    'Polnisches Sprichw': 'Polnisches Sprichwort',
    'Portugiesische Sprichw': 'Portugiesisches Sprichwort',
    'Römisches Sprichw': 'Römisches Sprichwort',
    'Russische Sprichw': 'Russisches Sprichwort',
    'Russisches Sprichw': 'Russisches Sprichwort',
    'Schottische Sprichw': 'Schottisches Sprichwort',
    'Schwedische Sprichw': 'Schwedisches Sprichwort',
    'Schweizer Sprichw': 'Schweizer Sprichwort',
    'Serbische Sprichw': 'Serbisches Sprichwort',
    'Serbisches Sprichw': 'Serbisches Sprichwort',
    'Sorbische Sprichw': 'Sorbisches Sprichwort',
    'Spanische Sprichw': 'Spanisches Sprichwort',
    'Spanisches Sprichw': 'Spanisches Sprichwort',
    'Sumerisches Sprichw': 'Sumerisches Sprichwort',
    'Tschechische Sprichw': 'Tschechisches Sprichwort',
    'Türkisches Sprichw': 'Türkisches Sprichwort',
    'Ungarische Sprichw': 'Ungarisches Sprichwort',
    'Venezianische Sprichw': 'Venezianisches Sprichwort',
    'Vorarlberger Sprichw': 'Vorarlberger Sprichwort',
    'Wallonisches Sprichw': 'Wallonisches Sprichwort',
    'Sprichw': 'Sprichwort',
}


def _extract_author_from_text(text: str) -> str:
    """Try to extract author from quote text (after ' - ')."""
    match = re.search(r'" - ([^"]+?)(?:\.|,|$)', text)
    if match:
        author_part = match.group(1).strip()
        for sep in [',', ':', ';', '.']:
            if sep in author_part:
                candidate = author_part.split(sep)[0].strip()
                if len(candidate) > 2:
                    return candidate
        return author_part[:200] if len(author_part) > 200 else author_part
    return ''


def _clean_text(text: str) -> str:
    """Clean wiki markup and whitespace from quote text."""
    # Strip '''' first (double-bold wiki markup), then '' (bold/italic)
    text = text.replace("''''", '')
    text = text.replace("''", '')
    # Replace &nbsp; with space
    text = text.replace('&nbsp;', ' ')
    # Collapse multiple spaces to single
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def _complete_sprichw(value: str) -> str:
    """Complete truncated Sprichw/Werbespr in a string."""
    if 'Werbespr' in value and 'Werbespruch' not in value and 'Werbesprüche' not in value:
        return value.replace('Werbespr', 'Werbespruch')
    # Try longest match first (e.g. "Deutsche Sprichw" before "Sprichw")
    for truncated, full in SPRICHW_MAP.items():
        if truncated in value:
            return value.replace(truncated, full)
    return value


def _clean_author(author: str, text: str) -> tuple[str, str | None]:
    """Clean author field. Returns (cleaned_author, optional_new_category).

    The second return value is a new category only when 'Zitat des Tages' is moved.
    """
    if not author:
        extracted = _extract_author_from_text(text)
        return (extracted, None)

    # Exact match: '''' (wiki artifact for "no author")
    if author == "''''":
        extracted = _extract_author_from_text(text)
        return (extracted, None)

    # Starts with '' (wiki bold prefix on name)
    if author.startswith("''") and author != "''''":
        author = author.lstrip("'")
        if not author:
            return (_extract_author_from_text(text), None)

    # Sprichw/Werbespr completion
    if 'Sprichw' in author or 'Werbespr' in author:
        return (_complete_sprichw(author), None)

    # Zitat des Tages/Archiv -> move to category, extract author from text
    if author.startswith('Zitat des Tages'):
        extracted = _extract_author_from_text(text)
        return (extracted, author)

    # Fragment authors: starts with ', ' or '; '
    if author.startswith(', ') or author.startswith('; '):
        return ('', None)

    # Reference fragments containing 'vgl'
    if 'vgl' in author.lower():
        return ('', None)

    return (author, None)


def _clean_category(category: str) -> str:
    """Clean category field."""
    if not category:
        return ''

    # Sprichw/Werbespr completion
    if 'Sprichw' in category or 'Werbespr' in category:
        return _complete_sprichw(category)

    # Truncated categories: <=3 chars starting with uppercase -> clear
    if len(category) <= 3 and category[0].isupper():
        return ''

    return category


def run_full_cleanup() -> dict[str, int]:
    """Run all cleanup steps on the quote database. Returns a stats dict."""
    stats: Counter = Counter()

    # --- Text cleanup (all quotes) ---
    all_quotes = Quote.query.all()
    stats['total_quotes'] = len(all_quotes)

    for quote in all_quotes:
        # Text cleanup
        new_text = _clean_text(quote.text)
        if new_text != quote.text:
            stats['text_cleaned'] += 1
            quote.text = new_text

        # Author cleanup
        new_author, new_cat = _clean_author(quote.author or '', quote.text)
        new_author = new_author.strip()
        old_author = (quote.author or '').strip()
        if new_author != old_author:
            stats['author_cleaned'] += 1
            quote.author = new_author

        # If Zitat des Tages was moved to category
        if new_cat is not None:
            stats['zitat_des_tages_moved'] += 1
            if not quote.category or quote.category == old_author:
                quote.category = new_cat

        # Category cleanup
        new_category = _clean_category(quote.category or '')
        if new_category != (quote.category or ''):
            stats['category_cleaned'] += 1
            quote.category = new_category

    db.session.flush()
    logger.info('Text/author/category cleanup done: %s', dict(stats))

    # --- Dedup: exact text duplicates ---
    text_groups = (
        db.session.query(Quote.text, db.func.count(Quote.id), db.func.min(Quote.id))
        .group_by(Quote.text)
        .having(db.func.count(Quote.id) > 1)
        .all()
    )
    for text_val, count, min_id in text_groups:
        dupes = Quote.query.filter(Quote.text == text_val, Quote.id != min_id).all()
        for dupe in dupes:
            db.session.delete(dupe)
            stats['duplicates_deleted'] += 1

    db.session.flush()
    logger.info('Dedup done: %d duplicates deleted', stats['duplicates_deleted'])

    # --- Garbage quotes: empty or placeholder text ---
    garbage = Quote.query.filter(
        db.or_(
            Quote.text == '',
            Quote.text.is_(None),
            db.func.length(db.func.trim(Quote.text)) == 0,
        )
    ).all()
    for g_quote in garbage:
        db.session.delete(g_quote)
        stats['garbage_deleted'] += 1

    db.session.commit()
    logger.info('Cleanup complete: %s', dict(stats))
    return dict(stats)
