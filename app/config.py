from __future__ import annotations

BACKUP_DIR: str = '/backups'

THEMES: dict[str, dict[str, str]] = {
    'klassisch': {
        'label': 'Klassisch',
        'color_navbar': '#6b4c3b',
        'color_bg': '#faf6f0',
        'color_text': '#3e2c1c',
        'color_accent': '#c9a96e',
        'color_card_bg': '#ffffff',
        'color_footer_bg': '#f0ebe3',
    },
    'modern': {
        'label': 'Modern',
        'color_navbar': '#2563eb',
        'color_bg': '#ffffff',
        'color_text': '#1e293b',
        'color_accent': '#3b82f6',
        'color_card_bg': '#f8fafc',
        'color_footer_bg': '#f1f5f9',
    },
    'dunkel': {
        'label': 'Dunkel',
        'color_navbar': '#1e1e2e',
        'color_bg': '#181825',
        'color_text': '#cdd6f4',
        'color_accent': '#89b4fa',
        'color_card_bg': '#313244',
        'color_footer_bg': '#11111b',
    },
    'wald': {
        'label': 'Wald',
        'color_navbar': '#2d6a4f',
        'color_bg': '#f0f7f4',
        'color_text': '#1b4332',
        'color_accent': '#52b788',
        'color_card_bg': '#ffffff',
        'color_footer_bg': '#d8f3dc',
    },
    'ozean': {
        'label': 'Ozean',
        'color_navbar': '#0077b6',
        'color_bg': '#f0f8ff',
        'color_text': '#023e58',
        'color_accent': '#00b4d8',
        'color_card_bg': '#ffffff',
        'color_footer_bg': '#caf0f8',
    },
}

DEFAULT_THEME: str = 'klassisch'

QUOTES_PER_PAGE: int = 20
ADMIN_QUOTES_PER_PAGE: int = 50
