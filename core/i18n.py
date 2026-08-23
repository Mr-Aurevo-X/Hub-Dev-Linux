# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal FR/EN strings."""

from __future__ import annotations

_LANG = "fr"

_STRINGS: dict[str, dict[str, str]] = {
    "nav_group_dev": {"fr": "Développement", "en": "Development"},
    "nav_group_formats": {"fr": "Formats", "en": "Formats"},
    "loopback_title": {"fr": "Loopback", "en": "Loopback"},
    "json_stub_title": {"fr": "JSON / .env (bientôt)", "en": "JSON / .env (soon)"},
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


def t(key: str) -> str:
    row = _STRINGS.get(key, {})
    return row.get(_LANG) or row.get("fr") or key
