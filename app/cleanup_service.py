from __future__ import annotations

import logging
import re
from collections import Counter

from extensions import db
from models import Quote

logger = logging.getLogger(__name__)

# Current cleanup version — bump to re-run on existing installs.
CLEANUP_VERSION = 4

# Map truncated "X Sprichw" -> full "X Sprichwort" with correct gender.
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

# Map "Aus COUNTRY" author -> "Sprichwort aus COUNTRY" (these are proverb origins).
AUS_COUNTRY_MAP = {
    'Aus Afrika': 'Sprichwort aus Afrika',
    'Aus Ägypten': 'Sprichwort aus Ägypten',
    'Aus Albanien': 'Sprichwort aus Albanien',
    'Aus Amerika': 'Sprichwort aus Amerika',
    'Aus Arabien': 'Sprichwort aus Arabien',
    'Aus Armenien': 'Sprichwort aus Armenien',
    'Aus Äthiopien': 'Sprichwort aus Äthiopien',
    'Aus Bayern': 'Sprichwort aus Bayern',
    'Aus Bosnien': 'Sprichwort aus Bosnien',
    'Aus Bosnien und Kroatien': 'Sprichwort aus Bosnien und Kroatien',
    'Aus Brasilien': 'Sprichwort aus Brasilien',
    'Aus Bulgarien': 'Sprichwort aus Bulgarien',
    'Aus Burundi': 'Sprichwort aus Burundi',
    'Aus China': 'Sprichwort aus China',
    'Aus China und aus Japan': 'Sprichwort aus China und Japan',
    'Aus Dänemark': 'Sprichwort aus Dänemark',
    'Aus dem Iran': 'Sprichwort aus dem Iran',
    'Aus den Niederlanden': 'Sprichwort aus den Niederlanden',
    'Aus den USA': 'Sprichwort aus den USA',
    'Aus der Schweiz': 'Sprichwort aus der Schweiz',
    'Aus der Türkei': 'Sprichwort aus der Türkei',
    'Aus Deutschand': 'Sprichwort aus Deutschland',
    'Aus Deutschland': 'Sprichwort aus Deutschland',
    'Aus Deutschland 1989': 'Sprichwort aus Deutschland',
    'Aus England': 'Sprichwort aus England',
    'Aus Estland': 'Sprichwort aus Estland',
    'Aus Finnland': 'Sprichwort aus Finnland',
    'Aus Frankreich': 'Sprichwort aus Frankreich',
    'Aus Friaul': 'Sprichwort aus Friaul',
    'Aus Georgien': 'Sprichwort aus Georgien',
    'Aus Griechenland': 'Sprichwort aus Griechenland',
    'Aus Indien': 'Sprichwort aus Indien',
    'Aus Irland': 'Sprichwort aus Irland',
    'Aus Italien': 'Sprichwort aus Italien',
    'Aus Jamaika': 'Sprichwort aus Jamaika',
    'Aus Japan': 'Sprichwort aus Japan',
    'Aus Kamerun': 'Sprichwort aus Kamerun',
    'Aus Korea': 'Sprichwort aus Korea',
    'Aus Kroatien': 'Sprichwort aus Kroatien',
    'Aus Litauen': 'Sprichwort aus Litauen',
    'Aus Marokko': 'Sprichwort aus Marokko',
    'Aus Nigeria': 'Sprichwort aus Nigeria',
    'Aus Österreich': 'Sprichwort aus Österreich',
    'Aus Pakistan': 'Sprichwort aus Pakistan',
    'Aus Persien': 'Sprichwort aus Persien',
    'Aus Polen': 'Sprichwort aus Polen',
    'Aus Portugal': 'Sprichwort aus Portugal',
    'Aus Rumänien': 'Sprichwort aus Rumänien',
    'Aus Russland': 'Sprichwort aus Russland',
    'Aus Schottland': 'Sprichwort aus Schottland',
    'Aus Schweden': 'Sprichwort aus Schweden',
    'Aus Senegal': 'Sprichwort aus Senegal',
    'Aus Serbien': 'Sprichwort aus Serbien',
    'Aus Sizilien': 'Sprichwort aus Sizilien',
    'Aus Sorben': 'Sprichwort aus Sorben',
    'Aus Spanien': 'Sprichwort aus Spanien',
    'Aus Sumer': 'Sprichwort aus Sumer',
    'Aus Tschechien': 'Sprichwort aus Tschechien',
    'Aus Uganda': 'Sprichwort aus Uganda',
    'Aus Ungarn': 'Sprichwort aus Ungarn',
    'Aus Venedig': 'Sprichwort aus Venedig',
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


def _try_extract_author(text: str) -> str:
    """Extract author from text, returning '' if the result is garbage."""
    extracted = _extract_author_from_text(text)
    if extracted and _is_garbage_author(extracted):
        return ''
    return extracted


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


def _fix_double_corruption(value: str) -> str:
    """Fix Sprichwortort -> Sprichwort (caused by v1 double-replacement bug)."""
    if 'Sprichwortört' in value:
        # Sprichwortörter -> Sprichwörter (plural with umlaut)
        value = value.replace('Sprichwortört', 'Sprichwört')
    if 'Sprichwortort' in value:
        value = value.replace('Sprichwortort', 'Sprichwort')
    return value


def _complete_sprichw(value: str) -> str:
    """Complete truncated Sprichw/Werbespr in a string."""
    # Skip if already fully expanded
    if 'Sprichwort' in value or 'Werbespruch' in value or 'Werbesprüche' in value:
        return value
    if 'Werbespr' in value:
        return value.replace('Werbespr', 'Werbespruch')
    for truncated, full in SPRICHW_MAP.items():
        if truncated in value:
            return value.replace(truncated, full)
    return value


def _strip_wiki_markup(value: str) -> str:
    """Remove wiki markup from a string."""
    # Remove [[...]] wiki links, keeping display text
    value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', value)
    # Remove [[ and ]] remnants (truncated links)
    value = value.replace('[[', '').replace(']]', '')
    # Remove '' wiki bold/italic
    value = value.replace("''''", '').replace("''", '')
    # Remove backtick/accent marks used as wiki formatting
    value = value.replace('`', '').replace('´', '')
    # Remove trailing lone single quote (wiki remnant)
    value = value.strip()
    if value.endswith("'") and not value.endswith("''"):
        value = value[:-1].rstrip()
    return value


def _is_garbage_author(author: str) -> bool:
    """Check if author is a garbage/fragment value that should be cleared."""
    # Punctuation only
    if all(ch in "',;.!?-–— " for ch in author):
        return True
    # Numeric only (page numbers, Bible verse refs like "1", "15", "1797")
    if re.fullmatch(r'[\d.,\s]+', author):
        return True
    # Single character
    if len(author) <= 1:
        return True
    # Two-char fragments (except known abbreviations)
    if len(author) == 2 and author not in ('AT', 'SZ'):
        return True
    # Known truncated fragments
    if author in ('Im', 'in', 'Zu', 'aus', 'und', 'Pap', 'Rep', 'Zit',
                   'Das M', 'Der K', 'In C', 'In t', 'Pro L', 'Joe E',
                   'Phil', 'Prof', 'orig', 'Hallo'):
        return True
    # Starts with 'am ' + digit (truncated date reference)
    if re.match(r'^am \d', author):
        return True
    return False


def _clean_author(author: str, text: str) -> tuple[str, str | None]:
    """Clean author field. Returns (cleaned_author, optional_new_category).

    The second return value is set when the author is really an origin/source
    that should be stored as category instead.
    """
    if not author:
        return (_try_extract_author(text), None)

    # Fix double-corruption from v1 bug (Sprichwortort -> Sprichwort)
    author = _fix_double_corruption(author)

    # Exact match: '''' (wiki artifact for "no author")
    if author == "''''":
        return (_try_extract_author(text), None)

    # Strip wiki markup from author
    cleaned = _strip_wiki_markup(author)
    if cleaned != author:
        author = cleaned
    if not author:
        return (_try_extract_author(text), None)

    # Starts with '' (wiki bold prefix on name) - catch any remaining
    if author.startswith("'"):
        author = author.lstrip("'")
        if not author:
            return (_try_extract_author(text), None)

    # Garbage authors (single char, numeric, punctuation, known fragments)
    if _is_garbage_author(author):
        return (_try_extract_author(text), None)

    # Strip truncated parentheticals early (before Sprichw check)
    # e.g. "Arabisches Sprichwort (16" -> "Arabisches Sprichwort"
    if '(' in author and ')' not in author:
        clean = re.sub(r'\s*\(.*$', '', author).strip()
        if clean and len(clean) > 2:
            author = clean
        else:
            return ('', None)

    # Sprichw/Werbespr completion
    if 'Sprichw' in author or 'Werbespr' in author:
        return (_complete_sprichw(author), None)

    # Zitat des Tages/Archiv -> move to category, extract author from text
    if author.startswith('Zitat des Tages'):
        return (_try_extract_author(text), author)

    # "Zitat des/von NAME" -> extract NAME
    m = re.match(r'^Zitat (?:des|von) (.+)', author)
    if m:
        return (m.group(1).strip(), None)

    # "Aus COUNTRY" -> convert to "Sprichwort aus COUNTRY"
    # First try exact match in map
    if author in AUS_COUNTRY_MAP:
        return (AUS_COUNTRY_MAP[author], None)
    # Handle "Aus Country (truncated..." - strip parenthetical, then match
    if re.match(r'^Aus [A-ZÄÖÜ]', author):
        base = re.sub(r'\s*\(.*$', '', author).strip()
        if base in AUS_COUNTRY_MAP:
            return (AUS_COUNTRY_MAP[base], None)
        # "Aus Rußland und Aus Deutschland" -> just use generic
        if ' und ' in author:
            return ('Sprichwort', None)
        # "Aus Deutschland(Name)" -> extract name
        m = re.match(r'^Aus \w+\((.+?)\)$', author)
        if m:
            return (m.group(1).strip(), None)
        # Remaining "Aus X" -> generic sprichwort
        return ('Sprichwort aus ' + base.replace('Aus ', ''), None)
    # "aus ..." lowercase (fragment references, not country origins)
    if author.startswith('aus '):
        return ('', None)

    # "nach NAME" -> extract NAME as author
    m = re.match(r'^nach (\w.+)', author)
    if m:
        name = m.group(1).strip()
        # "nach der Schlacht..." is not an author
        if name[0].isupper() and not name.startswith(('der ', 'einer ', 'dem ')):
            return (name, None)
        return ('', None)

    # Attribution: "X zugeschrieben" or "X fälschlich zugeschrieben"
    m = re.match(r'^(.+?)\s*\(?(?:fälschlich\s+)?zugeschrieben', author)
    if m:
        candidate = m.group(1).strip()
        # Skip if candidate is a meta-phrase not a name
        if candidate and candidate[0].isupper() and len(candidate) > 3:
            return (candidate, None)
        return ('', None)
    # "Fälschlich X zugeschrieben" or "Häufig X zugeschrieben"
    m = re.match(r'^(?:Fälschlich|Häufig|Obwohl regelmäßig)\s+(?:\S+\s+)*?(\w[\w\s.]+?)\s+(?:fälschlich\s+)?zugeschrieben', author)
    if m:
        candidate = m.group(1).strip()
        if len(candidate) > 3:
            return (candidate, None)

    # "basierend auf ..." -> clear (it's a source, not an author)
    if author.startswith('basierend auf'):
        return ('', None)

    # Fragment authors: starts with ', ' or '; '
    if author.startswith(', ') or author.startswith('; '):
        return ('', None)

    # Starts with '(' - truncated parenthetical fragments
    if author.startswith('('):
        # "(Johann König)" -> extract name
        m = re.match(r'^\(([A-ZÄÖÜ][\w\s.]+)\)$', author)
        if m:
            return (m.group(1).strip(), None)
        # "(Vor-)Letzte Worte" -> keep as-is (it's a source type)
        if 'Worte' in author or 'Rede' in author:
            return (author, None)
        # Other truncated parens -> clear
        return ('', None)

    # Reference fragments containing 'vgl'
    if 'vgl' in author.lower():
        return ('', None)
        return ('', None)

    return (author, None)


def _clean_category(category: str) -> str:
    """Clean category field."""
    if not category:
        return ''

    # Fix double-corruption from v1 bug
    category = _fix_double_corruption(category)

    # Strip wiki markup
    cleaned = _strip_wiki_markup(category)
    if cleaned != category:
        category = cleaned

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

        # If author was an origin label, move to category
        if new_cat is not None:
            stats['author_to_category'] += 1
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
