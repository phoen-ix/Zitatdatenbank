def test_get_set_setting(app):
    with app.app_context():
        from helpers import get_setting, set_setting
        assert get_setting('nonexistent') is None
        assert get_setting('nonexistent', 'default') == 'default'

        set_setting('test_key', 'test_val')
        assert get_setting('test_key') == 'test_val'

        set_setting('test_key', 'new_val')
        assert get_setting('test_key') == 'new_val'


def test_hex_to_rgb(app):
    with app.app_context():
        from helpers import hex_to_rgb
        assert hex_to_rgb('#ff0000') == '255, 0, 0'
        assert hex_to_rgb('#00ff00') == '0, 255, 0'
        assert hex_to_rgb('#0000ff') == '0, 0, 255'
        assert hex_to_rgb('invalid') == '0, 0, 0'
        assert hex_to_rgb('') == '0, 0, 0'


def test_is_dark_theme(app):
    with app.app_context():
        from helpers import is_dark_theme
        assert is_dark_theme({'color_bg': '#000000'}) is True
        assert is_dark_theme({'color_bg': '#ffffff'}) is False
        assert is_dark_theme({'color_bg': '#181825'}) is True


def test_translation(app, client):
    with app.test_request_context():
        from helpers import _
        # Default language is de
        result = _('nav_home')
        assert result == 'Startseite'


def test_get_active_theme(app):
    with app.app_context():
        from helpers import get_active_theme, set_setting
        theme = get_active_theme()
        assert 'color_navbar' in theme
        assert 'label' in theme


def test_parse_sql_inserts():
    from import_service import parse_sql_inserts
    sql = """INSERT INTO `zitate` (`id`, `zitat`, `autor_herkunft_thema`) VALUES
(1, 'Hello world', 'Test Author'),
(2, 'It''s a test', 'Category');"""
    rows = parse_sql_inserts(sql)
    assert len(rows) == 2
    assert rows[0] == (1, 'Hello world', 'Test Author')
    assert rows[1] == (2, "It's a test", 'Category')


def test_parse_sql_escaped_quotes():
    from import_service import parse_sql_inserts
    sql = """INSERT INTO `zitate` VALUES
(1, 'He said ''''hello'''' to me', 'Author');"""
    rows = parse_sql_inserts(sql)
    assert len(rows) == 1
    assert rows[0][1] == "He said ''hello'' to me"


def test_classify_source_keywords():
    from import_service import classify_and_extract
    author, cat = classify_and_extract('Some proverb text', 'Deutsche Sprichw')
    assert author == 'Deutsche Sprichw'
    assert cat == 'Deutsche Sprichw'

    author, cat = classify_and_extract('A tongue twister', 'Zungenbrecher')
    assert author == 'Zungenbrecher'


def test_classify_single_word_topic():
    from import_service import classify_and_extract
    author, cat = classify_and_extract(
        '"Life is short" - Seneca, Letters',
        'Leben'
    )
    assert cat == 'Leben'
    assert 'Seneca' in author


def test_classify_multi_word_author():
    from import_service import classify_and_extract
    author, cat = classify_and_extract(
        '"Some quote text"',
        'Johann Wolfgang von Goethe'
    )
    assert author == 'Johann Wolfgang von Goethe'


def test_import_service_import(app):
    """Test actual import from a small SQL snippet."""
    import tempfile
    import os
    with app.app_context():
        from import_service import import_quotes_from_sql
        from models import Quote
        from extensions import db

        sql = """INSERT INTO `zitate` (`id`, `zitat`, `autor_herkunft_thema`) VALUES
(1, 'Test quote one', 'Author One'),
(2, 'Test quote two', 'Author Two');"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8') as f:
            f.write(sql)
            path = f.name

        try:
            count = import_quotes_from_sql(path)
            assert count == 2
            assert Quote.query.count() == 2
            q1 = db.session.get(Quote, 1)
            assert q1.text == 'Test quote one'
        finally:
            os.unlink(path)
