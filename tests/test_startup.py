from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

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


APP_DIR = Path(__file__).resolve().parent.parent / 'app'


def _run_cli(tmp_path, *cmd, **env_extra):
    env = {k: v for k, v in os.environ.items()
           if k not in ('FLASK_TESTING', 'ADMIN_PASSWORD', 'FLASK_RUN_FROM_CLI')}
    env.update(FLASK_APP=str(APP_DIR / 'app.py'), SECRET_KEY='cli-test-key',
               SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path}/cli.db', **env_extra)
    return subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)


def test_flask_script_runs_cli_commands(tmp_path):
    """`flask <cmd>` (not only `python -m flask`): an app/__init__.py made the script import
    app.py as app.app without app/ on sys.path."""
    flask = str(Path(sys.executable).with_name('flask'))
    r = _run_cli(tmp_path, flask, 'create-admin', '--username', 'cli', '--password', 'pw')
    assert r.returncode == 0, r.stderr
    assert 'Admin user "cli" created.' in r.stdout


def test_cli_commands_skip_startup_sequence(tmp_path):
    """A CLI command only creates the tables: the startup's auto-import (here data/quotes.csv
    relative to the working directory) belongs to the server."""
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'quotes.csv').write_text('quote,author,category\n"Be yourself.",Oscar Wilde,life\n')
    r = _run_cli(tmp_path, sys.executable, '-m', 'flask', 'create-admin', '--username', 'cli',
                 '--password', 'pw', PYTHONPATH=str(APP_DIR))
    assert r.returncode == 0, r.stderr
    with sqlite3.connect(tmp_path / 'cli.db') as con:
        assert con.execute('SELECT COUNT(*) FROM quote').fetchone()[0] == 0
        assert con.execute('SELECT COUNT(*) FROM admin_user').fetchone()[0] == 1
