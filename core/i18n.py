# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal FR/EN strings."""

from __future__ import annotations

_LANG = "fr"

_STRINGS: dict[str, dict[str, str]] = {
    "nav_group_dev": {"fr": "Développement", "en": "Development"},
    "nav_group_formats": {"fr": "Formats", "en": "Formats"},
    "loopback_title": {"fr": "Loopback", "en": "Loopback"},
    "json_stub_title": {"fr": "JSON / .env", "en": "JSON / .env"},
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
    "home_title": {"fr": "Accueil", "en": "Home"},
    "home_lede": {
        "fr": "Hub Dev — modules à venir.",
        "en": "Hub Dev — modules coming soon.",
    },
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
