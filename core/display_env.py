# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe GDK display defaults (Mint/VM)."""

from __future__ import annotations

import os


def apply_safe_display_env() -> dict[str, str]:
    applied: dict[str, str] = {}
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("GDK_BACKEND", "x11")
        applied["GDK_BACKEND"] = "x11"
    return applied
