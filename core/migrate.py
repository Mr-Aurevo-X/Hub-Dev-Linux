# SPDX-License-Identifier: GPL-3.0-or-later
"""One-shot migration from legacy config paths."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from core.paths import config_dir, settings_path

_MIGRATED_FLAG = ".migrated"


def run_first_launch_migration() -> None:
    flag = config_dir() / _MIGRATED_FLAG
    if flag.exists():
        return
    from core.loopback.registry import migrate_from_localdock

    migrate_from_localdock()
    _migrate_legacy_settings()
    flag.touch()


def _migrate_legacy_settings() -> None:
    if settings_path().is_file():
        return
    # Override in hub-specific migrate modules after copy from Gest/Kit.
    legacy_candidates: list[Path] = []
    for legacy in legacy_candidates:
        src = legacy / "settings.json"
        if src.is_file():
            try:
                shutil.copy2(src, settings_path())
            except OSError:
                pass
            return
