from __future__ import annotations

import os
import secrets

from flask import g, session

from extensions import db
from models import Setting
from config import THEMES, DEFAULT_THEME


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
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
    # Check for custom color overrides
    result = dict(theme)
    for color_key in ('color_navbar', 'color_bg', 'color_text', 'color_accent',
                      'color_card_bg', 'color_footer_bg'):
        custom = get_setting(f'custom_{color_key}')
        if custom and get_setting('theme_name') == 'custom':
            result[color_key] = custom
    return result


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
