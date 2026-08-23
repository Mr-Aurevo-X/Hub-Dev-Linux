# SPDX-License-Identifier: GPL-3.0-or-later
"""Project scanner — detect npm/python dev servers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", "dist", "target", "venv", ".next", ".turbo", ".vercel"}
DEV_SCRIPTS = ("dev", "dev:local", "dev:local:all", "start:dev")


@dataclass
class ProposedApp:
    name: str
    cwd: str
    command: str
    args: list[str]
    preferred_port: int | None = None


def scan_root(root: Path, max_depth: int = 3) -> list[ProposedApp]:
    proposals: list[ProposedApp] = []
    _scan_dir(root, 0, max_depth, proposals)
    return proposals


def _scan_dir(path: Path, depth: int, max_depth: int, out: list[ProposedApp]) -> None:
    if depth > max_depth:
        return
    proposal = _detect_in_dir(path)
    if proposal is not None:
        out.append(proposal)
    if depth == max_depth:
        return
    try:
        children = list(path.iterdir())
    except OSError:
        return
    for child in children:
        if not child.is_dir() or child.name in SKIP_DIRS:
            continue
        _scan_dir(child, depth + 1, max_depth, out)


def _detect_in_dir(path: Path) -> ProposedApp | None:
    if (path / "manage.py").is_file():
        return ProposedApp(path.name, str(path), "python", ["manage.py", "runserver", "127.0.0.1:8000"], 8000)
    pkg = path / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        scripts = data.get("scripts") or {}
        for key in DEV_SCRIPTS:
            if key in scripts:
                return ProposedApp(path.name, str(path), "npm", ["run", key], _guess_vite_port(path))
        if "dev" in scripts:
            return ProposedApp(path.name, str(path), "npm", ["run", "dev"], _guess_vite_port(path))
    return None


def _guess_vite_port(path: Path) -> int | None:
    for name in ("vite.config.ts", "vite.config.js", "vite.config.mjs"):
        cfg = path / name
        if cfg.is_file():
            return 5173
    return None
