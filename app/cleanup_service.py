from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter

from extensions import db
from models import Quote

logger = logging.getLogger(__name__)

# Current cleanup version — bump to re-run on existing installs.
CLEANUP_VERSION = 17

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

# Known legitimate single-name authors (historical figures, artists, etc.)
KNOWN_SINGLE_NAMES = {
    'Äsop', 'Ovid', 'Homer', 'Horaz', 'Lenin', 'Plato', 'Saadi',
    'Solon', 'Sunzi', 'Hafes', 'Falco', 'Sting', 'Smudo', 'Jesus',
    'Lukan', 'Galen', 'Wols', 'Thot', 'Curse', 'Torch', 'Alain',
    'Bibel', 'Koran',
}

# Known real names that end in patterns that look truncated but aren't.
# Chinese/Asian names, abbreviations, etc.
REAL_SHORT_ENDINGS = {
    'Lü Bu We', 'Meng Zi', 'Johann Peter Uz', 'Malcolm X', 'Pius X',
    'Franz Joseph I', 'Friedrich Wilhelm I', 'Xerxes I',
}

# Source/reference works: "WorkName Section" → move to category
SOURCE_BOOKS = {
    # Bible books
    'Apostelgeschichte', 'Brief an die Römer', 'Deuteronomium',
    'Epheser', 'Galater', 'Genesis', 'Habakuk', 'Hebräer',
    'Hebräerbrief', 'Hesekiel', 'Hiob', 'Hohelied Salomos',
    'Hoheslied', 'Hosea', 'Jakobus', 'Jeremia', 'Jesaja',
    'Jesus Sirach', 'Johannes', 'Judas', 'Kolosser',
    'Leviticus', 'Levitikus', 'Lukas', 'Markus', 'Matthäus',
    'Micha', 'Obadja', 'Offenbarung', 'Offbarung',
    'Offenbarung des Johannes', 'Philipperbrief',
    'Prediger', 'Prediger Salomo', 'Psalm', 'Psalme',
    'Römer', 'Römerbrief', 'Sprüche', 'Sprüche Salomons',
    'Sprüche Salomos', 'Tobit', 'Zefanja',
    # Classical/literary works with section references
    'Agricola', 'Ars poetica', 'Bescheidenheit',
    'Blütenstaub', 'Blüthenstaub', 'Brutus',
    'Bücher der Geschichte', 'Carmen saeculare', 'Carmina',
    'Diodor', 'Elegiarum liber', 'Elegien Buch', 'Epistulae',
    'Essai sur les Moeurs', 'Fragment', 'Gargantua',
    'Gesammelte Irrtümer', 'Gorgias', 'Historien',
    'Lohn der Wahrheit', 'Metaphysik', 'Metaphysik I',
    'Phaidon', 'Phormio', 'Phädrus', 'Politik',
    'Pro Roscio', 'Vita Augusti', 'Vita Tiberi',
    'Vita divi Claudi',
}

# Encoding fixes: ? replacing non-ASCII characters in original data
ENCODING_FIXES = {
    'Czes?aw Mi?osz': 'Czesław Miłosz',
    'Karel ?apek': 'Karel Čapek',
    'Lech Wa??sa': 'Lech Wałęsa',
    'Matsuo Bash?': 'Matsuo Bashō',
    'Stanis?aw Jerzy Lec': 'Stanisław Jerzy Lec',
    'Stanis?aw Lem': 'Stanisław Lem',
    'Tayyip Erdo?an': 'Tayyip Erdoğan',
    'Mustafa Ceri?': 'Mustafa Cerić',
    'Paula von Preradovi?': 'Paula von Preradović',
    'Wies?aw Brudzi?ski': 'Wiesław Brudziński',
    'Yagy? Munenori': 'Yagyū Munenori',
    'Konstanty Ildefons Ga?czy?ski': 'Konstanty Ildefons Gałczyński',
    'Leszek Ko?akowski': 'Leszek Kołakowski',
    'Dscha?far as-S?diq': 'Dschaʿfar as-Sādiq',
    'Mahm?d Ahmad?-Ne': 'Mahmud Ahmadinedschad',
    'Johannes_XXIII': 'Johannes XXIII.',
}

# Wikiquote disambiguation page descriptors
DISAMBIGUATION_PAGE_TYPES = {
    'Film', 'Fernsehserie', 'Dokumentarfilm',
    'Pflanze', 'Tier', 'Gestein', 'Gesteinssediment',
    'Farbe', 'Philosophie', 'Stadt', 'Raum',
    'Schokoriegel', 'Leuchtmittel', 'Schwarzer',
    'Zeitung', 'politische Gesinnung', 'Wetter',
}

