# SPDX-License-Identifier: GPL-3.0-or-later
"""Hide usernames and home paths in UI text."""

from __future__ import annotations

import re
from pathlib import Path

_HOME_USER = re.compile(r"(^|/)home/[^/]+")
_MEDIA_USER = re.compile(r"/(run/media|media)/[^/]+")
_WIN_USER = re.compile(r"/Users/[^/]+")


def display_path(path: str | Path) -> str:
    raw = str(path).replace("\\", "/")
    try:
        home = str(Path.home().expanduser().resolve()).replace("\\", "/")
    except OSError:
        home = str(Path.home()).replace("\\", "/")
    if raw == home or raw.startswith(f"{home}/"):
        raw = f"~{raw[len(home):]}"
    raw = raw.replace("/Documents and Settings/", "/Users/…/")
    raw = _HOME_USER.sub(r"\1home/…", raw)
    raw = _MEDIA_USER.sub(r"/\1/…", raw)
    raw = _WIN_USER.sub("/Users/…", raw)
    return raw


def display_detail(detail: str) -> str:
    text = str(detail)
    if text.startswith(("/", "~", "file:")):
        return display_path(text.removeprefix("file://"))
    return text
