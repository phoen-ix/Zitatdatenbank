from __future__ import annotations

import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from extensions import db
from models import Quote, Tag, BackupLog, Setting, quote_tags
from helpers import _, get_setting, set_setting, get_theme_overrides, get_cached_stat, invalidate_stats_cache, get_cached_result, FastPagination
from config import ADMIN_QUOTES_PER_PAGE, THEMES, DEFAULT_THEME, BACKUP_DIR, COLOR_KEYS, EFFECT_KEYS, ALL_THEME_KEYS
from backup_service import run_backup, restore_backup, list_backups, delete_backup_file

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def require_login():
    pass


def _sync_tags(quote, tag_string):
    """Parse comma-separated tag string and sync tags to quote."""
    tag_names = [t.strip() for t in tag_string.split(',') if t.strip()]
    # Get or create tags
    new_tags = []
    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()
        new_tags.append(tag)
    quote.tags = new_tags


@admin_bp.route('/')
def dashboard():
    total_quotes = get_cached_stat('total_quotes',
        lambda: db.session.query(func.count(Quote.id)).scalar() or 0)
    total_authors = get_cached_stat('total_authors',
        lambda: db.session.query(func.count(func.distinct(Quote.author))).filter(
            Quote.author != '', Quote.author.isnot(None)
        ).scalar() or 0)
    total_tags = get_cached_stat('total_tags',
        lambda: db.session.query(func.count(Tag.id)).scalar() or 0)

    recent_quotes = Quote.query.options(selectinload(Quote.tags)).order_by(Quote.id.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_quotes=total_quotes,
                           total_authors=total_authors,
                           total_tags=total_tags,
                           recent_quotes=recent_quotes)


