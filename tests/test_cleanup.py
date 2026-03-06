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
        q1 = Quote(text='Duplicate text', author='A', category='C')
        q2 = Quote(text='Duplicate text', author='B', category='D')
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
        q = Quote(text='', author='A', category='C')
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

    def test_cli_command(self, app):
        from app import app as flask_app
        runner = flask_app.test_cli_runner()
        q = Quote(text='test', author='Author', category='Cat')
        db.session.add(q)
        db.session.commit()

        result = runner.invoke(args=['cleanup-quotes'])
        assert result.exit_code == 0
        assert 'total_quotes' in result.output
