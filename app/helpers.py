from __future__ import annotations

import os
import secrets

from flask import g, session

from extensions import db
from models import Setting
from config import THEMES, DEFAULT_THEME, COLOR_KEYS, EFFECT_KEYS, ALL_THEME_KEYS


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
    theme_name = get_setting('theme_name', DEFAULT_THEME)
    if theme_name == 'custom':
        base = dict(THEMES[DEFAULT_THEME])
        base['body_class'] = ''
        base['preview_css'] = ''
        # Load custom colors (legacy format)
        for key in COLOR_KEYS:
            val = get_setting(f'custom_{key}')
            if val:
                base[key] = val
        return base

    base = dict(THEMES.get(theme_name, THEMES[DEFAULT_THEME]))
    # Load per-theme overrides
    for key in ALL_THEME_KEYS:
        val = get_setting(f'theme_{theme_name}_{key}')
        if val:
            base[key] = val
    return base


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
