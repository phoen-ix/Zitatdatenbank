from __future__ import annotations

import re
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy import func, or_
from sqlalchemy.orm import selectinload

from extensions import db, limiter
from models import Quote, Tag, quote_tags
from helpers import _, get_setting, get_cached_stat, get_cached_result, FastPagination
from config import QUOTES_PER_PAGE

main_bp = Blueprint('main', __name__)


def _get_per_page() -> int:
    """Get quotes_per_page setting, safely defaulting on corrupt values."""
    try:
        return int(get_cached_result('quotes_per_page',
            lambda: get_setting('quotes_per_page', str(QUOTES_PER_PAGE))))
    except (ValueError, TypeError):
        return QUOTES_PER_PAGE


def _escape_like(q: str) -> str:
    """Escape LIKE metacharacters so % and _ are matched literally."""
    return q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _sanitize_fulltext(q: str) -> str:
    """Strip FULLTEXT boolean-mode operators to prevent query syntax errors."""
    return re.sub(r'[+\-~*"@<>()]+', ' ', q).strip()


def _random_quote():
    """Get a random quote efficiently without ORDER BY RAND()."""
    if db.engine.dialect.name == 'sqlite':
        return Quote.query.options(selectinload(Quote.tags)).order_by(func.random()).first()

    # Fast random: pick a random ID in the range
    max_id = db.session.query(func.max(Quote.id)).scalar()
    if not max_id:
        return None
    import random
    for _ in range(5):
        rand_id = random.randint(1, max_id)
        quote = db.session.query(Quote).options(
            selectinload(Quote.tags)).filter(Quote.id >= rand_id).first()
        if quote:
            return quote
    return db.session.query(Quote).options(selectinload(Quote.tags)).first()


@main_bp.route('/')
def index():
    total_quotes = get_cached_stat('total_quotes',
        lambda: db.session.query(func.count(Quote.id)).scalar() or 0)
    total_authors = get_cached_stat('total_authors',
        lambda: db.session.query(func.count(func.distinct(Quote.author))).filter(
            Quote.author != '', Quote.author.isnot(None)
        ).scalar() or 0)
    total_tags = get_cached_stat('total_tags',
        lambda: db.session.query(func.count(Tag.id)).scalar() or 0)

    random_quote = _random_quote() if total_quotes > 0 else None

    return render_template('index.html',
                           random_quote=random_quote,
                           total_quotes=total_quotes,
                           total_authors=total_authors,
                           total_tags=total_tags)


