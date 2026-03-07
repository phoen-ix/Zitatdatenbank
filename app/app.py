from __future__ import annotations

import logging
import os
import secrets
import time
from datetime import datetime, timedelta

import click
from urllib.parse import quote as urlquote, urlparse

from flask import Flask, Response, g, session, request, redirect, url_for, flash, jsonify, render_template
from markupsafe import Markup, escape
from werkzeug.security import generate_password_hash

from extensions import db, csrf, migrate, limiter, login_manager
from helpers import _, get_setting, get_active_theme, hex_to_rgb, is_dark_theme, get_cached_result
from config import DEFAULT_THEME


def setup_logging() -> None:
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))
    root.addHandler(handler)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)


app = Flask(__name__)

_secret = os.environ.get('SECRET_KEY', '')
if not _secret or _secret == 'change-this-to-a-random-secret-key':
    if os.environ.get('FLASK_TESTING') == '1':
        _secret = 'test-key-not-for-production'
    else:
        raise RuntimeError(
            'SECRET_KEY is not set or is the insecure default. '
            'Set a strong random value in your .env file.'
        )
app.config['SECRET_KEY'] = _secret

_db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI', '')
if not _db_uri:
    _db_user = os.environ.get('DB_USER', '')
    _db_pass = os.environ.get('DB_PASSWORD', '')
    if not _db_user or not _db_pass:
        if os.environ.get('FLASK_TESTING') == '1':
            _db_uri = 'sqlite://'
        else:
            raise RuntimeError(
                'DB_USER and DB_PASSWORD must be set in your .env file '
                '(or set SQLALCHEMY_DATABASE_URI directly).'
            )
    else:
        _db_host = os.environ.get('DB_HOST', 'localhost')
        _db_port = os.environ.get('DB_PORT', '3306')
        _db_name = os.environ.get('DB_NAME', 'zitatdatenbank')
        _db_uri = f'mysql+pymysql://{urlquote(_db_user, safe="")}:{urlquote(_db_pass, safe="")}@{_db_host}:{_db_port}/{_db_name}'
app.config['SQLALCHEMY_DATABASE_URI'] = _db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.environ.get('FLASK_TESTING') != '1':
    app.config['SESSION_COOKIE_SECURE'] = True

db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
limiter.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

import models  # noqa: F401

from routes import register_blueprints
register_blueprints(app)


@app.template_filter('nlbr')
def nl_br_filter(text):
    """Convert // line breaks in quotes to <br> tags."""
    if not text:
        return text
    return Markup(escape(text).replace(' // ', Markup('<br>')).replace('//', Markup('<br>')))


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(models.AdminUser, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    flash(_('login_required'), 'error')
    return redirect(url_for('auth.login', next=request.url))


@app.errorhandler(404)
def not_found_handler(e):
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'detail': 'Not found'}), 404
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error_handler(e):
    logger.error('Internal server error: %s', e)
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'detail': 'Internal server error'}), 500
    return render_template('errors/500.html'), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'detail': str(e.description)}), 429
    flash(_('rate_limited'), 'error')
    ref = request.referrer
    if ref and urlparse(ref).netloc not in ('', request.host):
        ref = None
    return redirect(ref or url_for('main.index'))


@app.context_processor
def inject_globals():
    theme = get_active_theme()
    nonce = secrets.token_urlsafe(16)
    g.csp_nonce = nonce
    return dict(
        _=_,
        theme=theme,
        theme_navbar_rgb=hex_to_rgb(theme.get('color_navbar', '#6b4c3b')),
        is_dark=is_dark_theme(theme),
        csp_nonce=nonce,
        site_name=get_cached_result('site_name',
            lambda: get_setting('site_name', 'Zitatdatenbank')),
        current_lang=session.get('lang', 'de'),
    )


@app.after_request
def set_security_headers(response: Response) -> Response:
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    if 'text/html' in response.content_type:
        nonce = g.get('csp_nonce', '')
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        )
    return response


# CLI commands
@app.cli.command('import-quotes')
@click.argument('path')
def import_quotes_cmd(path):
    """Import quotes from a SQL dump file."""
    from import_service import import_quotes_from_sql
    if not os.path.exists(path):
        click.echo(f'File not found: {path}')
        return
    count = import_quotes_from_sql(path)
    click.echo(f'Imported {count} quotes.')


