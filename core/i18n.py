# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal FR/EN strings."""

from __future__ import annotations

_LANG = "fr"

_STRINGS: dict[str, dict[str, str]] = {
    "nav_group_dev": {"fr": "Développement", "en": "Development"},
    "nav_group_tools": {"fr": "Outils", "en": "Tools"},
    "nav_group_formats": {"fr": "Formats", "en": "Formats"},
    "loopback_title": {"fr": "Loopback", "en": "Loopback"},
    "textdiff_title": {"fr": "Diff texte", "en": "Text diff"},
    "snippets_title": {"fr": "Snippets", "en": "Snippets"},
    "json_stub_title": {"fr": "JSON", "en": "JSON"},
    "env_stub_title": {"fr": ".env", "en": ".env"},
    "loopback_scan": {"fr": "Scanner", "en": "Scan"},
    "loopback_add_root": {"fr": "Ajouter racine", "en": "Add root"},
    "loopback_refresh_ports": {"fr": "Actualiser ports", "en": "Refresh ports"},
    "loopback_apps": {"fr": "Applications", "en": "Applications"},
    "loopback_ports": {"fr": "Ports loopback", "en": "Loopback ports"},
    "loopback_start": {"fr": "Démarrer", "en": "Start"},
    "loopback_stop": {"fr": "Arrêter", "en": "Stop"},
    "loopback_remove": {"fr": "Retirer", "en": "Remove"},
    "loopback_open_url": {"fr": "Ouvrir", "en": "Open"},
    "json_pretty": {"fr": "Pretty JSON", "en": "Pretty JSON"},
    "json_minify": {"fr": "Minify JSON", "en": "Minify JSON"},
    "env_sort": {"fr": "Trier clés", "en": "Sort keys"},
    "env_validate": {"fr": "Valider", "en": "Validate"},
    "env_ok": {"fr": "Fichier .env valide", "en": ".env file is valid"},
    "welcome_lang": {"fr": "Langue", "en": "Language"},
    "welcome_lang_body": {
        "fr": "Choisissez la langue de l'interface.",
        "en": "Choose the interface language.",
    },
    "pending_textdiff": {
        "fr": "Fichiers reçus depuis Hub Utilitaires.",
        "en": "Files received from Utilities Hub.",
    },
    "group_files": {"fr": "Fichiers", "en": "Files"},
    "group_actions": {"fr": "Actions", "en": "Actions"},
    "textdiff_a": {"fr": "Fichier A", "en": "File A"},
    "textdiff_b": {"fr": "Fichier B", "en": "File B"},
    "textdiff_ignore_ws": {"fr": "Ignorer espaces", "en": "Ignore whitespace"},
    "textdiff_ignore_eol": {"fr": "Ignorer fins de ligne", "en": "Ignore line endings"},
    "snippets_name": {"fr": "Nom", "en": "Name"},
    "snippets_tags": {"fr": "Tags", "en": "Tags"},
    "snippets_filter": {"fr": "Filtrer tag", "en": "Filter tag"},
    "snippets_save": {"fr": "Enregistrer", "en": "Save"},
    "snippets_delete": {"fr": "Supprimer", "en": "Delete"},
    "snippets_filter_go": {"fr": "Filtrer", "en": "Filter"},
    "snippets_export": {"fr": "Export JSON", "en": "Export JSON"},
    "snippets_import": {"fr": "Import JSON", "en": "Import JSON"},
    "copy": {"fr": "Copier", "en": "Copy"},
    "copied": {"fr": "Copié", "en": "Copied"},
}


def set_language(lang: str) -> None:
    global _LANG  # noqa: PLW0603
    _LANG = "en" if lang == "en" else "fr"


def language() -> str:
    return _LANG


def t(key: str, **kwargs: str) -> str:
    row = _STRINGS.get(key, {})
    text = row.get(_LANG) or row.get("fr") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text
