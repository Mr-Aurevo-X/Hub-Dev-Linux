# SPDX-License-Identifier: GPL-3.0-or-later
"""Local preferences."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from core.paths import settings_path

DEFAULTS: dict[str, Any] = {
    "language": "fr",
    "language_chosen": False,
    "last_page": "loopback",
    "nav_groups_expanded": {},
}

PAGE_KEYS = ("loopback", "textdiff", "snippets", "json", "env", "lua")
PAGE_ALIASES = {"json_stub": "json", "env_stub": "env"}


def load_settings() -> dict[str, Any]:
    path = settings_path()
    if not path.is_file():
        return deepcopy(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULTS)
    merged = deepcopy(DEFAULTS)
    if isinstance(data, dict):
        merged.update(data)
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def coerce_page(value: object) -> str:
    key = str(value or "loopback").strip()
    key = PAGE_ALIASES.get(key, key)
    return key if key in PAGE_KEYS else "loopback"


def needs_language_prompt(settings: dict[str, Any]) -> bool:
    return not bool(settings.get("language_chosen"))