# Known multi-word film/show/work titles not starting with articles
KNOWN_WORK_TITLES = {
    'Babylon 5', 'Es war einmal in Amerika',
    'Fear and Loathing in Las Vegas', 'From Dusk Till Dawn',
    'Ghost in the Shell', 'Ghost in the Shell 2: Innocence',
    'Jagd auf Roter Oktober', 'Jenseits von Schuld und Sühne',
    'Leben und sterben lassen', 'Mein Leben und ich',
    'Mein Name ist Nobody', 'My Big Fat Greek Summer',
    'My Big Fat Greek Wedding', 'Nur noch 60 Sekunden',
    'Per Anhalter durch die Galaxis', 'Reise ans Ende der Nacht',
    'Serengeti darf nicht sterben', 'Spiel mir das Lied vom Tod',
    'Stadien auf des Lebens Weg', 'Stargate SG1',
    'Stirb an einem anderen Tag', 'Terminator 2', 'Terminator 3',
    'Wem die Stunde schl',
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
    """Extract author from text, returning '' if the result is garbage or a work title."""
    extracted = _extract_author_from_text(text)
    if not extracted:
        return ''
    if _is_garbage_author(extracted):
        return ''
    if _is_work_title(extracted):
        return ''
    # Reject all-caps names (brand names, publications like "DEUTSCHE BA")
    if extracted.isupper():
        return ''
    # Reject names containing wiki markup
    if '[[' in extracted or ']]' in extracted:
        return ''
    # Reject very long extractions (source references, not person names)
    if len(extracted) > 60:
        return ''
    # Reject extractions ending in "Nr" (magazine references)
    if extracted.endswith(' Nr'):
        return ''
    # Reject names starting with '(' (parenthetical references)
    if extracted.startswith('('):
        return ''
    # Reject doubled/corrupted entries
    if re.search(r'(.{4,})\1', extracted):
        return ''
    # Reject fragment authors starting with punctuation
    if extracted[0] in ',;.!?':
        return ''
    # Reject "vgl" references
    if 'vgl' in extracted.lower():
        return ''
    # Reject "nach ..." phrases (not person names)
    if extracted.startswith('nach '):
        return ''
    # Reject descriptive phrases starting with "Über"
    if extracted.startswith('Über '):
        return ''
    # Reject source book references (Bible verses, classical work sections)
    m_src = re.match(r'^(.+?)\s+§?\s*(\d[\da-z.,+/-]*)$', extracted)
    if m_src:
        book = re.sub(r'\s*\([^)]+\)', '', m_src.group(1)).strip()
        if book in SOURCE_BOOKS:
            return ''
    # Reject " / " patterns (play/dialogue references)
    if ' / ' in extracted:
        return ''
    # Reject titles with '!'
    if '!' in extracted:
        return ''
    # Reject "Werbespruch für ..." (descriptive, not a name)
    if extracted.startswith('Werbespruch für') or extracted.startswith('Werbespruch von'):
        return ''
    # Reject brand names / company names (contain uppercase acronyms 2+ chars)
    # Pattern: word with 2+ consecutive uppercase letters not at start of a normal name
    if re.search(r'\b[A-Z]{2,}', extracted):
        return ''
    # Apply same cleanup that _clean_author would do:
    # Strip truncated parenthetical endings
    if '(' in extracted and ')' not in extracted:
        extracted = re.sub(r'\s*\(.*$', '', extracted).strip()
        if not extracted:
            return ''
    # Strip truncated name endings
    cleaned = _strip_truncated_name_ending(extracted)
    if cleaned != extracted:
        extracted = cleaned
    # Reject single short words (3-5 chars) unless known figure — likely truncated first names
    if ' ' not in extracted and len(extracted) <= 5 and extracted not in KNOWN_SINGLE_NAMES:
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
    # Remove :w: prefix wiki links
    value = re.sub(r':w:', '', value)
    # Remove [[...]] wiki links, keeping display text
    value = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', value)
    # Remove [[ and ]] remnants (truncated links)
    value = value.replace('[[', '').replace(']]', '')
    # Remove '' wiki bold/italic
    value = value.replace("''''", '').replace("''", '')
    # Remove backtick/accent marks used as wiki formatting
    value = value.replace('`', '').replace('´', '')
    # Remove leading/trailing „" quotation marks
    value = value.strip('„"')
    # Remove trailing lone single quote (wiki remnant)
    value = value.strip()
    if value.endswith("'") and not value.endswith("''"):
        value = value[:-1].rstrip()
    return value


def _has_non_latin_chars(text: str) -> bool:
    """Check if text contains non-Latin script characters (Arabic, CJK, Cyrillic, etc.)."""
    # Allowed Unicode ranges: Basic Latin, Latin Extended, combining marks, common punctuation
    for ch in text:
        if ch.isascii():
            continue
        try:
            name = unicodedata.name(ch, '')
        except ValueError:
            return True
        # Allow Latin-based scripts and common marks
        if any(prefix in name for prefix in (
            'LATIN', 'SPACE', 'HYPHEN', 'DASH', 'APOSTROPHE', 'QUOTATION',
            'COMMA', 'FULL STOP', 'COLON', 'SEMICOLON', 'COMBINING',
            'NO-BREAK', 'MIDDLE DOT', 'MODIFIER', 'RIGHT SINGLE',
            'LEFT SINGLE', 'RIGHT DOUBLE', 'LEFT DOUBLE', 'PRIME',
            'INVERTED', 'CEDILLA', 'DIAERESIS', 'TILDE',
        )):
            continue
        return True
    return False


def _is_sentence_like(text: str) -> bool:
    """Check if text looks like a sentence/quote rather than a person name."""
    if len(text) < 15:
        return False
    lower = text.lower()
    # Starts with lowercase = sentence fragment
    if text[0].islower():
        return True
    # Contains sentence-like markers
    sentence_markers = (' is ', ' are ', ' was ', ' were ', ' will ', ' can ', ' has ',
                        ' have ', ' do ', ' does ', ' the ', ' that ', ' this ',
                        ' your ', ' you ', ' they ', ' not ', " don't", " doesn't",
                        " won't", " can't", " isn't", " aren't",
                        ' ist ', ' sind ', ' hat ', ' nicht ', ' wenn ', ' weil ')
    if any(m in lower for m in sentence_markers):
        return True
    # Ends with period (sentences, not abbreviations)
    if text.endswith('.') and len(text) > 30:
        return True
    # Too many words for a name (more than 8)
    if len(text.split()) > 8:
        return True
    return False


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
    # Two-char fragments
    if len(author) == 2:
        return True
    # Known truncated fragments and non-person authors
    if author in ('Im', 'in', 'Zu', 'aus', 'und', 'Pap', 'Rep', 'Zit',
                   'Das M', 'Der K', 'In C', 'In t', 'Pro L', 'Joe E',
                   'Phil', 'Prof', 'orig', 'Hallo', 'Das Sch', 'Das Unm',
                   'Der gro', 'Mein F',
                   'AT', 'SZ', 'DKV', 'ORF', 'Bild', 'Stern', 'Milka', 'Krug',
                   'In: E', 'Juli'):
        return True
    # Starts with 'am ' + digit (truncated date reference)
    if re.match(r'^am \d', author):
        return True
    # Starts with lowercase (fragment, not a proper name) except known patterns
    if author[0].islower() and not author.startswith(('nach ', 'von ')):
        return True
    # Descriptive phrases that aren't person names
    if re.match(r'^(?:Dieser|Dieses|Rede |Volksmund|Lautsprecherdurchsage|Megaphondurchsage'
                 r'|Titel |Urteil |Während |Fragen zur '
                 r'|Anfang |Ende |Mitte |Sommer |Winter |Herbst |Frühjahr '
                 r'|Januar |Februar |März |April |Mai |Juni |Juli |August '
                 r'|September |Oktober |November |Dezember )', author):
        return True
    return False


def _is_work_title(author: str) -> bool:
    """Check if the author field is actually a work/film/book title, not a person."""
    # Starts with digit (film/work titles like "00 Schneider", "12 Monkeys", "2001:")
    if author[0].isdigit():
        return True
    # Contains '!' (titles/shows, not person names)
    if '!' in author:
        return True
    # Starts with "Im " (German "in dem" contraction)
    if author.startswith('Im '):
        return True
    # Known multi-word titles
    if author in KNOWN_WORK_TITLES:
        return True
    # "Kapitel N" (chapter references)
    if re.match(r'^Kapitel \d', author):
        return True
    # German articles + common work-title patterns
    # These are wikiquote page names for works, not people
    if re.match(r'^(?:Das|Der|Die|Ein|Eine) ', author):
        # Exclude "Der/Die/Das" + person name patterns (rare but possible)
        # Person names after articles: "Der Alte Fritz" -> not a person in our data
        # All of these in our data are work/concept titles
        return True
    # English article titles
    if re.match(r'^(?:A |The )', author):
        return True
    # Latin work titles: "De SOMETHING", "Ad SOMETHING" (lowercase after)
    if re.match(r'^(?:De |Ad |In |Ex |Pro )[a-z]', author):
        return True
    # Religious/literary source texts (not person names)
    # Note: Ilias, Aias, Werke are handled in post-processing (need category swap)
    if author in ('Bibel', 'Koran', 'Yvain'):
        return True
    # Known work titles without articles
    if re.match(r'^(?:Briefe|Annalen|Andria|Episteln|Eklogen|Moralia|Satiren|Fragmente'
                 r'|Nikomachische Ethik|Accattone|American History'
                 r'|Dragonball|Rambo|Blues Brothers|Star Wars'
                 r'|Laelius de amicitia|Orator ad|Quintilian|Tusculanae'
                 r'|Liebesgedichte|Liebeskunst'
                 r'|Frühling und Herbst'
                 r'|In Catilinam'
                 r'|Remedia Amoris|Paradoxa Stoicorum|Cato Maior'
                 r'|Hectors Reise|Star Trek'
                 r'|Glauben und Liebe|Geschichte von'
                 r'|Grundgesetz der'
                 r'|Réflexions ou sentences'
                 r'|Interview (?:im|in |mit ))', author):
        return True
    # "X oder Y" pattern (work titles with alternatives)
    if ' oder ' in author and not _looks_like_person_name(author.split(' oder ')[0].strip()):
        return True
    return False


def _extract_name_from_source_ref(author: str) -> str:
    """Extract person name from a source reference like 'Name in der Zeitung' or 'Name YYYY in...'."""
    # "Name YYYY in ..." or "Name (YYYY) in ..."
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:\(?\d{4}\)?\s+)?(?:in |bei |im |zur |auf |am |vom |zu )'
                 r'(?:der|dem|die|einer|einem|den|seinem|ihrem|seiner|ihrer|diesem|dieser'
                 r'|einem |einer |Bezug|einem|der |dem |die '
                 r'|Interview|Gespräch|Ansprache|Sendung|Pressemitteilung|Antwort|Brief'
                 r'|Bundestagsdebatte|Entgegennahme|Verleihung|Zusammenhang'
                 r'|Fernsehduell|Presseko|Situation|Zukunft)', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        # Must look like a person name (at least 2 words, not too long)
        if ' ' in candidate and len(candidate) < 60 and _looks_like_person_name(candidate):
            return candidate
    # "Name nach EVENT" (person reacting to event, not "nach Name")
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+nach\s+(?:der|dem|einem|einer|seinem|seiner|seinem)\b', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if ' ' in candidate and _looks_like_person_name(candidate):
            return candidate
    # "Name anlässlich/als/gemäß/laut ..."
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:anlässlich|als |gemäß |laut )', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if ' ' in candidate and _looks_like_person_name(candidate):
            return candidate
    # "Name - context" (dash separator)
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+-\s+', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if ' ' in candidate and _looks_like_person_name(candidate):
            return candidate
    # "Name zitiert in/von ..."
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:\(\d{4}\)\s+)?zitiert\s+(?:in|von|bei)\b', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if ' ' in candidate and _looks_like_person_name(candidate):
            return candidate
    # "Name aus Work" (person + their work)
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+aus\s+(?:[A-ZÄÖÜ]|Sämtliche|Gedanken|Rime|nuvens)', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if ' ' in candidate and _looks_like_person_name(candidate):
            return candidate
    # "Name am/vom/zum N" (truncated date reference) → extract name
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:am|vom|zum)\s+\d', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if _looks_like_person_name(candidate):
            return candidate
    # "Name YYYY preposition$" (truncated source reference ending in dangling preposition)
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+\d{4}\s+(?:in|im|bei|auf|am|vom|zu|während)$', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if _looks_like_person_name(candidate):
            return candidate
    # "Name YYYY" at the end (year reference without further context)
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+\(?\d{4}\)?$', author)
    if m:
        candidate = m.group(1).strip().rstrip(',')
        if _looks_like_person_name(candidate):
            return candidate
    return ''