@admin_bp.route('/quotes')
def quotes():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    cursor = request.args.get('cursor', type=int)
    cursor_dir = request.args.get('_cursor_dir', 'next')

    query = Quote.query.options(selectinload(Quote.tags))
    if q:
        like_pattern = f'%{q}%'

        # Use cached tag map for fast tag matching
        def _load_tag_map():
            rows = db.session.query(Tag.id, Tag.name).all()
            return [(tid, name.lower()) for tid, name in rows]

        tag_map = get_cached_result('tag_id_name_map', _load_tag_map)
        q_lower = q.lower()
        matching_tag_ids = [tid for tid, name in tag_map if q_lower in name]

        conditions = []
        if db.engine.dialect.name == 'sqlite':
            conditions = [Quote.text.ilike(like_pattern), Quote.author.ilike(like_pattern)]
        else:
            conditions = [Quote.text.match(q), Quote.author.match(q)]

        if matching_tag_ids:
            tag_subquery = db.session.query(quote_tags.c.quote_id).filter(
                quote_tags.c.tag_id.in_(matching_tag_ids)
            ).subquery()
            conditions.append(Quote.id.in_(db.session.query(tag_subquery.c.quote_id)))

        query = query.filter(db.or_(*conditions))

    # Keyset pagination when not searching (full table, ID-based)
    use_keyset = not q

    if use_keyset and cursor is not None:
        going_forward = (cursor_dir != 'prev')
        if going_forward:
            items = query.filter(Quote.id < cursor).order_by(
                Quote.id.desc()).limit(ADMIN_QUOTES_PER_PAGE + 1).all()
        else:
            items = query.filter(Quote.id > cursor).order_by(
                Quote.id.asc()).limit(ADMIN_QUOTES_PER_PAGE + 1).all()
            items = items[:ADMIN_QUOTES_PER_PAGE]
            items.reverse()

        if going_forward:
            has_more = len(items) > ADMIN_QUOTES_PER_PAGE
            items = items[:ADMIN_QUOTES_PER_PAGE]
        else:
            has_more = True

        total = get_cached_stat('total_quotes',
            lambda: db.session.query(func.count(Quote.id)).scalar() or 0)
        total_pages = max(1, (total + ADMIN_QUOTES_PER_PAGE - 1) // ADMIN_QUOTES_PER_PAGE)

        pagination = FastPagination(items, page, ADMIN_QUOTES_PER_PAGE, has_more)
        pagination.total = total
        pagination.pages = total_pages
    elif q:
        # Search: use FastPagination to skip COUNT
        query = query.order_by(Quote.id.desc())
        offset = (page - 1) * ADMIN_QUOTES_PER_PAGE
        items = query.offset(offset).limit(ADMIN_QUOTES_PER_PAGE + 1).all()
        has_more = len(items) > ADMIN_QUOTES_PER_PAGE
        items = items[:ADMIN_QUOTES_PER_PAGE]
        pagination = FastPagination(items, page, ADMIN_QUOTES_PER_PAGE, has_more)
    else:
        # First page without cursor — use OFFSET
        query = query.order_by(Quote.id.desc())
        pagination = query.paginate(page=page, per_page=ADMIN_QUOTES_PER_PAGE, error_out=False)
        items = pagination.items

    return render_template('admin/quotes.html',
                           pagination=pagination,
                           quotes=items if use_keyset or q else pagination.items,
                           search_query=q,
                           use_keyset=use_keyset)


@admin_bp.route('/quotes/add', methods=['GET', 'POST'])
def add_quote():
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        author = request.form.get('author', '').strip()
        tags_str = request.form.get('tags', '').strip()

        if not text:
            flash(_('quote_text') + ' is required.', 'error')
            return render_template('admin/quote_form.html', quote=None,
                                   form_data=request.form)

        quote = Quote(text=text, author=author)
        db.session.add(quote)
        db.session.flush()
        _sync_tags(quote, tags_str)
        db.session.commit()
        invalidate_stats_cache()
        flash(_('save') + ' OK', 'success')
        return redirect(url_for('admin.quotes'))

    return render_template('admin/quote_form.html', quote=None, form_data={})


@admin_bp.route('/quotes/<int:quote_id>/edit', methods=['GET', 'POST'])
def edit_quote(quote_id):
    quote = db.session.get(Quote, quote_id)
    if not quote:
        flash('Quote not found.', 'error')
        return redirect(url_for('admin.quotes'))

    if request.method == 'POST':
        quote.text = request.form.get('text', '').strip()
        quote.author = request.form.get('author', '').strip()
        tags_str = request.form.get('tags', '').strip()

        if not quote.text:
            flash(_('quote_text') + ' is required.', 'error')
            return render_template('admin/quote_form.html', quote=quote,
                                   form_data=request.form)

        _sync_tags(quote, tags_str)
        db.session.commit()
        flash(_('save') + ' OK', 'success')
        return redirect(url_for('admin.quotes'))

    return render_template('admin/quote_form.html', quote=quote, form_data={})


@admin_bp.route('/quotes/<int:quote_id>/delete', methods=['POST'])
def delete_quote(quote_id):
    quote = db.session.get(Quote, quote_id)
    if quote:
        db.session.delete(quote)
        db.session.commit()
        invalidate_stats_cache()
        flash(_('delete_quote') + ' OK', 'success')
    return redirect(url_for('admin.quotes'))


@admin_bp.route('/tags')
def tags_list():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    per_page = 50

    # Cache the full tag list with counts (sorted by name for admin)
    def _load_admin_tags():
        return db.session.query(
            Tag.id, Tag.name, func.count(quote_tags.c.quote_id).label('count')
        ).outerjoin(quote_tags, Tag.id == quote_tags.c.tag_id
        ).group_by(Tag.id).order_by(Tag.name).all()

    all_tags = get_cached_result('admin_tags_with_counts', _load_admin_tags)

    # Filter in Python (fast, list is small)
    if q:
        q_lower = q.lower()
        filtered = [t for t in all_tags if q_lower in t[1].lower()]
    else:
        filtered = all_tags

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    tags_page = filtered[(page - 1) * per_page: page * per_page]

    return render_template('admin/tags.html', tags=tags_page,
                           page=page, total_pages=total_pages, total=total,
                           search_query=q)


@admin_bp.route('/tags/add', methods=['POST'])
def add_tag():
    name = request.form.get('name', '').strip()
    if name:
        existing = Tag.query.filter_by(name=name).first()
        if existing:
            flash(_('tag_exists'), 'error')
        else:
            db.session.add(Tag(name=name))
            db.session.commit()
            invalidate_stats_cache()
            flash(_('save') + ' OK', 'success')
    return redirect(url_for('admin.tags_list'))


@admin_bp.route('/tags/<int:tag_id>/delete', methods=['POST'])
def delete_tag(tag_id):
    tag = db.session.get(Tag, tag_id)
    if tag:
        db.session.delete(tag)
        db.session.commit()
        invalidate_stats_cache()
        flash(_('tag_deleted'), 'success')
    return redirect(url_for('admin.tags_list'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        tab = request.form.get('tab', 'general')

        if tab == 'general':
            try:
                qpp = int(request.form.get('quotes_per_page', '20'))
                qpp = max(5, min(qpp, 100))
            except (ValueError, TypeError):
                qpp = 20
            set_setting('quotes_per_page', str(qpp))
            site_name = request.form.get('site_name', 'Zitatdatenbank').strip()[:100]
            set_setting('site_name', site_name or 'Zitatdatenbank')
            invalidate_stats_cache()
            flash(_('settings_saved'), 'success')

        elif tab == 'themes':
            theme_name = request.form.get('theme_name', DEFAULT_THEME)
            previous_theme = get_setting('theme_name', DEFAULT_THEME)
            if theme_name in THEMES or theme_name == 'custom':
                set_setting('theme_name', theme_name)
                theme_changed = theme_name != previous_theme
                if theme_changed and theme_name in THEMES:
                    stale = Setting.query.filter(
                        Setting.key.like(f'theme_{theme_name}_%')
                    ).all()
                    for row in stale:
                        db.session.delete(row)
                    if stale:
                        db.session.commit()
                if theme_name == 'custom':
                    for key in COLOR_KEYS:
                        val = request.form.get(key, '').strip()
                        if val and re.match(r'^#[0-9a-fA-F]{6}$', val):
                            set_setting(f'custom_{key}', val)
                elif theme_name in THEMES and not theme_changed:
                    defaults = THEMES[theme_name]
                    for key in ALL_THEME_KEYS:
                        val = request.form.get(key, '').strip()
                        if val and val != defaults.get(key, ''):
                            set_setting(f'theme_{theme_name}_{key}', val)
                        elif val == defaults.get(key, ''):
                            s = db.session.get(Setting, f'theme_{theme_name}_{key}')
                            if s:
                                db.session.delete(s)
                                db.session.commit()
            invalidate_stats_cache()
            flash(_('settings_saved'), 'success')

        elif tab == 'reset_theme':
            theme_name = request.form.get('theme_name', '')
            if theme_name in THEMES:
                rows = Setting.query.filter(
                    Setting.key.like(f'theme_{theme_name}_%')
                ).all()
                for row in rows:
                    db.session.delete(row)
                db.session.commit()
                invalidate_stats_cache()
                flash(_('settings_saved'), 'success')

        return redirect(url_for('admin.settings'))

    current_theme = get_setting('theme_name', DEFAULT_THEME)
    overrides = get_theme_overrides()

    custom_colors = {}
    for key in COLOR_KEYS:
        custom_colors[key] = get_setting(f'custom_{key}', THEMES[DEFAULT_THEME].get(key, ''))

    return render_template('admin/settings.html',
                           themes=THEMES,
                           current_theme=current_theme,
                           custom_colors=custom_colors,
                           overrides=overrides,
                           color_keys=COLOR_KEYS,
                           effect_keys=EFFECT_KEYS,
                           quotes_per_page=get_setting('quotes_per_page', '20'),
                           site_name_val=get_setting('site_name', 'Zitatdatenbank'))


@admin_bp.route('/backup')
def backup():
    backups = list_backups()
    logs = BackupLog.query.order_by(BackupLog.ran_at.desc()).limit(20).all()
    return render_template('admin/backup.html', backups=backups, logs=logs)


@admin_bp.route('/backup/create', methods=['POST'])
def backup_create():
    ok, result = run_backup()
    if ok:
        flash(_('backup_created'), 'success')
    else:
        flash(_('backup_failed') + f': {result}', 'error')
    return redirect(url_for('admin.backup'))


def _valid_backup_filename(filename):
    return bool(re.match(r'^zitate_backup_[\d_-]+\.tar\.gz$', filename))


@admin_bp.route('/backup/<filename>/download')
def backup_download(filename):
    if not _valid_backup_filename(filename):
        abort(404)
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@admin_bp.route('/backup/<filename>/restore', methods=['POST'])
def backup_restore(filename):
    if not _valid_backup_filename(filename):
        abort(404)
    ok, msg = restore_backup(filename)
    if ok:
        invalidate_stats_cache()
        flash(_('backup_restored'), 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin.backup'))


@admin_bp.route('/backup/<filename>/delete', methods=['POST'])
def backup_delete(filename):
    if not _valid_backup_filename(filename):
        abort(404)
    if delete_backup_file(filename):
        flash(_('backup_deleted'), 'success')
    else:
        flash('File not found.', 'error')
    return redirect(url_for('admin.backup'))
