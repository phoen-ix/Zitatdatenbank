from __future__ import annotations

import os

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import func, or_

from extensions import db
from models import Quote, Tag, quote_tags
from helpers import _, get_setting
from config import QUOTES_PER_PAGE

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    total_quotes = db.session.query(func.count(Quote.id)).scalar() or 0
    total_authors = db.session.query(func.count(func.distinct(Quote.author))).filter(
        Quote.author != '', Quote.author.isnot(None)
    ).scalar() or 0
    total_tags = db.session.query(func.count(Tag.id)).scalar() or 0

    random_quote = None
    if total_quotes > 0:
        if db.engine.dialect.name == 'sqlite':
            random_quote = Quote.query.order_by(func.random()).first()
        else:
            random_quote = Quote.query.order_by(func.rand()).first()

    return render_template('index.html',
                           random_quote=random_quote,
                           total_quotes=total_quotes,
                           total_authors=total_authors,
                           total_tags=total_tags)


@main_bp.route('/browse')
def browse():
    page = request.args.get('page', 1, type=int)
    author_filter = request.args.get('author', '').strip()
    tag_filter = request.args.get('tag', '').strip()
    sort = request.args.get('sort', 'newest')
    per_page = int(get_setting('quotes_per_page', str(QUOTES_PER_PAGE)))

    query = Quote.query
    if author_filter:
        query = query.filter(Quote.author == author_filter)
    if tag_filter:
        query = query.filter(Quote.tags.any(Tag.name == tag_filter))

    if sort == 'oldest':
        query = query.order_by(Quote.id.asc())
    elif sort == 'author_az':
        query = query.order_by(Quote.author.asc(), Quote.id.asc())
    elif sort == 'author_za':
        query = query.order_by(Quote.author.desc(), Quote.id.asc())
    else:  # newest
        query = query.order_by(Quote.id.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('browse.html',
                           pagination=pagination,
                           quotes=pagination.items,
                           author_filter=author_filter,
                           tag_filter=tag_filter,
                           sort=sort)


@main_bp.route('/browse/authors')
def authors():
    page = request.args.get('page', 1, type=int)
    letter = request.args.get('letter', '').strip()

    query = db.session.query(
        Quote.author, func.count(Quote.id).label('count')
    ).filter(
        Quote.author != '', Quote.author.isnot(None)
    ).group_by(Quote.author).order_by(Quote.author.asc())

    if letter:
        query = query.filter(Quote.author.like(f'{letter}%'))

    all_results = query.all()
    # Manual pagination for grouped query
    per_page = 50
    total = len(all_results)
    start = (page - 1) * per_page
    end = start + per_page
    authors_page = all_results[start:end]

    # Get available first letters
    letters_query = db.session.query(
        func.upper(func.substr(Quote.author, 1, 1))
    ).filter(
        Quote.author != '', Quote.author.isnot(None)
    ).distinct().order_by(func.upper(func.substr(Quote.author, 1, 1))).all()
    letters = sorted(set(l[0] for l in letters_query if l[0] and l[0].isalpha()))

    return render_template('authors.html',
                           authors=authors_page,
                           letters=letters,
                           active_letter=letter,
                           page=page,
                           total_pages=(total + per_page - 1) // per_page if total > 0 else 1,
                           total=total)


@main_bp.route('/browse/tags')
def tags():
    page = request.args.get('page', 1, type=int)

    query = db.session.query(
        Tag.name, func.count(quote_tags.c.quote_id).label('count')
    ).join(quote_tags, Tag.id == quote_tags.c.tag_id
    ).group_by(Tag.id).order_by(func.count(quote_tags.c.quote_id).desc())

    all_results = query.all()
    per_page = 50
    total = len(all_results)
    start = (page - 1) * per_page
    end = start + per_page
    tags_page = all_results[start:end]

    return render_template('tags.html',
                           tags=tags_page,
                           page=page,
                           total_pages=(total + per_page - 1) // per_page if total > 0 else 1,
                           total=total)


@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = int(get_setting('quotes_per_page', str(QUOTES_PER_PAGE)))

    if not q:
        return render_template('search_results.html', quotes=[], pagination=None, query='')

    like_pattern = f'%{q}%'
    # Search in text, author, and tags
    tag_subquery = db.session.query(quote_tags.c.quote_id).join(
        Tag, Tag.id == quote_tags.c.tag_id
    ).filter(Tag.name.ilike(like_pattern)).subquery()

    if db.engine.dialect.name == 'sqlite':
        query = Quote.query.filter(
            or_(
                Quote.text.ilike(like_pattern),
                Quote.author.ilike(like_pattern),
                Quote.id.in_(db.session.query(tag_subquery.c.quote_id)),
            )
        )
    else:
        query = Quote.query.filter(
            or_(
                Quote.text.match(q),
                Quote.author.ilike(like_pattern),
                Quote.id.in_(db.session.query(tag_subquery.c.quote_id)),
            )
        )

    query = query.order_by(Quote.id.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('search_results.html',
                           quotes=pagination.items,
                           pagination=pagination,
                           query=q)


@main_bp.route('/quote/<int:quote_id>')
def quote_detail(quote_id):
    quote = db.session.get(Quote, quote_id)
    if not quote:
        return render_template('quote_detail.html', quote=None), 404

    # Get related quotes by same author
    related_by_author = []
    if quote.author:
        related_by_author = Quote.query.filter(
            Quote.author == quote.author, Quote.id != quote.id
        ).order_by(func.random() if db.engine.dialect.name == 'sqlite' else func.rand()
                   ).limit(5).all()

    return render_template('quote_detail.html',
                           quote=quote,
                           related_by_author=related_by_author)


@main_bp.route('/api/random')
def api_random():
    if db.engine.dialect.name == 'sqlite':
        quote = Quote.query.order_by(func.random()).first()
    else:
        quote = Quote.query.order_by(func.rand()).first()

    if not quote:
        return jsonify({'error': 'No quotes available'}), 404
    return jsonify({
        'id': quote.id,
        'text': quote.text,
        'author': quote.author or '',
        'tags': [t.name for t in quote.tags],
    })


@main_bp.route('/credits')
def credits_page():
    return render_template('credits.html')


@main_bp.route('/health')
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'ok'
    except Exception:
        db_status = 'error'

    status = 'ok' if db_status == 'ok' else 'error'
    return jsonify({
        'status': status,
        'checks': {
            'database': db_status,
        }
    }), 200 if status == 'ok' else 503


@main_bp.route('/set-lang/<lang>')
def set_lang(lang):
    if lang in ('de', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))