def _extract_name_from_uber(author: str) -> str:
    """Extract person name from 'Name über TOPIC' pattern."""
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+über\s+', author)
    if m:
        candidate = m.group(1).strip()
        if _looks_like_person_name(candidate):
            return candidate
    return ''


def _looks_like_person_name(value: str) -> bool:
    """Heuristic: does this look like a person's name?"""
    if not value or len(value) < 3:
        return False
    # Must start with uppercase
    if not value[0].isupper():
        return False
    # Must not start with articles or descriptive prefixes (those are titles/descriptions)
    if re.match(r'^(?:Das |Der |Die |Ein |Eine |A |The |Über |Im |Aus )', value):
        return False
    # Must not be all-caps (acronyms)
    if value.isupper():
        return False
    # Should have at least first + last name, OR be a known single-name author
    words = value.split()
    if len(words) < 2:
        # Single-word names are suspicious but allowed for historical figures
        return len(value) > 3
    # Check that most words start with uppercase (name parts)
    upper_words = sum(1 for w in words if w[0].isupper() or w in ('von', 'van', 'de', 'der', 'den', 'di', 'du', 'i', 'e', 'und'))
    return upper_words >= len(words) * 0.6


def _strip_truncated_name_ending(author: str) -> str:
    """Strip truncated 1-2 char endings from person names due to VARCHAR(255) truncation.

    E.g. 'Georg B' -> 'Georg', 'Friedrich Fr' -> 'Friedrich'.
    Only strips if it looks like a person name with a truncated last-name fragment.
    """
    if author in REAL_SHORT_ENDINGS:
        return author

    # Match: "Words... X" where X is 1-2 chars at end
    m = re.match(r'^(.+?)\s+([A-ZÄÖÜ][a-zäöü]?)$', author)
    if not m:
        return author

    prefix = m.group(1).strip()
    fragment = m.group(2)

    # Don't strip Roman numerals used as ordinals (Xerxes I, Friedrich Wilhelm I)
    # Only protect I/V/X and multi-char numerals — D/C/L/M alone are almost certainly
    # truncated surname initials in this dataset.
    if fragment in ('I', 'V', 'X', 'II', 'IV', 'VI', 'IX', 'XI', 'XV', 'XX'):
        return author

    # Don't strip if prefix doesn't look like a person name
    # Allow single first names (Joe, Don, Georg) and "Firstname von" patterns
    if not _looks_like_person_name(prefix):
        if not re.match(r'^[A-ZÄÖÜ][a-zäöü]+(?:\s+(?:von|van|de|der|di|die))?$', prefix):
            return author

    # The prefix (without the fragment) is the cleaned name
    # For single first names, keep as-is (better than empty)
    if len(prefix.split()) >= 1 and len(prefix) > 3:
        return prefix

    return author


