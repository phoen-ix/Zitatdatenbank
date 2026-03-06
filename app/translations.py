from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    # Navigation
    'nav_home': {'de': 'Startseite', 'en': 'Home'},
    'nav_browse': {'de': 'Durchsuchen', 'en': 'Browse'},
    'nav_authors': {'de': 'Autoren', 'en': 'Authors'},
    'nav_categories': {'de': 'Kategorien', 'en': 'Categories'},
    'nav_search': {'de': 'Suche', 'en': 'Search'},
    'nav_admin': {'de': 'Verwaltung', 'en': 'Admin'},
    'nav_login': {'de': 'Anmelden', 'en': 'Login'},
    'nav_logout': {'de': 'Abmelden', 'en': 'Logout'},
    'nav_language': {'de': 'EN', 'en': 'DE'},

    # Index page
    'site_title': {'de': 'Zitatdatenbank', 'en': 'Quote Database'},
    'site_subtitle': {'de': 'Sammlung deutscher Zitate', 'en': 'Collection of German Quotes'},
    'random_quote': {'de': 'Zufallszitat', 'en': 'Random Quote'},
    'new_random': {'de': 'Neues Zitat', 'en': 'New Quote'},
    'total_quotes': {'de': 'Zitate gesamt', 'en': 'Total Quotes'},
    'total_authors': {'de': 'Autoren', 'en': 'Authors'},
    'total_categories': {'de': 'Kategorien', 'en': 'Categories'},

    # Browse
    'browse_quotes': {'de': 'Zitate durchsuchen', 'en': 'Browse Quotes'},
    'all_authors': {'de': 'Alle Autoren', 'en': 'All Authors'},
    'all_categories': {'de': 'Alle Kategorien', 'en': 'All Categories'},
    'filter_by_author': {'de': 'Nach Autor filtern', 'en': 'Filter by Author'},
    'filter_by_category': {'de': 'Nach Kategorie filtern', 'en': 'Filter by Category'},
    'sort_by': {'de': 'Sortieren nach', 'en': 'Sort by'},
    'sort_newest': {'de': 'Neueste zuerst', 'en': 'Newest first'},
    'sort_oldest': {'de': 'Älteste zuerst', 'en': 'Oldest first'},
    'sort_author_az': {'de': 'Autor A-Z', 'en': 'Author A-Z'},
    'sort_author_za': {'de': 'Autor Z-A', 'en': 'Author Z-A'},
    'quotes_count': {'de': 'Zitate', 'en': 'quotes'},
    'no_quotes_found': {'de': 'Keine Zitate gefunden.', 'en': 'No quotes found.'},
    'quote': {'de': 'Zitat', 'en': 'Quote'},
    'author': {'de': 'Autor', 'en': 'Author'},
    'category': {'de': 'Kategorie', 'en': 'Category'},
    'unknown_author': {'de': 'Unbekannt', 'en': 'Unknown'},

    # Search
    'search_placeholder': {'de': 'Zitate suchen...', 'en': 'Search quotes...'},
    'search_results': {'de': 'Suchergebnisse', 'en': 'Search Results'},
    'search_results_for': {'de': 'Suchergebnisse für', 'en': 'Search results for'},
    'no_results': {'de': 'Keine Ergebnisse gefunden.', 'en': 'No results found.'},
    'search_button': {'de': 'Suchen', 'en': 'Search'},

    # Quote detail
    'quote_detail': {'de': 'Zitatdetails', 'en': 'Quote Details'},
    'back_to_browse': {'de': 'Zurück zur Übersicht', 'en': 'Back to Browse'},
    'more_by_author': {'de': 'Weitere Zitate von', 'en': 'More quotes by'},
    'more_in_category': {'de': 'Weitere Zitate in Kategorie', 'en': 'More quotes in category'},

    # Admin
    'admin_dashboard': {'de': 'Admin-Dashboard', 'en': 'Admin Dashboard'},
    'admin_quotes': {'de': 'Zitate verwalten', 'en': 'Manage Quotes'},
    'admin_settings': {'de': 'Einstellungen', 'en': 'Settings'},
    'admin_backup': {'de': 'Backup', 'en': 'Backup'},
    'add_quote': {'de': 'Zitat hinzufügen', 'en': 'Add Quote'},
    'edit_quote': {'de': 'Zitat bearbeiten', 'en': 'Edit Quote'},
    'delete_quote': {'de': 'Zitat löschen', 'en': 'Delete Quote'},
    'save': {'de': 'Speichern', 'en': 'Save'},
    'cancel': {'de': 'Abbrechen', 'en': 'Cancel'},
    'delete': {'de': 'Löschen', 'en': 'Delete'},
    'confirm_delete': {'de': 'Wirklich löschen?', 'en': 'Really delete?'},
    'actions': {'de': 'Aktionen', 'en': 'Actions'},
    'edit': {'de': 'Bearbeiten', 'en': 'Edit'},
    'quote_text': {'de': 'Zitattext', 'en': 'Quote Text'},

    # Settings
    'settings_general': {'de': 'Allgemein', 'en': 'General'},
    'settings_themes': {'de': 'Themen', 'en': 'Themes'},
    'settings_backup': {'de': 'Backup', 'en': 'Backup'},
    'theme_active': {'de': 'Aktives Thema', 'en': 'Active Theme'},
    'theme_select': {'de': 'Thema auswählen', 'en': 'Select Theme'},
    'custom_colors': {'de': 'Eigene Farben', 'en': 'Custom Colors'},
    'theme_colors': {'de': 'Farben anpassen', 'en': 'Customize Colors'},
    'theme_effects': {'de': 'Effekte', 'en': 'Effects'},
    'typing_speed': {'de': 'Tippgeschwindigkeit', 'en': 'Typing Speed'},
    'typing_speed_help': {'de': '0 = aus, kleiner = schneller', 'en': '0 = off, lower = faster'},
    'particle_count': {'de': 'Partikelanzahl', 'en': 'Particle Count'},
    'particle_count_help': {'de': 'Blasen, Sterne, Funken etc.', 'en': 'Bubbles, stars, embers etc.'},
    'reset_defaults': {'de': 'Zurücksetzen', 'en': 'Reset to Defaults'},
    'quotes_per_page': {'de': 'Zitate pro Seite', 'en': 'Quotes per Page'},
    'site_name': {'de': 'Seitenname', 'en': 'Site Name'},
    'settings_saved': {'de': 'Einstellungen gespeichert.', 'en': 'Settings saved.'},

    # Backup
    'create_backup': {'de': 'Backup erstellen', 'en': 'Create Backup'},
    'restore_backup': {'de': 'Backup wiederherstellen', 'en': 'Restore Backup'},
    'download_backup': {'de': 'Herunterladen', 'en': 'Download'},
    'delete_backup': {'de': 'Backup löschen', 'en': 'Delete Backup'},
    'no_backups': {'de': 'Keine Backups vorhanden.', 'en': 'No backups available.'},
    'backup_created': {'de': 'Backup erstellt.', 'en': 'Backup created.'},
    'backup_restored': {'de': 'Backup wiederhergestellt.', 'en': 'Backup restored.'},
    'backup_deleted': {'de': 'Backup gelöscht.', 'en': 'Backup deleted.'},
    'backup_failed': {'de': 'Backup fehlgeschlagen.', 'en': 'Backup failed.'},
    'confirm_restore': {'de': 'Wirklich wiederherstellen? Alle aktuellen Daten werden überschrieben!',
                        'en': 'Really restore? All current data will be overwritten!'},

    # Auth
    'login_title': {'de': 'Anmelden', 'en': 'Login'},
    'username': {'de': 'Benutzername', 'en': 'Username'},
    'password': {'de': 'Passwort', 'en': 'Password'},
    'login_button': {'de': 'Anmelden', 'en': 'Login'},
    'login_failed': {'de': 'Ungültiger Benutzername oder Passwort.', 'en': 'Invalid username or password.'},
    'login_required': {'de': 'Bitte melden Sie sich an.', 'en': 'Please log in.'},

    # Misc
    'page': {'de': 'Seite', 'en': 'Page'},
    'of': {'de': 'von', 'en': 'of'},
    'prev': {'de': 'Zurück', 'en': 'Prev'},
    'next': {'de': 'Weiter', 'en': 'Next'},
    'footer_text': {'de': 'Zitatdatenbank', 'en': 'Quote Database'},
    'id': {'de': 'Nr.', 'en': 'No.'},
}
