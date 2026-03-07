from __future__ import annotations

import os
import secrets
import time

from flask import g, session

from extensions import db
from models import Setting
from config import THEMES, DEFAULT_THEME, COLOR_KEYS, EFFECT_KEYS, ALL_THEME_KEYS

# Simple in-memory cache for expensive stats queries
_stats_cache: dict[str, tuple[float, int]] = {}  # key -> (expires_at, value)
STATS_TTL = 300  # 5 minutes


def get_setting(key: str, default: str | None = None) -> str | None:
    s = db.session.get(Setting, key)
    return s.value if s else default


def set_setting(key: str, value: str) -> None:
    s = db.session.get(Setting, key) or Setting(key=key)
    s.value = value
    db.session.add(s)
    db.session.commit()


def get_lang() -> str:
    return session.get('lang', 'de')


def _(key: str) -> str:
    from translations import TRANSLATIONS
    entry = TRANSLATIONS.get(key, {})
    lang = get_lang()
    return entry.get(lang, entry.get('de', key))


def get_active_theme() -> dict[str, str]:
    """Return the active theme dict, cached to avoid 14+ DB queries per request."""
    def _load_theme():
        theme_name = get_setting('theme_name', DEFAULT_THEME)
        if theme_name == 'custom':
            base = dict(THEMES[DEFAULT_THEME])
            base['body_class'] = ''
            base['preview_css'] = ''
            for key in COLOR_KEYS:
                val = get_setting(f'custom_{key}')
                if val:
                    base[key] = val
            return base

        base = dict(THEMES.get(theme_name, THEMES[DEFAULT_THEME]))
        for key in ALL_THEME_KEYS:
            val = get_setting(f'theme_{theme_name}_{key}')
            if val:
                base[key] = val
        return base

    return get_cached_result('active_theme', _load_theme)


def get_theme_overrides() -> dict[str, dict[str, str]]:
    """Load all per-theme overrides from the DB at once."""
    rows = Setting.query.filter(Setting.key.like('theme_%_%')).all()
    overrides: dict[str, dict[str, str]] = {}
    for row in rows:
        # key format: theme_{theme_name}_{field}
        parts = row.key.split('_', 2)  # ['theme', name, field]
        if len(parts) < 3:
            continue
        prefix = parts[0]
        if prefix != 'theme':
            continue
        # theme name might contain underscores, so we need to match against known themes
        rest = row.key[6:]  # remove 'theme_'
        for tname in THEMES:
            if rest.startswith(tname + '_'):
                field = rest[len(tname) + 1:]
                if field in ALL_THEME_KEYS:
                    overrides.setdefault(tname, {})[field] = row.value
                break
    return overrides


def get_cached_result(key: str, query_fn, ttl: int = STATS_TTL):
    """Return a cached result of any type, recomputing if expired."""
    now = time.monotonic()
    if key in _stats_cache:
        expires_at, value = _stats_cache[key]
        if now < expires_at:
            return value
    value = query_fn()
    _stats_cache[key] = (now + ttl, value)
    return value


def get_cached_stat(key: str, query_fn) -> int:
    """Return a cached stat value, recomputing if expired."""
    now = time.monotonic()
    if key in _stats_cache:
        expires_at, value = _stats_cache[key]
        if now < expires_at:
            return value
    value = query_fn()
    _stats_cache[key] = (now + STATS_TTL, value)
    return value


def invalidate_stats_cache() -> None:
    """Clear the stats cache (call after adding/deleting quotes)."""
    _stats_cache.clear()


class FastPagination:
    """Lightweight pagination without COUNT query. Fetches per_page+1 to detect next page."""

    def __init__(self, items, page, per_page, has_more):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.has_next = has_more
        self.has_prev = page > 1
        self.next_num = page + 1 if has_more else None
        self.prev_num = page - 1 if page > 1 else None
        self.total = None
        self.pages = None

    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        """Yield page numbers around current page (without knowing total)."""
        # Show a window around the current page
        start = max(1, self.page - left_current)
        end = self.page + right_current + (1 if self.has_next else 0)
        for p in range(start, end + 1):
            if p == self.page or p >= 1:
                yield p


def hex_to_rgb(hex_color: str) -> str:
    try:
        h = hex_color.lstrip('#')
        return f'{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}'
    except Exception:
        return '0, 0, 0'


def is_dark_theme(theme: dict[str, str]) -> bool:
    """Check if theme background is dark (for text contrast)."""
    bg = theme.get('color_bg', '#ffffff')
    try:
        h = bg.lstrip('#')
        r, g_val, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        luminance = (0.299 * r + 0.587 * g_val + 0.114 * b) / 255
        return luminance < 0.5
    except Exception:
        return False