def _split_glued_name_title(author: str) -> str:
    """Split names glued to work titles: 'NameTitle' -> 'Name'.

    E.g. 'Abū l-Qāsem-e FerdousīDas Buch der Könige' -> 'Abū l-Qāsem-e Ferdousī'
    E.g. 'Marie von Ebner-EschenbachAphorismen' -> 'Marie von Ebner-Eschenbach'
    """
    # Look for lowercase/special char followed immediately by uppercase (title start)
    # But skip legitimate patterns like McBeal, MacGowan, LaVey, DeLillo etc.
    m = re.search(r'([a-zäöüīā])([A-ZÄÖÜ][a-zäöü])', author)
    if not m:
        return author

    pos = m.start() + 1  # position of the uppercase char
    before = author[:pos]
    after = author[pos:]

    # Skip Mc/Mac/La/De/Di patterns
    # Check if this is a legitimate camelCase name part
    prefix_end = before[-2:] if len(before) >= 2 else before
    if prefix_end in ('Mc', 'mc'):
        return author
    # Check 3-char patterns
    prefix_3 = before[-3:] if len(before) >= 3 else ''
    if prefix_3 in ('Mac', 'mac'):
        return author

    # Check if the part before looks like a name and the part after looks like a title
    if len(before.strip()) > 3 and re.match(r'^[A-ZÄÖÜ]', after):
        return before.strip()

    return author


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

    # Fix encoding issues (? replacing non-ASCII chars, _ in names)
    if '?' in author or '_' in author:
        if author in ENCODING_FIXES:
            author = ENCODING_FIXES[author]

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
    # "Sprichwort der/des X" with truncated ending -> generic Sprichwort
    if re.match(r'^Sprichwort (?:der|des|aus) [A-ZÄÖÜ][a-zäöü]?$', author):
        return ('Sprichwort', None)

    # Source/reference works with section numbers → move to category
    # Matches "BookName N", "BookName § N", "BookName (Note) N"
    m = re.match(r'^(.+?)\s+§?\s*(\d[\da-z.,+/-]*)$', author)
    if m:
        book = re.sub(r'\s*\([^)]+\)', '', m.group(1)).strip()
        if book in SOURCE_BOOKS:
            return ('', author)

    # Zitat des Tages/Archiv -> move to category, extract author from text
    if author.startswith('Zitat des Tages'):
        return (_try_extract_author(text), author)

    # "Zitat des/von NAME" -> extract NAME
    m = re.match(r'^Zitat (?:des|von) (.+)', author)
    if m:
        return (m.group(1).strip(), None)

    # "Aus COUNTRY" -> convert to "Sprichwort aus COUNTRY"
    if author in AUS_COUNTRY_MAP:
        return (AUS_COUNTRY_MAP[author], None)
    if re.match(r'^Aus [A-ZÄÖÜ]', author):
        base = re.sub(r'\s*\(.*$', '', author).strip()
        if base in AUS_COUNTRY_MAP:
            return (AUS_COUNTRY_MAP[base], None)
        if ' und ' in author:
            return ('Sprichwort', None)
        m = re.match(r'^Aus \w+\((.+?)\)$', author)
        if m:
            return (m.group(1).strip(), None)
        return ('Sprichwort aus ' + base.replace('Aus ', ''), None)
    if author.startswith('aus '):
        return ('', None)

    # Doubled/corrupted entries like "Aus …landAus …land" or "ProduktProduktname"
    if re.search(r'(.{4,})\1', author):
        return ('', None)

    # Fragment starting with /
    if author.startswith('/'):
        return ('', None)

    # "Work / Character" play/dialogue references
    if ' / ' in author:
        if 'Sprichwort' in author:
            return ('Sprichwort', None)
        if any(w in author for w in ('GmbH', 'Produkt', 'Urheber')):
            return ('Werbespruch', None)
        return ('', author)

    # Company names → Werbespruch
    if 'GmbH' in author or re.search(r'& (?:Co|Cie)\b', author):
        return ('Werbespruch', None)

    # Work/film/book titles -> move to category (not an author)
    if _is_work_title(author):
        return ('', author)

    # Wikiquote disambiguation/topic pages: "Word (Descriptor)"
    m = re.match(r'^(.+?)\s+\(([^)]+)\)$', author)
    if m:
        desc = m.group(2).strip()
        base = m.group(1).strip()
        # Letter range index pages: (a-d), (e-m), (n-z)
        if re.match(r'^[a-z]-[a-z]$', desc):
            return ('', author)
        # Known disambiguation types
        if desc in DISAMBIGUATION_PAGE_TYPES:
            return ('', author)
        # Person name with profession/party/years → strip parens
        if _looks_like_person_name(base) and len(base) > 5:
            return (base, None)
        # Year range like (1912-84)
        if re.match(r'^\d{4}[–-]\d{2,4}$', desc):
            return (base, None)

    # "Kapitel N" chapter references -> move to category
    if author.startswith('Kapitel'):
        return ('', author)

    # Source references: "Name in der/dem/einem/einer..."
    # Must check BEFORE truncated-name stripping since these contain full names
    name = _extract_name_from_source_ref(author)
    if name:
        return (name, None)

    # "Name TitleWord Title" → extract person name before work title
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:Das|Der|Die|Ein|Eine|Über|Zur|Von|Vom|Zum) \w', author)
    if m:
        candidate = m.group(1).strip()
        if _looks_like_person_name(candidate) and len(candidate) > 5:
            return (candidate, None)

    # "Name über TOPIC" -> extract name
    name = _extract_name_from_uber(author)
    if name:
        return (name, None)

    # "nach NAME" -> extract NAME as author
    m = re.match(r'^nach (\w.+)', author)
    if m:
        name = m.group(1).strip()
        if name[0].isupper() and not name.startswith(('der ', 'einer ', 'dem ')):
            return (name, None)
        return ('', None)

    # "von NAME" or "von NAME in/im CONTEXT" → extract NAME
    if author.startswith('von '):
        rest = author[4:].strip()
        name = _extract_name_from_source_ref(rest)
        if name:
            return (name, None)
        # "von Name im/in/bei CONTEXT" → extract just the name
        m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:im|in|bei|auf|am|vom|zu)\s+', rest)
        if m:
            candidate = m.group(1).strip()
            if _looks_like_person_name(candidate):
                return (candidate, None)
        if _looks_like_person_name(rest) and len(rest) > 3:
            return (rest, None)
        return ('', None)

    # Attribution: "X zugeschrieben" or "X fälschlich zugeschrieben"
    m = re.match(r'^(.+?)\s*\(?(?:fälschlich\s+)?zugeschrieben', author)
    if m:
        candidate = m.group(1).strip()
        if candidate and candidate[0].isupper() and len(candidate) > 3:
            return (candidate, None)
        return ('', None)
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
        m = re.match(r'^\(([A-ZÄÖÜ][\w\s.]+)\)$', author)
        if m:
            return (m.group(1).strip(), None)
        if 'Worte' in author or 'Rede' in author:
            return (author, None)
        return ('', None)

    # Reference fragments containing 'vgl'
    if 'vgl' in author.lower():
        return ('', None)

    # Literary/religious sources as authors -> move to category
    # Note: Ilias, Aias, Werke are handled in run_full_cleanup post-processing
    # because they may need swapping with category (which holds the real author)
    if author in ('Bibel', 'Koran', 'Yvain'):
        return ('', author)

    # Descriptions / wiki metadata -> move to category
    if re.match(r'^(?:Über die |Wahlspruch |Grundannahme |Saarkundgebung |Tagebucheintrag '
                 r'|Sperrung von |Ohne Kenntnis |Meinungsbilder/|Leitsatz von '
                 r'|Drei Quellen |So soll er |Reaktion auf |Sprichwort aus Gespräch)', author):
        return ('', author)

    # "Sprichwort + extra comment in parens" -> strip the comment
    m = re.match(r'^((?:\w+ )?Sprichwort(?:\w*)?)\s+\(.+\)$', author)
    if m:
        return (m.group(1).strip(), None)
    # "Sprichwörtlich/Sprichwortörtlich nach NAME" -> extract name
    if re.match(r'^Sprichwort(?:ört)?lich', author):
        m = re.match(r'^Sprichwort(?:ört)?lich(?:e Anspielung)?\s+nach\s+(.+)', author)
        if m:
            return (m.group(1).strip(), None)
        return ('', author)

    # "Name „Work Title"" or 'Name „Title"' — check before length cutoff
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+[„"»«]', author)
    if m:
        candidate = m.group(1).strip()
        if _looks_like_person_name(candidate) and len(candidate) > 5:
            return (candidate, None)

    # Long authors (>55 chars) are almost always descriptions, not names
    if len(author) > 55:
        # Try to extract a person name from the beginning
        m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]{3,40}?)\s+(?:in |bei |im |zur |auf |am |vom |zu |über |nach |\d{4})', author)
        if m:
            candidate = m.group(1).strip().rstrip(',')
            if _looks_like_person_name(candidate):
                return (candidate, None)
        # Move the whole thing to category
        return ('', author)

    # "Name (YYYY)" with year in parens -> strip the year
    m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+\(\d{4}\)$', author)
    if m:
        return (m.group(1).strip(), None)

    # "Brief von Name (YYYY) ..." -> extract name
    m = re.match(r'^Brief von\s+(.+?)(?:\s+\(|\s+an\b)', author)
    if m:
        candidate = m.group(1).strip()
        if _looks_like_person_name(candidate):
            return (candidate, None)

    # Magazine/newspaper references ending in "Nr" -> move to category
    if author.endswith(' Nr') or re.search(r' Nr\b', author):
        # Try to extract a person name from before the publication
        m = re.match(r'^([A-ZÄÖÜ][\w\s.,-]+?)\s+(?:in |im )', author)
        if m:
            candidate = m.group(1).strip()
            if _looks_like_person_name(candidate):
                return (candidate, None)
        return ('', author)

    # DER SPIEGEL, ARD-Jahrbuch, etc. (all-caps publication names)
    if re.match(r'^[A-Z]{2,}[ -]', author):
        return ('', author)

    # "Fragen zur Wikiquote/..." -> clear
    if author.startswith('Fragen zur '):
        return ('', None)

    # Split glued name+title
    fixed = _split_glued_name_title(author)
    if fixed != author:
        author = fixed

    # Strip truncated name endings (1-2 char fragments from VARCHAR(255) truncation)
    fixed = _strip_truncated_name_ending(author)
    if fixed != author:
        author = fixed

    # Final check: sentence-like authors (from CSV import garbage)
    if _is_sentence_like(author):
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
    if 0 < len(category) <= 3 and category[0].isupper():
        return ''

    return category


