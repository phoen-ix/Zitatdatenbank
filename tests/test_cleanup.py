import pytest
from extensions import db
from models import Quote


class TestCleanText:
    def test_strips_wiki_bold(self, app):
        from cleanup_service import _clean_text
        assert _clean_text("''bold''") == 'bold'

    def test_strips_quadruple_quotes(self, app):
        from cleanup_service import _clean_text
        assert _clean_text("''''") == ''

    def test_replaces_nbsp(self, app):
        from cleanup_service import _clean_text
        assert _clean_text('hello&nbsp;world') == 'hello world'

    def test_collapses_spaces(self, app):
        from cleanup_service import _clean_text
        assert _clean_text('hello   world') == 'hello world'

    def test_combined(self, app):
        from cleanup_service import _clean_text
        assert _clean_text("''bold''  &nbsp; text") == 'bold text'


class TestCompleteSprichw:
    def test_deutsche(self, app):
        from cleanup_service import _complete_sprichw
        assert _complete_sprichw('Deutsche Sprichw') == 'Deutsches Sprichwort'

    def test_russische(self, app):
        from cleanup_service import _complete_sprichw
        assert _complete_sprichw('Russische Sprichw') == 'Russisches Sprichwort'

    def test_bare_sprichw(self, app):
        from cleanup_service import _complete_sprichw
        assert _complete_sprichw('Sprichw') == 'Sprichwort'

    def test_werbespr(self, app):
        from cleanup_service import _complete_sprichw
        assert _complete_sprichw('Werbespr') == 'Werbespruch'

    def test_already_complete(self, app):
        from cleanup_service import _complete_sprichw
        assert _complete_sprichw('Werbespruch') == 'Werbespruch'


