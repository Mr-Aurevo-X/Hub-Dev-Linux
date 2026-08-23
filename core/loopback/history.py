# SPDX-License-Identifier: GPL-3.0-or-later
"""Local loopback event log (config_dir/history.json)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from core.paths import config_dir

MAX_EVENTS = 200


def history_path():
    return config_dir() / "history.json"


def load() -> list[dict[str, Any]]:
    path = history_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    items: list[dict[str, Any]] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        items.append(
            {
                "ts": str(raw.get("ts") or ""),
                "event": str(raw.get("event") or ""),
                "detail": str(raw.get("detail") or ""),
            }
        )
    return items


def append(event: str, detail: str) -> None:
    items = load()
    items.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": str(event),
            "detail": str(detail),
        }
    )
    items = items[-MAX_EVENTS:]
    path = history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