def run_full_cleanup() -> dict[str, int]:
    """Run all cleanup steps on the quote database. Returns a stats dict."""
    stats: Counter = Counter()

    # --- Text cleanup (all quotes, batched to limit memory) ---
    stats['total_quotes'] = db.session.query(db.func.count(Quote.id)).scalar() or 0
    all_quotes = Quote.query.yield_per(1000).all()

    for i, quote in enumerate(all_quotes):
        # Text cleanup
        new_text = _clean_text(quote.text)
        if new_text != quote.text:
            stats['text_cleaned'] += 1
            quote.text = new_text

        # Author cleanup (run twice to converge — first pass may produce
        # a value that the second pass further cleans, e.g. extracted author
        # that itself needs cleanup)
        new_author, new_cat = _clean_author(quote.author or '', quote.text)
        new_author = new_author.strip()
        new_author2, new_cat2 = _clean_author(new_author, quote.text)
        new_author2 = new_author2.strip()
        if new_author2 != new_author:
            new_author = new_author2
            if new_cat2 is not None:
                new_cat = new_cat2
        old_author = (quote.author or '').strip()
        if new_author != old_author:
            stats['author_cleaned'] += 1
            quote.author = new_author

        # If author was an origin label, move to category
        if new_cat is not None:
            if not quote.category or quote.category == old_author:
                if quote.category != new_cat:
                    stats['author_to_category'] += 1
                    quote.category = new_cat

        # Category cleanup
        new_category = _clean_category(quote.category or '')
        if new_category != (quote.category or ''):
            stats['category_cleaned'] += 1
            quote.category = new_category

        # Flush in batches to avoid memory/transaction issues
        if (i + 1) % 1000 == 0:
            db.session.flush()

    db.session.commit()
    logger.info('Text/author/category cleanup done: %s', dict(stats))

    # --- Post-processing: context-dependent fixes (need category info) ---
    all_quotes = Quote.query.yield_per(1000).all()
    for i, quote in enumerate(all_quotes):
        author = (quote.author or '').strip()
        cat = (quote.category or '').strip()
        if not author:
            continue

        # Single-word brand names with Werbespruch category -> 'Werbespruch'
        if ' ' not in author and cat == 'Werbespruch' and author != 'Werbespruch':
            quote.author = 'Werbespruch'
            stats['brand_to_werbespruch'] += 1
            continue

        # Single-word truncated first names: category starts with "Author X"
        # e.g. author="Georg", category="Georg B" -> both were truncated from VARCHAR(255)
        if ' ' not in author and cat and re.match(re.escape(author) + r' [A-ZÄÖÜ]', cat):
            quote.author = ''
            stats['truncated_firstname_cleared'] += 1
            continue

        # Literary works where category holds the real author:
        # e.g. author="Ilias" category="Homer" or author="Aias" category="Sophokles"
        if author in ('Ilias', 'Aias', 'Werke') and cat:
            if _looks_like_person_name(cat):
                quote.category = author
                quote.author = cat
                stats['author_category_swapped'] += 1
            else:
                # Category is not a person name, just move work to category
                quote.author = ''
                quote.category = author
                stats['author_to_category'] += 1
            continue

        # Single-word 3-5 char authors not known as single-name figures → clear
        # (truncated first names like Axel, Fred, Hans, Horst, etc.)
        if (' ' not in author and 3 <= len(author) <= 5
                and author[0].isupper() and author not in KNOWN_SINGLE_NAMES
                and cat != 'Werbespruch'):
            quote.author = ''
            stats['truncated_firstname_cleared'] += 1
            continue

        if (i + 1) % 1000 == 0:
            db.session.flush()

    db.session.commit()
    logger.info('Post-processing done: %s', {k: v for k, v in stats.items()
                if k in ('brand_to_werbespruch', 'truncated_firstname_cleared', 'author_category_swapped')})

    # --- Dedup: exact text duplicates ---
    # Strategy: add a persistent text_hash column (CRC32) with an index, then group by hash.
    # This avoids full-table scan on TEXT column.
    from models import quote_tags as quote_tags_table
    if db.engine.dialect.name == 'sqlite':
        text_groups = (
            db.session.query(db.func.min(Quote.id), db.func.count(Quote.id))
            .group_by(Quote.text)
            .having(db.func.count(Quote.id) > 1)
            .all()
        )
        keep_ids = {min_id for min_id, cnt in text_groups}
        if keep_ids:
            for min_id in keep_ids:
                quote = db.session.get(Quote, min_id)
                if quote:
                    dupe_ids = [d.id for d in db.session.query(Quote.id).filter(
                        Quote.text == quote.text, Quote.id != min_id).all()]
                    if dupe_ids:
                        db.session.execute(
                            quote_tags_table.delete().where(quote_tags_table.c.quote_id.in_(dupe_ids))
                        )
                        Quote.query.filter(Quote.id.in_(dupe_ids)).delete(synchronize_session=False)
                        stats['duplicates_deleted'] += len(dupe_ids)
    else:
        # MariaDB: use a temporary hash column with index for fast grouping
        # Step 1: Add text_hash column if not exists
        try:
            db.session.execute(db.text(
                'ALTER TABLE quote ADD COLUMN text_hash INT UNSIGNED NULL'
            ))
            db.session.commit()
            logger.info('Added text_hash column')
        except Exception:
            db.session.rollback()  # column already exists

        # Step 2: Populate hash column in batches
        db.session.execute(db.text(
            'UPDATE quote SET text_hash = CRC32(text) WHERE text_hash IS NULL'
        ))
        db.session.commit()
        logger.info('Populated text_hash column')

        # Step 3: Add index if not exists
        try:
            db.session.execute(db.text(
                'ALTER TABLE quote ADD INDEX idx_text_hash (text_hash)'
            ))
            db.session.commit()
            logger.info('Added text_hash index')
        except Exception:
            db.session.rollback()  # index already exists

        # Step 4: Find duplicate hash groups (fast with index)
        hash_groups = db.session.execute(db.text(
            'SELECT text_hash, COUNT(*) as cnt FROM quote '
            'GROUP BY text_hash HAVING cnt > 1'
        )).fetchall()
        logger.info('Found %d hash groups with potential duplicates', len(hash_groups))

        for text_hash, cnt in hash_groups:
            # Get all IDs with this hash, ordered by ID
            rows = db.session.execute(db.text(
                'SELECT id FROM quote WHERE text_hash = :h ORDER BY id'
            ), {'h': text_hash}).fetchall()
            if len(rows) < 2:
                continue
            # Group by exact text within this hash bucket
            ids = [r[0] for r in rows]
            seen_texts: dict[str, int] = {}  # text -> keep_id
            dupe_ids = []
            for qid in ids:
                quote = db.session.get(Quote, qid)
                if not quote:
                    continue
                if quote.text in seen_texts:
                    dupe_ids.append(qid)
                    stats['duplicates_deleted'] += 1
                else:
                    seen_texts[quote.text] = qid
            if dupe_ids:
                # Delete quote_tags entries first, then quotes
                db.session.execute(
                    quote_tags_table.delete().where(quote_tags_table.c.quote_id.in_(dupe_ids))
                )
                Quote.query.filter(Quote.id.in_(dupe_ids)).delete(synchronize_session=False)

    db.session.flush()
    logger.info('Dedup done: %d duplicates deleted', stats['duplicates_deleted'])

    # --- Non-Latin author quotes: delete entirely ---
    # Quotes with Arabic, CJK, Cyrillic etc. authors are from malformed CSV imports
    # Only scan distinct authors to find non-Latin ones, then bulk-delete by author
    # Must delete quote_tags first due to FK constraint
    distinct_authors = db.session.query(Quote.author).filter(
        Quote.author != '', Quote.author.isnot(None)
    ).distinct().all()
    non_latin_authors = [a[0] for a in distinct_authors if _has_non_latin_chars(a[0])]
    if non_latin_authors:
        for batch_start in range(0, len(non_latin_authors), 100):
            batch = non_latin_authors[batch_start:batch_start + 100]
            # Get IDs of quotes to delete
            ids_to_delete = [q.id for q in
                             db.session.query(Quote.id).filter(Quote.author.in_(batch)).all()]
            if ids_to_delete:
                # Delete quote_tags entries first, then quotes
                db.session.execute(
                    quote_tags_table.delete().where(quote_tags_table.c.quote_id.in_(ids_to_delete))
                )
                count = Quote.query.filter(Quote.id.in_(ids_to_delete)).delete(synchronize_session=False)
                stats['non_latin_deleted'] += count
        db.session.flush()
        logger.info('Deleted %d quotes with non-Latin authors', stats['non_latin_deleted'])

    # --- Garbage quotes: empty or placeholder text ---
    garbage_ids = [q.id for q in db.session.query(Quote.id).filter(
        db.or_(
            Quote.text == '',
            Quote.text.is_(None),
            db.func.length(db.func.trim(Quote.text)) == 0,
        )
    ).all()]
    if garbage_ids:
        db.session.execute(
            quote_tags_table.delete().where(quote_tags_table.c.quote_id.in_(garbage_ids))
        )
        Quote.query.filter(Quote.id.in_(garbage_ids)).delete(synchronize_session=False)
        stats['garbage_deleted'] += len(garbage_ids)

    db.session.commit()
    logger.info('Cleanup complete: %s', dict(stats))
    return dict(stats)
