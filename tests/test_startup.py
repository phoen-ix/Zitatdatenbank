from __future__ import annotations

import os
import re
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
    """A fresh install imports the English CSV (tagged) before the migration runs: the
    migration must not replace those tags."""
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


def test_auto_import_loads_both_sources_into_an_empty_table(tmp_path, monkeypatch):
    """The server's first start imports data/zitate.sql (German, untagged) and data/quotes.csv
    (English, tagged); a later start finds quotes and imports nothing."""
    from app import _auto_import
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'zitate.sql').write_text(
        "INSERT INTO `zitate` (`id`, `zitat`, `autor_herkunft_thema`) VALUES (1, 'Erstes Zitat', 'Goethe');\n",
        encoding='utf-8')
    (tmp_path / 'data' / 'quotes.csv').write_text(
        'quote,author,category\n"Be yourself.",Oscar Wilde,life\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    _auto_import()
    assert Quote.query.count() == 2
    assert _tag_names(1) == []
    english = Quote.query.filter_by(author='Oscar Wilde').one()
    assert _tag_names(english.id) == ['Englisch', 'English', 'Source: Kaggle', 'life']
    _auto_import()
    assert Quote.query.count() == 2


def test_cli_import_quotes_and_create_admin(app, tmp_path):
    from werkzeug.security import check_password_hash
    from models import AdminUser
    runner = app.test_cli_runner()
    sql = tmp_path / 'zitate.sql'
    sql.write_text("INSERT INTO `zitate` (`id`, `zitat`, `autor_herkunft_thema`) VALUES (1, 'Eins', 'A'), "
                   "(2, 'Zwei', 'B');\n", encoding='utf-8')
    assert 'Imported 2 quotes.' in runner.invoke(args=['import-quotes', str(sql)]).output
    assert 'File not found' in runner.invoke(args=['import-quotes', str(tmp_path / 'missing.sql')]).output
    assert Quote.query.count() == 2

    runner.invoke(args=['create-admin', '--username', 'cli', '--password', 'old'])
    result = runner.invoke(args=['create-admin', '--username', 'cli', '--password', 'new'])
    assert 'Admin user "cli" password updated.' in result.output
    assert check_password_hash(AdminUser.query.filter_by(username='cli').one().password_hash, 'new')


ENTRYPOINT = Path(__file__).resolve().parent.parent / 'entrypoint.sh'


def _run_entrypoint(data_dir):
    """entrypoint.sh with /data pointed at data_dir and without gosu (the image's user switch)."""
    script = re.sub(r'(?<!\w)/data\b', str(data_dir), ENTRYPOINT.read_text()).replace('exec gosu appuser', 'exec')
    return subprocess.run(['sh', '-c', script, 'entrypoint.sh', 'true'], capture_output=True, text=True,
                          timeout=60)


def test_entrypoint_extracts_the_data_archive(tmp_path):
    import tarfile
    src = tmp_path / 'src'
    src.mkdir()
    (src / 'zitate.sql').write_text('-- dump\n')
    (src / 'quotes.csv').write_text('quote,author,category\n')
    with tarfile.open(tmp_path / 'data.tar.gz', 'w:gz') as tar:
        for name in ('zitate.sql', 'quotes.csv'):
            tar.add(src / name, arcname=name)
    r = _run_entrypoint(tmp_path)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / 'zitate.sql').read_text() == '-- dump\n'
    assert (tmp_path / 'quotes.csv').exists()


def test_entrypoint_stops_on_an_lfs_pointer(tmp_path):
    (tmp_path / 'data.tar.gz').write_text('version https://git-lfs.github.com/spec/v1\noid sha256:0\nsize 1\n')
    r = _run_entrypoint(tmp_path)
    assert r.returncode == 1
    assert 'git lfs pull' in r.stderr
    assert not (tmp_path / 'zitate.sql').exists()
