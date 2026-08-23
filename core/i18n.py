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
    "json_title": {"fr": "JSON", "en": "JSON"},
    "env_title": {"fr": ".env", "en": ".env"},
    "lua_title": {"fr": "Lua", "en": "Lua"},
    "json_stub_title": {"fr": "JSON", "en": "JSON"},
    "env_stub_title": {"fr": ".env", "en": ".env"},
    "loopback_scan": {"fr": "Scanner", "en": "Scan"},
    "loopback_scan_disk": {"fr": "Scanner", "en": "Scan"},
    "loopback_scan_disk_running": {"fr": "Scan de tous les disques…", "en": "Scanning all disks…"},
    "loopback_scan_disk_done": {"fr": "{count} serveur(s) lançable(s)", "en": "{count} launchable server(s)"},
    "loopback_cancel_scan": {"fr": "Annuler le scan", "en": "Cancel scan"},
    "loopback_clear_scan": {"fr": "Clear scan", "en": "Clear scan"},
    "loopback_scan_cleared": {"fr": "Scan vidé ({count})", "en": "Scan cleared ({count})"},
    "loopback_add_root": {"fr": "Ajouter racine", "en": "Add root"},
    "loopback_link_path": {"fr": "Lier", "en": "Link"},
    "loopback_paste_hint": {"fr": "Coller un dossier…", "en": "Paste a folder…"},
    "loopback_explorer": {"fr": "Localhost", "en": "Localhost"},
    "loopback_roots": {"fr": "Dossiers liés", "en": "Linked folders"},
    "loopback_remove_root": {"fr": "Retirer le dossier", "en": "Remove folder"},
    "loopback_running": {"fr": "En cours", "en": "Running"},
    "loopback_stopped": {"fr": "Arrêté", "en": "Stopped"},
    "loopback_no_apps": {
        "fr": "Aucun serveur lançable. Scanner fouille tous les disques, sans cibler un dossier.",
        "en": "No launchable servers. Scan walks every disk — no folder targeting required.",
    },
    "loopback_bad_root": {
        "fr": "Dossier ignoré (chemin invalide ou dossier système).",
        "en": "Folder ignored (invalid path or system directory).",
    },
    "loopback_linked": {"fr": "Dossier lié", "en": "Folder linked"},
    "loopback_already": {"fr": "Dossier déjà lié — scan…", "en": "Folder already linked — scanning…"},
    "loopback_scan_done": {"fr": "{count} serveur(s)", "en": "{count} server(s)"},
    "loopback_refresh_ports": {"fr": "Actualiser ports", "en": "Refresh ports"},
    "loopback_apps": {"fr": "Applications", "en": "Applications"},
    "loopback_ports": {"fr": "Ports loopback", "en": "Loopback ports"},
    "loopback_start": {"fr": "Démarrer", "en": "Start"},
    "loopback_stop": {"fr": "Arrêter", "en": "Stop"},
    "loopback_remove": {"fr": "Retirer", "en": "Remove"},
    "loopback_open_url": {"fr": "Ouvrir", "en": "Open"},
    "loopback_add_edit": {"fr": "Ajouter / Éditer", "en": "Add / Edit"},
    "loopback_history": {"fr": "Historique", "en": "History"},
    "loopback_field_name": {"fr": "Nom", "en": "Name"},
    "loopback_field_cwd": {"fr": "Répertoire", "en": "Working directory"},
    "loopback_field_command": {"fr": "Commande", "en": "Command"},
    "loopback_field_args": {"fr": "Arguments", "en": "Arguments"},
    "loopback_field_port": {"fr": "Port", "en": "Port"},
    "loopback_field_profile": {"fr": "Profil", "en": "Profile"},
    "loopback_need_name": {"fr": "Nom requis", "en": "Name required"},
    "loopback_need_command": {"fr": "Commande requise", "en": "Command required"},
    "loopback_bad_port": {"fr": "Port invalide", "en": "Invalid port"},
    "profile_dev": {"fr": "dev", "en": "dev"},
    "profile_preview": {"fr": "preview", "en": "preview"},
    "profile_prod": {"fr": "prod", "en": "prod"},
    "dialog_ok": {"fr": "OK", "en": "OK"},
    "dialog_cancel": {"fr": "Annuler", "en": "Cancel"},
    "json_pretty": {"fr": "Pretty JSON", "en": "Pretty JSON"},
    "json_minify": {"fr": "Minify JSON", "en": "Minify JSON"},
    "env_sort": {"fr": "Trier clés", "en": "Sort keys"},
    "env_validate": {"fr": "Valider", "en": "Validate"},
    "env_ok": {"fr": "Fichier .env valide", "en": ".env file is valid"},
    "lua_pretty": {"fr": "Pretty Lua", "en": "Pretty Lua"},
    "lua_check": {"fr": "Vérifier", "en": "Check"},
    "lua_ok": {"fr": "Syntaxe Lua valide", "en": "Lua syntax is valid"},
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
