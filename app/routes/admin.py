from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models import Quote, BackupLog
from helpers import _, get_setting, set_setting
from config import ADMIN_QUOTES_PER_PAGE, THEMES, DEFAULT_THEME, BACKUP_DIR
from backup_service import run_backup, restore_backup, list_backups, delete_backup_file

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def require_login():
    pass


@admin_bp.route('/')
def dashboard():
    total_quotes = db.session.query(func.count(Quote.id)).scalar() or 0
    total_authors = db.session.query(func.count(func.distinct(Quote.author))).filter(
        Quote.author != '', Quote.author.isnot(None)
    ).scalar() or 0
    total_categories = db.session.query(func.count(func.distinct(Quote.category))).filter(
        Quote.category != '', Quote.category.isnot(None)
    ).scalar() or 0

    recent_quotes = Quote.query.order_by(Quote.id.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_quotes=total_quotes,
                           total_authors=total_authors,
                           total_categories=total_categories,
                           recent_quotes=recent_quotes)


@admin_bp.route('/quotes')
def quotes():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()

    query = Quote.query
    if q:
        like_pattern = f'%{q}%'
        query = query.filter(
            db.or_(
                Quote.text.ilike(like_pattern),
                Quote.author.ilike(like_pattern),
                Quote.category.ilike(like_pattern),
            )
        )

    query = query.order_by(Quote.id.desc())
    pagination = query.paginate(page=page, per_page=ADMIN_QUOTES_PER_PAGE, error_out=False)

    return render_template('admin/quotes.html',
                           pagination=pagination,
                           quotes=pagination.items,
                           search_query=q)


@admin_bp.route('/quotes/add', methods=['GET', 'POST'])
def add_quote():
    if request.method == 'POST':
        text = request.form.get('text', '').strip()
        author = request.form.get('author', '').strip()
        category = request.form.get('category', '').strip()

        if not text:
            flash(_('quote_text') + ' is required.', 'error')
            return render_template('admin/quote_form.html', quote=None,
                                   form_data=request.form)

        quote = Quote(text=text, author=author, category=category)
        db.session.add(quote)
        db.session.commit()
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
        quote.category = request.form.get('category', '').strip()

        if not quote.text:
            flash(_('quote_text') + ' is required.', 'error')
            return render_template('admin/quote_form.html', quote=quote,
                                   form_data=request.form)

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
        flash(_('delete_quote') + ' OK', 'success')
    return redirect(url_for('admin.quotes'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        tab = request.form.get('tab', 'general')

        if tab == 'general':
            set_setting('quotes_per_page', request.form.get('quotes_per_page', '20'))
            set_setting('site_name', request.form.get('site_name', 'Zitatdatenbank'))
            flash(_('settings_saved'), 'success')

        elif tab == 'themes':
            theme_name = request.form.get('theme_name', DEFAULT_THEME)
            if theme_name in THEMES or theme_name == 'custom':
                set_setting('theme_name', theme_name)
                if theme_name == 'custom':
                    for key in ('color_navbar', 'color_bg', 'color_text', 'color_accent',
                                'color_card_bg', 'color_footer_bg'):
                        val = request.form.get(key, '')
                        if val:
                            set_setting(f'custom_{key}', val)
            flash(_('settings_saved'), 'success')

        return redirect(url_for('admin.settings'))

    current_theme = get_setting('theme_name', DEFAULT_THEME)
    custom_colors = {}
    for key in ('color_navbar', 'color_bg', 'color_text', 'color_accent',
                'color_card_bg', 'color_footer_bg'):
        custom_colors[key] = get_setting(f'custom_{key}', THEMES[DEFAULT_THEME].get(key, ''))

    return render_template('admin/settings.html',
                           themes=THEMES,
                           current_theme=current_theme,
                           custom_colors=custom_colors,
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


@admin_bp.route('/backup/<filename>/download')
def backup_download(filename):
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@admin_bp.route('/backup/<filename>/restore', methods=['POST'])
def backup_restore(filename):
    ok, msg = restore_backup(filename)
    if ok:
        flash(_('backup_restored'), 'success')
    else:
        flash(msg, 'error')
    return redirect(url_for('admin.backup'))


@admin_bp.route('/backup/<filename>/delete', methods=['POST'])
def backup_delete(filename):
    if delete_backup_file(filename):
        flash(_('backup_deleted'), 'success')
    else:
        flash('File not found.', 'error')
    return redirect(url_for('admin.backup'))
