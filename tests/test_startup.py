from __future__ import annotations

from app import _auto_migrate_tags
from helpers import get_setting
from models import Quote


def _tag_names(quote_id):
    from extensions import db
    return sorted(t.name for t in db.session.get(Quote, quote_id).tags)


def test_tag_migration_tags_untagged_quotes(make_quote):
    q = make_quote(category='Liebe')
    _auto_migrate_tags()
    assert _tag_names(q.id) == ['Deutsch', 'German', 'Liebe', 'Quelle: Zitatdatenbank']
    assert get_setting('tags_migrated') == '1'


def test_tag_migration_keeps_existing_tags(make_quote):
    """A fresh install imports the English CSV (tagged) before the migration runs, and a
    restore clears tags_migrated: the migration must not replace those tags."""
    german = make_quote(category='Natur')
    english = make_quote(tags=['English', 'Englisch', 'Source: Kaggle', 'life'])
    _auto_migrate_tags()
    assert _tag_names(english.id) == ['Englisch', 'English', 'Source: Kaggle', 'life']
    assert _tag_names(german.id) == ['Deutsch', 'German', 'Natur', 'Quelle: Zitatdatenbank']


def test_tag_migration_with_only_tagged_quotes_sets_flag(make_quote):
    from models import Tag
    english = make_quote(tags=['English'])
    _auto_migrate_tags()
    assert _tag_names(english.id) == ['English']
    assert get_setting('tags_migrated') == '1'
    assert Tag.query.filter_by(name='Deutsch').first() is None