@app.cli.command('import-csv')
@click.argument('path')
@click.option('--default-tags', default='', help='Comma-separated default tags for all imported quotes')
def import_csv_cmd(path, default_tags):
    """Import quotes from a CSV file (columns: quote, author, category)."""
    from import_service import import_quotes_from_csv
    if not os.path.exists(path):
        click.echo(f'File not found: {path}')
        return
    tag_names = [t.strip() for t in default_tags.split(',') if t.strip()] if default_tags else []
    count = import_quotes_from_csv(path, tag_names)
    click.echo(f'Imported {count} quotes.')


@app.cli.command('cleanup-quotes')
def cleanup_quotes_cmd():
    """Clean up quote data: fix wiki markup, truncated authors, duplicates."""
    from cleanup_service import run_full_cleanup
    stats = run_full_cleanup()
    for key, val in stats.items():
        click.echo(f'{key}: {val}')


@app.cli.command('create-admin')
@click.option('--username', prompt=True)
@click.option('--password', prompt=True, hide_input=True)
def create_admin_cmd(username, password):
    """Create an admin user."""
    existing = models.AdminUser.query.filter_by(username=username).first()
    if existing:
        existing.password_hash = generate_password_hash(password)
        db.session.commit()
        click.echo(f'Admin user "{username}" password updated.')
    else:
        admin = models.AdminUser(
            username=username,
            password_hash=generate_password_hash(password),
        )
        db.session.add(admin)
        db.session.commit()
        click.echo(f'Admin user "{username}" created.')


def _ensure_admin():
    """Create admin user from env vars if no admin exists."""
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', '')
    if not password:
        return
    existing = models.AdminUser.query.filter_by(username=username).first()
    if existing:
        logger.info('       Admin user "%s" already exists.', username)
    else:
        admin = models.AdminUser(
            username=username,
            password_hash=generate_password_hash(password),
        )
        db.session.add(admin)
        db.session.commit()
        logger.info('       Admin user "%s" created.', username)


def _auto_import():
    """Auto-import quotes on first startup if table is empty."""
    count = db.session.query(models.Quote).count()
    if count > 0:
        logger.info('       Database already has %d quotes, skipping import.', count)
        return
    # Import SQL dump (German quotes)
    for path in ['/data/zitate.sql', '/app/data/zitate.sql', 'data/zitate.sql']:
        if os.path.exists(path):
            logger.info('       Importing German quotes from %s ...', path)
            from import_service import import_quotes_from_sql
            imported = import_quotes_from_sql(path)
            logger.info('       Imported %d German quotes.', imported)
            break

    # Import CSV (English quotes) if present
    for path in ['/data/quotes.csv', '/app/data/quotes.csv', 'data/quotes.csv']:
        if os.path.exists(path):
            logger.info('       Importing English quotes from %s ...', path)
            from import_service import import_quotes_from_csv
            tag_names = ['English', 'Englisch', 'Source: Kaggle']
            imported = import_quotes_from_csv(path, tag_names)
            logger.info('       Imported %d English quotes.', imported)
            break


def _auto_cleanup():
    """Run quote cleanup if version is outdated. Uses a version Setting to avoid re-running."""
    from helpers import get_setting, set_setting
    from cleanup_service import CLEANUP_VERSION
    current = int(get_setting('cleanup_version', '0'))
    if current >= CLEANUP_VERSION:
        logger.info('       Cleanup already at v%d, nothing to do.', current)
        return
    count = db.session.query(models.Quote).count()
    if count == 0:
        return
    logger.info('       Cleaning up %d quotes (v%d → v%d)... this may take a few minutes.',
                count, current, CLEANUP_VERSION)
    from cleanup_service import run_full_cleanup
    stats = run_full_cleanup()
    set_setting('cleanup_version', str(CLEANUP_VERSION))
    logger.info('       Cleanup complete: %s', stats)


