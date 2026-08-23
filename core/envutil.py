# SPDX-License-Identifier: GPL-3.0-or-later
"""Minimal .env parse/format helpers."""

from __future__ import annotations


class EnvError(Exception):
    pass


def parse_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise EnvError(f"ligne {lineno}: pas de '='")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise EnvError(f"ligne {lineno}: clé vide")
        out[key] = value.strip()
    return out


def format_env(data: dict[str, str], *, sort_keys: bool = True) -> str:
    keys = sorted(data.keys()) if sort_keys else list(data.keys())
    lines = [f"{key}={data[key]}" for key in keys]
    return "\n".join(lines) + ("\n" if lines else "")