class TestStripWikiMarkup:
    def test_strips_wiki_links(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup('[[Some Link]]') == 'Some Link'

    def test_strips_piped_links(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup('[[Page|Display Text]]') == 'Display Text'

    def test_strips_remnant_brackets(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup('Eva Herman in der Sendung [[') == 'Eva Herman in der Sendung'

    def test_strips_bold_italic(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup("Aus China''") == 'Aus China'

    def test_strips_backticks(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup('`Paramahansa-Upanishad´') == 'Paramahansa-Upanishad'

    def test_strips_w_prefix(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup(':w:Some Article') == 'Some Article'

    def test_strips_german_quotes(self, app):
        from cleanup_service import _strip_wiki_markup
        assert _strip_wiki_markup('„Dann gibt es nur eins!"') == 'Dann gibt es nur eins!'


class TestIsGarbageAuthor:
    def test_single_char(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('A') is True

    def test_numeric(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('15') is True
        assert _is_garbage_author('1797') is True

    def test_punctuation(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author(',') is True
        assert _is_garbage_author(';') is True
        assert _is_garbage_author("'") is True

    def test_known_fragments(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('Im') is True
        assert _is_garbage_author('Pap') is True
        assert _is_garbage_author('Das M') is True
        assert _is_garbage_author('Das Sch') is True
        assert _is_garbage_author('Mein F') is True

    def test_normal_name_not_garbage(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('Homer') is False
        assert _is_garbage_author('Albert Einstein') is False

    def test_lowercase_start_is_garbage(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('eigentlich spricht jemand') is True
        assert _is_garbage_author('altes Sprichwort') is True

    def test_lowercase_exceptions(self, app):
        from cleanup_service import _is_garbage_author
        # 'nach' and 'von' prefixes are handled separately in _clean_author
        assert _is_garbage_author('nach Plato') is False
        assert _is_garbage_author('von Goethe') is False

    def test_descriptive_phrases(self, app):
        from cleanup_service import _is_garbage_author
        assert _is_garbage_author('Dieser DDR-Volksmund') is True
        assert _is_garbage_author('Rede im Mai 1991') is True
        assert _is_garbage_author('Volksmund in der DDR') is True


class TestIsWorkTitle:
    def test_digit_start(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('00 Schneider') is True
        assert _is_work_title('12 Monkeys') is True
        assert _is_work_title('2001: Odyssee im Weltraum') is True

    def test_kapitel(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('Kapitel 33') is True

    def test_german_articles(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('Das Gute') is True
        assert _is_work_title('Der Herr der Ringe') is True
        assert _is_work_title('Die Verurteilten') is True

    def test_english_articles(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('A Beautiful Mind') is True
        assert _is_work_title('The Dark Knight') is True

    def test_latin_titles(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('De arte poetica') is True
        assert _is_work_title('Ad familiares') is True

    def test_known_work_patterns(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('Briefe I') is True
        assert _is_work_title('Annalen I') is True
        assert _is_work_title('Interview im Stern') is True

    def test_person_name_not_title(self, app):
        from cleanup_service import _is_work_title
        assert _is_work_title('Albert Einstein') is False
        assert _is_work_title('Goethe') is False
        assert _is_work_title('Marie Curie') is False


class TestExtractNameFromSourceRef:
    def test_name_in_der(self, app):
        from cleanup_service import _extract_name_from_source_ref
        assert _extract_name_from_source_ref(
            'Albert Einstein in einer Ansprache in der Sorbonne'
        ) == 'Albert Einstein'

    def test_name_year_in(self, app):
        from cleanup_service import _extract_name_from_source_ref
        assert _extract_name_from_source_ref(
            'Adolf Loos 1910 in dem Essay'
        ) == 'Adolf Loos'

    def test_name_bei(self, app):
        from cleanup_service import _extract_name_from_source_ref
        assert _extract_name_from_source_ref(
            'Horst Köhler bei einer gemeinsamen Sondersitzung'
        ) == 'Horst Köhler'

    def test_no_match(self, app):
        from cleanup_service import _extract_name_from_source_ref
        assert _extract_name_from_source_ref('Albert Einstein') == ''

    def test_title_not_person(self, app):
        from cleanup_service import _extract_name_from_source_ref
        # "Die Wahrheit lügt in der Mitte" - starts with article, not a person
        assert _extract_name_from_source_ref(
            'Die Wahrheit lügt in der Mitte'
        ) == ''


class TestExtractNameFromUber:
    def test_name_uber_topic(self, app):
        from cleanup_service import _extract_name_from_uber
        assert _extract_name_from_uber(
            'Albert Einstein über Johann Sebastian Bach'
        ) == 'Albert Einstein'

    def test_name_uber_thing(self, app):
        from cleanup_service import _extract_name_from_uber
        assert _extract_name_from_uber(
            'Harald Schmidt über Hypochonder'
        ) == 'Harald Schmidt'

    def test_no_uber(self, app):
        from cleanup_service import _extract_name_from_uber
        assert _extract_name_from_uber('Albert Einstein') == ''


class TestStripTruncatedNameEnding:
    def test_single_letter_stripped(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Georg B') == 'Georg'

    def test_two_letter_stripped(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Anselm Gr') == 'Anselm'

    def test_real_name_kept(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Lü Bu We') == 'Lü Bu We'
        assert _strip_truncated_name_ending('Malcolm X') == 'Malcolm X'

    def test_roman_numeral_kept(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Xerxes I') == 'Xerxes I'

    def test_normal_name_unchanged(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Albert Einstein') == 'Albert Einstein'

    def test_multi_word_prefix(self, app):
        from cleanup_service import _strip_truncated_name_ending
        assert _strip_truncated_name_ending('Friedrich H') == 'Friedrich'
        assert _strip_truncated_name_ending('Erich von D') == 'Erich von'


class TestSplitGluedNameTitle:
    def test_name_glued_to_title(self, app):
        from cleanup_service import _split_glued_name_title
        result = _split_glued_name_title('Marie von Ebner-EschenbachAphorismen')
        assert result == 'Marie von Ebner-Eschenbach'

    def test_mc_name_kept(self, app):
        from cleanup_service import _split_glued_name_title
        assert _split_glued_name_title('Ally McBeal') == 'Ally McBeal'
        assert _split_glued_name_title('Carson McCullers') == 'Carson McCullers'

    def test_normal_name_unchanged(self, app):
        from cleanup_service import _split_glued_name_title
        assert _split_glued_name_title('Albert Einstein') == 'Albert Einstein'


class TestCleanAuthor:
    def test_empty_author_extracts_from_text(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('', '"Life is short" - Goethe')
        assert author == 'Goethe'
        assert cat is None

    def test_wiki_artifact_empty(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author("''''", 'some text')
        assert author == ''

    def test_wiki_prefix_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author("''Einstein", 'some text')
        assert author == 'Einstein'

    def test_sprichw_completed(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Deutsche Sprichw', 'text')
        assert author == 'Deutsches Sprichwort'

    def test_zitat_des_tages_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Zitat des Tages/Archiv 2006', '"Wisdom" - Plato')
        assert author == 'Plato'
        assert cat == 'Zitat des Tages/Archiv 2006'

    def test_fragment_comma(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(', some fragment', 'text')
        assert author == ''

    def test_fragment_semicolon(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('; ref', 'text')
        assert author == ''

    def test_vgl_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('vgl. Goethe', 'text')
        assert author == ''

    def test_normal_author_unchanged(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Albert Einstein', 'text')
        assert author == 'Albert Einstein'

    def test_numeric_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('15', 'text')
        assert author == ''

    def test_single_char_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('A', 'text')
        assert author == ''

    def test_aus_country_converted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Aus Deutschland', 'text')
        assert author == 'Sprichwort aus Deutschland'

    def test_aus_country_truncated(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Aus Albanien (30', 'text')
        assert author == 'Sprichwort aus Albanien'

    def test_aus_typo(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Aus Deutschand', 'text')
        assert author == 'Sprichwort aus Deutschland'

    def test_name_truncated_paren(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Albert Einstein (25', 'text')
        assert author == 'Albert Einstein'

    def test_name_truncated_date(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Astrid Lindgren (18', 'text')
        assert author == 'Astrid Lindgren'

    def test_nach_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('nach Plato', 'text')
        assert author == 'Plato'

    def test_nach_phrase_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('nach der Schlacht im Teutoburger Wald', 'text')
        assert author == ''

    def test_zugeschrieben_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Karl Lueger zugeschrieben', 'text')
        assert author == 'Karl Lueger'

    def test_basierend_auf_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author("basierend auf ''''", 'text')
        assert author == ''

    def test_paren_start_name_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('(Johann König)', 'text')
        assert author == 'Johann König'

    def test_paren_start_garbage_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('(2', 'text')
        assert author == ''

    def test_zitat_von_extracts(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Zitat von Marcus Pinarius Rusca', 'text')
        assert author == 'Marcus Pinarius Rusca'

    def test_wiki_link_in_author(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('[[:w:Der verschwenderische Jüngling und die Schwalbe]]', 'text')
        assert '[[' not in author
        assert ']]' not in author

    def test_garbage_fragment_im(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Im', 'text')
        assert author == ''

    def test_punctuation_author(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(',', 'text')
        assert author == ''

    def test_double_corruption_fixed(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Englisches Sprichwortort', 'text')
        assert author == 'Englisches Sprichwort'

    def test_garbage_not_re_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('1', '"Verse" - 1. Petrus 5,7')
        assert author == ''

    def test_numeric_comma_fragment(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(', 11', 'text')
        assert author == ''

    # --- New v5 tests ---

    def test_work_title_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Der Herr der Ringe', 'text')
        assert author == ''
        assert cat == 'Der Herr der Ringe'

    def test_film_title_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('12 Monkeys', 'text')
        assert author == ''
        assert cat == '12 Monkeys'

    def test_concept_category_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Das Gute', 'text')
        assert author == ''
        assert cat == 'Das Gute'

    def test_kapitel_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Kapitel 33', 'text')
        assert author == ''
        assert cat == 'Kapitel 33'

    def test_latin_title_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('De arte poetica', 'text')
        assert author == ''
        assert cat == 'De arte poetica'

    def test_source_ref_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Albert Einstein in einer Ansprache in der Sorbonne', 'text')
        assert author == 'Albert Einstein'

    def test_year_inline_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Adolf Loos 1910 in dem Essay', 'text')
        assert author == 'Adolf Loos'

    def test_uber_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Albert Einstein über Johann Sebastian Bach', 'text')
        assert author == 'Albert Einstein'

    def test_truncated_name_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Georg B', 'text')
        assert author == 'Georg'

    def test_truncated_two_char_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Friedrich Fr', 'text')
        assert author == 'Friedrich'

    def test_glued_name_split(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Marie von Ebner-EschenbachAphorismen', 'text')
        assert author == 'Marie von Ebner-Eschenbach'

    def test_very_long_author_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Albert Einstein in einer Ansprache in der französischen '
            'Philosophischen Gesellschaft in der Sorbonne am 6 April 1922',
            'text')
        assert author == 'Albert Einstein'

    def test_english_title_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('The Dark Knight', 'text')
        assert author == ''
        assert cat == 'The Dark Knight'

    def test_a_beautiful_mind_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('A Beautiful Mind', 'text')
        assert author == ''
        assert cat == 'A Beautiful Mind'

    def test_lowercase_start_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('eigentlich spricht Mlodinow hier', 'text')
        assert author == ''

    def test_doubled_entry_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('ProduktProduktname', 'text')
        assert author == ''

    def test_name_with_year_parens(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Albert Einstein (1905)', 'text')
        assert author == 'Albert Einstein'

    def test_name_with_work_quote(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Bertrand Russell „Hat die Religion nützliche Beiträge geleistet?"',
            'text')
        assert author == 'Bertrand Russell'

    def test_interview_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Interview im Stern 44/1992', 'text')
        assert author == ''
        assert cat is not None

    def test_magazine_nr_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Der Spiegel Nr', 'text')
        assert author == ''

    def test_all_caps_publication(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('DER SPIEGEL 32/1966 vom 1', 'text')
        assert author == ''

    def test_real_chinese_name_kept(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Lü Bu We', 'text')
        assert author == 'Lü Bu We'

    def test_mc_name_kept(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Ally McBeal', 'text')
        assert author == 'Ally McBeal'

    def test_brief_von_extracts_name(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Brief von Albert Einstein (1954) an seinen Freund Besso', 'text')
        assert author == 'Albert Einstein'

    def test_bibel_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Bibel', 'text')
        assert author == ''
        assert cat == 'Bibel'

    def test_koran_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Koran', 'text')
        assert author == ''
        assert cat == 'Koran'

    def test_name_nach_event_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Sting nach einem Konzert der Toten Hosen im Olympiastadion in München', 'text')
        assert author == 'Sting'

    def test_name_dash_context_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Joseph Goebbels - stammt ursprünglich aus dem Stück', 'text')
        assert author == 'Joseph Goebbels'

    def test_name_zitiert_in_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Richard Feynman zitiert in Tony Hey und Patrick Walters', 'text')
        assert author == 'Richard Feynman'

    def test_name_anlässlich_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Luciano Pavarotti nach seiner Krebs-Operation', 'text')
        assert author == 'Luciano Pavarotti'

    def test_name_bei_entgegennahme_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Alexander Solschenizyn bei Entgegennahme des Nobelpreises für Literatur', 'text')
        assert author == 'Alexander Solschenizyn'

    def test_sprichwort_with_comment_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Griechisches Sprichwort  (In der griechischen Mythologie ist der Gott Hypnos)', 'text')
        # Truncated paren handler strips the comment, then Sprichwort handler completes it
        assert 'Sprichwort' in author

    def test_description_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Über die Handlungsweise der nationalsozialistischen Regierung', 'text')
        assert author == ''
        assert cat is not None

    def test_name_aus_work_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Stanisław Jerzy Lec aus Sämtliche unfrisierte Gedanken', 'text')
        assert author == 'Stanisław Jerzy Lec'

    def test_oder_work_title_moved(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author(
            'Geh nicht nach El Kuwehd oder Der zweifache Tod des Kaufmanns Mohallab', 'text')
        assert author == ''
        assert cat is not None

    # --- New v15 tests ---

    def test_encoding_fix_question_mark(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Matsuo Bash?', 'text')
        assert author == 'Matsuo Bashō'

    def test_encoding_fix_underscore(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Johannes_XXIII', 'text')
        assert author == 'Johannes XXIII.'

    def test_bible_verse_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Matthäus 6', 'text')
        assert author == ''
        assert cat == 'Matthäus 6'

    def test_bible_multiword_book(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Jesus Sirach 10', 'text')
        assert author == ''
        assert cat == 'Jesus Sirach 10'

    def test_psalm_moved_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Psalm 90', 'text')
        assert author == ''
        assert cat == 'Psalm 90'

    def test_classical_work_section(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Blütenstaub § 16', 'text')
        assert author == ''
        assert cat == 'Blütenstaub § 16'

    def test_agricola_section(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Agricola 30', 'text')
        assert author == ''
        assert cat == 'Agricola 30'

    def test_disambiguation_film(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Gandhi (Film)', 'text')
        assert author == ''
        assert cat == 'Gandhi (Film)'

    def test_disambiguation_letter_range(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Freiheit (a-d)', 'text')
        assert author == ''
        assert cat == 'Freiheit (a-d)'

    def test_disambiguation_pflanze(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Baum (Pflanze)', 'text')
        assert author == ''
        assert cat == 'Baum (Pflanze)'

    def test_person_with_profession_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Fritz Riemann (Psychoanalytiker)', 'text')
        assert author == 'Fritz Riemann'

    def test_person_with_year_range_stripped(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Rudolf Hagelstange (1912–84)', 'text')
        assert author == 'Rudolf Hagelstange'

    def test_play_character_to_category(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Woyzeck / Doktor', 'text')
        assert author == ''
        assert cat == 'Woyzeck / Doktor'

    def test_slash_brand_to_werbespruch(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Unilever Deutschland GmbH / Produkt', 'text')
        assert author == 'Werbespruch'

    def test_company_gmbh_to_werbespruch(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Sylphen GmbH &', 'text')
        assert author == 'Werbespruch'

    def test_company_co_to_werbespruch(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Henkell & Co', 'text')
        assert author == 'Werbespruch'

    def test_fragment_slash_cleared(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('/ Hauptmann', 'text')
        assert author == ''

    def test_known_film_title(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Fear and Loathing in Las Vegas', 'text')
        assert author == ''
        assert cat == 'Fear and Loathing in Las Vegas'

    def test_terminator_title(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Terminator 2', 'text')
        assert author == ''
        assert cat == 'Terminator 2'

    def test_exclamation_title(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Sledge Hammer!', 'text')
        assert author == ''
        assert cat == 'Sledge Hammer!'

    def test_im_prefix_title(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Im Auftrag des Teufels', 'text')
        assert author == ''
        assert cat == 'Im Auftrag des Teufels'

    def test_name_work_title_article(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Jakob Lorber Das große Evangelium Johannes', 'text')
        assert author == 'Jakob Lorber'

    def test_name_von_title(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Martin Luther Von den jüden und iren lügen', 'text')
        assert author == 'Martin Luther'

    def test_name_am_digit_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Christian Wulff am 3', 'text')
        assert author == 'Christian Wulff'

    def test_von_name_context_extracted(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('von Arundhati Roy im SPIEGEL 44/01', 'text')
        assert author == 'Arundhati Roy'

    def test_goethe_unchanged(self, app):
        from cleanup_service import _clean_author
        author, cat = _clean_author('Johann Wolfgang von Goethe', 'text')
        assert author == 'Johann Wolfgang von Goethe'

    def test_person_name_not_bible(self, app):
        """Lukas is a first name, but 'Lukas 6' is a Bible reference."""
        from cleanup_service import _clean_author
        # Just "Lukas" without a number should pass through
        author, cat = _clean_author('Lukas Cranach', 'text')
        assert author == 'Lukas Cranach'


class TestCleanCategory:
    def test_sprichw_completed(self, app):
        from cleanup_service import _clean_category
        assert _clean_category('Deutsche Sprichw') == 'Deutsches Sprichwort'

    def test_short_truncated_cleared(self, app):
        from cleanup_service import _clean_category
        assert _clean_category('Sch') == ''

    def test_short_lowercase_kept(self, app):
        from cleanup_service import _clean_category
        assert _clean_category('abc') == 'abc'

    def test_normal_category_unchanged(self, app):
        from cleanup_service import _clean_category
        assert _clean_category('Philosophie') == 'Philosophie'

    def test_empty_stays_empty(self, app):
        from cleanup_service import _clean_category
        assert _clean_category('') == ''

    def test_wiki_markup_stripped(self, app):
        from cleanup_service import _clean_category
        assert _clean_category("Griechenland'") == 'Griechenland'


class TestRunFullCleanup:
    def test_cleans_text_markup(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text="''bold text''", author='Author', category='Cat')
        db.session.add(q)
        db.session.commit()

        stats = run_full_cleanup()
        db.session.refresh(q)
        assert q.text == 'bold text'
        assert stats['text_cleaned'] >= 1

    def test_fixes_author_wiki_artifact(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='some text', author="''''", category='Cat')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == ''

    def test_completes_sprichw_author(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Ein Apfel am Tag', author='Deutsche Sprichw', category='Deutsche Sprichw')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Deutsches Sprichwort'
        assert q.category == 'Deutsches Sprichwort'

    def test_removes_duplicates(self, app):
        from cleanup_service import run_full_cleanup
        q1 = Quote(text='Duplicate text', author='Author1', category='C')
        q2 = Quote(text='Duplicate text', author='Author2', category='D')
        db.session.add_all([q1, q2])
        db.session.commit()
        min_id = min(q1.id, q2.id)

        stats = run_full_cleanup()
        assert stats['duplicates_deleted'] >= 1
        remaining = Quote.query.filter_by(text='Duplicate text').all()
        assert len(remaining) == 1
        assert remaining[0].id == min_id

    def test_removes_garbage(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='', author='Author', category='C')
        db.session.add(q)
        db.session.commit()
        qid = q.id

        stats = run_full_cleanup()
        assert stats['garbage_deleted'] >= 1
        assert db.session.get(Quote, qid) is None

    def test_clears_truncated_category(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='quote', author='Author', category='Gl')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.category == ''

    def test_converts_aus_country(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Wer den Pfennig nicht ehrt', author='Aus Deutschland', category='Geld')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Sprichwort aus Deutschland'

    def test_strips_truncated_paren_from_author(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Imagination is more important', author='Albert Einstein (25', category='')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Albert Einstein'

    def test_clears_numeric_author(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Bible verse text', author='1', category='Sorge')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == ''

    def test_moves_work_title_to_category(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='You shall not pass!', author='Der Herr der Ringe', category='')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == ''
        assert q.category == 'Der Herr der Ringe'

    def test_extracts_name_from_source_ref(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Some quote', author='Eva Herman in der Sendung', category='')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Eva Herman'

    def test_brand_name_to_werbespruch(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Just do it', author='BMW', category='Werbespruch')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Werbespruch'

    def test_truncated_firstname_cleared(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Some quote', author='Georg', category='Georg B')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == ''

    def test_ilias_author_swapped_with_category(self, app):
        from cleanup_service import run_full_cleanup
        q = Quote(text='Sing, o Göttin', author='Ilias', category='Homer')
        db.session.add(q)
        db.session.commit()

        run_full_cleanup()
        db.session.refresh(q)
        assert q.author == 'Homer'
        assert q.category == 'Ilias'

    def test_cli_command(self, app):
        from app import app as flask_app
        runner = flask_app.test_cli_runner()
        q = Quote(text='test', author='Author', category='Cat')
        db.session.add(q)
        db.session.commit()

        result = runner.invoke(args=['cleanup-quotes'])
        assert result.exit_code == 0
        assert 'total_quotes' in result.output
