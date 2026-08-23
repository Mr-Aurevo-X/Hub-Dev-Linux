# SPDX-License-Identifier: GPL-3.0-or-later
"""Hub config paths."""

from __future__ import annotations

import os
from pathlib import Path

HUB_SLUG = "dev"
FLATPAK_ID = "org.mraurevox.HubDev"


def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    path = base / "Mr-Aurevo-X" / "hubs" / HUB_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / "hub-dev"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "settings.json"