@main_bp.route('/browse')
def browse():
    page = max(1, request.args.get('page', 1, type=int))
    author_filter = request.args.get('author', '').strip()
    tag_filter = request.args.get('tag', '').strip()
    sort = request.args.get('sort', 'newest')
    per_page = _get_per_page()
    cursor = request.args.get('cursor', type=int)
    if cursor is not None and cursor < 1:
        cursor = None
    cursor_dir = request.args.get('_cursor_dir', 'next')  # 'next' or 'prev'

    query = Quote.query.options(selectinload(Quote.tags))
    if author_filter:
        query = query.filter(Quote.author == author_filter)
    if tag_filter:
        query = query.filter(Quote.tags.any(Tag.name == tag_filter))

    # Keyset pagination for ID-based sorts (no filters) — O(1) at any depth
    use_keyset = sort in ('newest', 'oldest') and not author_filter and not tag_filter

    if use_keyset and cursor is not None:
        going_forward = (cursor_dir != 'prev')

        if sort == 'newest':
            if going_forward:
                items = query.filter(Quote.id < cursor).order_by(
                    Quote.id.desc()).limit(per_page + 1).all()
            else:
                # Going back: get items with higher IDs, ordered ASC, then reverse
                items = query.filter(Quote.id > cursor).order_by(
                    Quote.id.asc()).limit(per_page + 1).all()
                items = items[:per_page]
                items.reverse()
        else:  # oldest
            if going_forward:
                items = query.filter(Quote.id > cursor).order_by(
                    Quote.id.asc()).limit(per_page + 1).all()
            else:
                items = query.filter(Quote.id < cursor).order_by(
                    Quote.id.desc()).limit(per_page + 1).all()
                items = items[:per_page]
                items.reverse()

        if going_forward:
            has_more = len(items) > per_page
            items = items[:per_page]
        else:
            has_more = True  # We came from a next page, so there's always more ahead

        # Get total count (cached) for page count display
        total = get_cached_stat('total_quotes',
            lambda: db.session.query(func.count(Quote.id)).scalar() or 0)
        total_pages = max(1, (total + per_page - 1) // per_page)

        pagination = FastPagination(items, page, per_page, has_more)
        pagination.total = total
        pagination.pages = total_pages
    else:
        # OFFSET pagination for author sorts, filtered queries, or first page
        if sort == 'oldest':
            query = query.order_by(Quote.id.asc())
        elif sort == 'author_az':
            query = query.order_by(Quote.author.asc(), Quote.id.asc())
        elif sort == 'author_za':
            query = query.order_by(Quote.author.desc(), Quote.id.asc())
        else:  # newest
            query = query.order_by(Quote.id.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        items = pagination.items

    return render_template('browse.html',
                           pagination=pagination,
                           quotes=items,
                           author_filter=author_filter,
                           tag_filter=tag_filter,
                           sort=sort,
                           use_keyset=use_keyset and not author_filter and not tag_filter)


@main_bp.route('/browse/authors')
def authors():
    page = max(1, request.args.get('page', 1, type=int))
    letter = request.args.get('letter', '').strip()
    per_page = 50

    # Cache the full author list (small — only ~25 distinct authors with counts)
    def _load_all_authors():
        return db.session.query(
            Quote.author, func.count(Quote.id).label('count')
        ).filter(
            Quote.author != '', Quote.author.isnot(None)
        ).group_by(Quote.author).order_by(Quote.author.asc()).all()

    all_authors = get_cached_result('all_authors', _load_all_authors)

    # Filter by letter in Python (fast, list is small)
    if letter:
        filtered = [(a, c) for a, c in all_authors if a and a[0].upper() == letter.upper()]
    else:
        filtered = all_authors

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    authors_page = filtered[(page - 1) * per_page: page * per_page]

    # Extract letters from cached data
    letters = sorted(set(a[0].upper() for a, c in all_authors if a and a[0].isalpha()))

    return render_template('authors.html',
                           authors=authors_page,
                           letters=letters,
                           active_letter=letter,
                           page=page,
                           total_pages=total_pages,
                           total=total)


@main_bp.route('/browse/tags')
def tags():
    page = max(1, request.args.get('page', 1, type=int))
    per_page = 50

    # Cache the full tag list with counts (small number of tags)
    def _load_all_tags():
        return db.session.query(
            Tag.name, func.count(quote_tags.c.quote_id).label('count')
        ).join(quote_tags, Tag.id == quote_tags.c.tag_id
        ).group_by(Tag.id).order_by(
            func.count(quote_tags.c.quote_id).desc()
        ).all()

    all_tags = get_cached_result('all_tags_with_counts', _load_all_tags)

    total = len(all_tags)
    total_pages = max(1, (total + per_page - 1) // per_page)
    tags_page = all_tags[(page - 1) * per_page: page * per_page]

    return render_template('tags.html',
                           tags=tags_page,
                           page=page,
                           total_pages=total_pages,
                           total=total)


@main_bp.route('/search')
@limiter.limit('30/minute')
def search():
    q = request.args.get('q', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    per_page = _get_per_page()

    if not q:
        return render_template('search_results.html', quotes=[], pagination=None, query='')

    like_pattern = f'%{_escape_like(q)}%'

    # Find matching tag IDs from cache (microseconds vs SQL ILIKE scan)
    def _load_tag_map():
        rows = db.session.query(Tag.id, Tag.name).all()
        return [(tid, name.lower()) for tid, name in rows]

    tag_map = get_cached_result('tag_id_name_map', _load_tag_map)
    q_lower = q.lower()
    matching_tag_ids = [tid for tid, name in tag_map if q_lower in name]

    # Build tag filter using exact IDs (fast index lookup)
    tag_filter = None
    if matching_tag_ids:
        tag_subquery = db.session.query(quote_tags.c.quote_id).filter(
            quote_tags.c.tag_id.in_(matching_tag_ids)
        ).subquery()
        tag_filter = Quote.id.in_(db.session.query(tag_subquery.c.quote_id))

    if db.engine.dialect.name == 'sqlite':
        conditions = [Quote.text.ilike(like_pattern), Quote.author.ilike(like_pattern)]
    else:
        ft_q = _sanitize_fulltext(q)
        if ft_q:
            conditions = [Quote.text.match(ft_q), Quote.author.match(ft_q)]
        else:
            conditions = [Quote.text.ilike(like_pattern), Quote.author.ilike(like_pattern)]

    if tag_filter is not None:
        conditions.append(tag_filter)

    query = Quote.query.options(selectinload(Quote.tags)).filter(
        or_(*conditions)).order_by(Quote.id.asc())

    # Fetch per_page+1 to detect next page (avoids expensive COUNT query)
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page + 1).all()
    has_more = len(items) > per_page
    items = items[:per_page]

    pagination = FastPagination(items, page, per_page, has_more)

    return render_template('search_results.html',
                           quotes=items,
                           pagination=pagination,
                           query=q)


@main_bp.route('/quote/<int:quote_id>')
def quote_detail(quote_id):
    quote = db.session.get(Quote, quote_id, options=[selectinload(Quote.tags)])
    if not quote:
        return render_template('quote_detail.html', quote=None), 404

    # Get related quotes by same author
    related_by_author = []
    if quote.author:
        related_by_author = Quote.query.options(selectinload(Quote.tags)).filter(
            Quote.author == quote.author, Quote.id != quote.id
        ).limit(5).all()

    return render_template('quote_detail.html',
                           quote=quote,
                           related_by_author=related_by_author)


def _quote_to_dict(quote):
    """Convert a Quote to an API-friendly dict."""
    return {
        'id': quote.id,
        'text': quote.text,
        'author': quote.author or '',
        'tags': [t.name for t in quote.tags],
    }


@main_bp.route('/api/random')
@limiter.limit('30/minute')
def api_random():
    quote = _random_quote()

    if not quote:
        return jsonify({'error': 'No quotes available'}), 404
    return jsonify(_quote_to_dict(quote))


@main_bp.route('/api/quotes')
@limiter.limit('30/minute')
def api_quotes():
    page = max(1, request.args.get('page', 1, type=int))
    per_page = max(1, min(request.args.get('per_page', 20, type=int), 100))
    author = request.args.get('author', '').strip()
    tag = request.args.get('tag', '').strip()
    q = request.args.get('q', '').strip()

    query = Quote.query.options(selectinload(Quote.tags))

    if author:
        query = query.filter(Quote.author == author)
    if tag:
        query = query.filter(Quote.tags.any(Tag.name == tag))
    if q:
        like_pat = f'%{_escape_like(q)}%'
        if db.engine.dialect.name == 'sqlite':
            query = query.filter(
                or_(Quote.text.ilike(like_pat), Quote.author.ilike(like_pat)))
        else:
            ft_q = _sanitize_fulltext(q)
            if ft_q:
                query = query.filter(or_(Quote.text.match(ft_q), Quote.author.match(ft_q)))
            else:
                query = query.filter(
                    or_(Quote.text.ilike(like_pat), Quote.author.ilike(like_pat)))

    query = query.order_by(Quote.id.desc())

    items = query.offset((page - 1) * per_page).limit(per_page + 1).all()
    has_more = len(items) > per_page
    items = items[:per_page]

    return jsonify({
        'quotes': [_quote_to_dict(row) for row in items],
        'page': page,
        'per_page': per_page,
        'has_next': has_more,
        'has_prev': page > 1,
    })


@main_bp.route('/api/quotes/<int:quote_id>')
@limiter.limit('60/minute')
def api_quote_detail(quote_id):
    quote = db.session.get(Quote, quote_id, options=[selectinload(Quote.tags)])
    if not quote:
        return jsonify({'error': 'Quote not found'}), 404
    return jsonify(_quote_to_dict(quote))


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
    ref = request.referrer
    if ref and urlparse(ref).netloc not in ('', request.host):
        ref = None
    return redirect(ref or url_for('main.index'))