def _auto_migrate_tags():
    """Migrate category field to tags (one-time). Adds default tags to all quotes."""
    from helpers import get_setting, set_setting
    if get_setting('tags_migrated', '') == '1':
        logger.info('       Tags already migrated.')
        return
    count = db.session.query(models.Quote).count()
    if count == 0:
        return
    logger.info('       Migrating categories to tags for %d quotes...', count)

    # Create default tags
    default_tag_names = ['Deutsch', 'German', 'Quelle: Zitatdatenbank']
    default_tags = []
    for name in default_tag_names:
        tag = models.Tag.query.filter_by(name=name).first()
        if not tag:
            tag = models.Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        default_tags.append(tag)

    # Build tag cache from all existing tags + categories
    tag_cache: dict[str, models.Tag] = {}
    for tag in models.Tag.query.all():
        tag_cache[tag.name] = tag
    for t in default_tags:
        tag_cache[t.name] = t

    all_quotes = models.Quote.query.all()
    categories_seen: dict[str, str] = {}  # lowercase -> preferred casing
    for q in all_quotes:
        cat = (q.category or '').strip()
        if cat and cat.lower() not in categories_seen:
            categories_seen[cat.lower()] = cat

    # Create tags for unique categories not yet in DB (case-insensitive dedup)
    tag_cache_lower = {k.lower(): v for k, v in tag_cache.items()}
    for cat_lower, cat_name in categories_seen.items():
        if cat_lower not in tag_cache_lower:
            tag = models.Tag(name=cat_name)
            db.session.add(tag)
            tag_cache[cat_name] = tag
            tag_cache_lower[cat_lower] = tag
        else:
            # Map original category name to existing tag
            tag_cache[cat_name] = tag_cache_lower[cat_lower]
    db.session.flush()

    # Assign tags to quotes (default tags + category tag)
    for i, q in enumerate(all_quotes):
        q.tags = list(default_tags)
        cat = (q.category or '').strip()
        if cat and cat in tag_cache:
            cat_tag = tag_cache[cat]
            if cat_tag not in q.tags:
                q.tags.append(cat_tag)
        if (i + 1) % 1000 == 0:
            db.session.flush()
            logger.info('       Tagged %d / %d quotes...', i + 1, len(all_quotes))

    db.session.commit()
    set_setting('tags_migrated', '1')
    logger.info('       Tag migration complete: %d quotes, %d tags.', len(all_quotes), len(tag_cache))


def _ensure_fulltext_indexes():
    """Create FULLTEXT indexes on quote table if not present (MariaDB only)."""
    if db.engine.dialect.name == 'sqlite':
        return
    try:
        result = db.session.execute(db.text(
            "SELECT INDEX_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'quote' AND INDEX_NAME = 'ft_quote_text'"
        ))
        if result.fetchone():
            logger.info('       FULLTEXT indexes already exist.')
            return
        logger.info('       Creating FULLTEXT indexes (may take a moment)...')
        db.session.execute(db.text('ALTER TABLE quote ADD FULLTEXT INDEX ft_quote_text (text)'))
        db.session.execute(db.text('ALTER TABLE quote ADD FULLTEXT INDEX ft_quote_author (author)'))
        db.session.commit()
        logger.info('       FULLTEXT indexes created.')
    except Exception as e:
        logger.warning('       Could not create FULLTEXT indexes: %s', e)
        db.session.rollback()


# Startup logic
if os.environ.get('FLASK_TESTING') != '1':
    from sqlalchemy.exc import OperationalError

    _startup_start = time.monotonic()
    logger.info('='*60)
    logger.info('  Zitatdatenbank — Starting up')
    logger.info('='*60)

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            with app.app_context():
                logger.info('[1/6] Connecting to database...')
                db.session.execute(db.text('SELECT 1'))
                db.create_all()
                logger.info('[1/6] Database connected.')

                logger.info('[2/6] Checking admin user...')
                _ensure_admin()

                logger.info('[3/6] Checking for data to import...')
                _auto_import()

                logger.info('[4/6] Running data cleanup...')
                _auto_cleanup()

                logger.info('[5/6] Migrating tags...')
                _auto_migrate_tags()

                logger.info('[6/6] Ensuring search indexes...')
                _ensure_fulltext_indexes()

            _elapsed = time.monotonic() - _startup_start
            logger.info('='*60)
            logger.info('  Startup complete in %.1fs — ready to serve', _elapsed)
            logger.info('='*60)
            break
        except OperationalError:
            if attempt == max_retries:
                logger.error('Could not connect to database after %d attempts', max_retries)
                raise
            delay = 2 ** (attempt - 1)
            logger.warning('DB not ready, retrying in %ds... (%d/%d)', delay, attempt, max_retries)
            time.sleep(delay)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG') == '1')
