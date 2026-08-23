# SPDX-License-Identifier: GPL-3.0-or-later
"""Project scanner — detect npm/pnpm/yarn/python dev servers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.loopback.ports import guess_preferred_port

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "dist-site",
    "target",
    "venv",
    ".venv",
    ".next",
    ".turbo",
    ".vercel",
    ".cursor",
    "graphify-out",
    "__pycache__",
    "coverage",
}
DEV_SCRIPTS = ("dev", "dev:local", "dev:local:all", "start:dev", "start")


@dataclass
class ProposedApp:
    name: str
    cwd: str
    command: str
    args: list[str]
    preferred_port: int | None = None


def normalize_root(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"not a directory: {resolved}")
    if resolved.name in SKIP_DIRS:
        raise ValueError(f"skipped directory: {resolved.name}")
    return resolved


def empty_linked_roots(roots: list[str], apps: list[Any]) -> list[str]:
    return [root for root, group in apps_grouped_by_root(roots, apps) if root and not group]


def apps_grouped_by_root(
    roots: list[str],
    apps: list[Any],
) -> list[tuple[str, list[Any]]]:
    used: set[str] = set()
    groups: list[tuple[str, list[Any]]] = []
    for root in roots:
        try:
            resolved = Path(root).expanduser().resolve()
        except OSError:
            resolved = Path(root)
        group: list[Any] = []
        for app in apps:
            if app.id in used:
                continue
            try:
                cwd = Path(app.cwd).expanduser().resolve()
            except OSError:
                continue
            if cwd == resolved or resolved in cwd.parents:
                group.append(app)
                used.add(app.id)
        groups.append((str(resolved), group))
    leftover = [app for app in apps if app.id not in used]
    if leftover:
        groups.append(("", leftover))
    return groups


def scan_root(root: Path, max_depth: int = 4) -> list[ProposedApp]:
    proposals: list[ProposedApp] = []
    try:
        start = normalize_root(root)
    except ValueError:
        start = Path(root)
        if not start.is_dir():
            return []
    _scan_dir(start, 0, max_depth, proposals)
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


def _package_manager(path: Path, data: dict[object, object]) -> str:
    manager = str(data.get("packageManager") or "")
    if manager.startswith("pnpm") or (path / "pnpm-lock.yaml").is_file() or (path / "pnpm-workspace.yaml").is_file():
        return "pnpm"
    if manager.startswith("yarn") or (path / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _detect_in_dir(path: Path) -> ProposedApp | None:
    if (path / "manage.py").is_file():
        return ProposedApp(path.name, str(path), "python", ["manage.py", "runserver", "127.0.0.1:8000"], 8000)
    pkg = path / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts") or {}
    if not isinstance(scripts, dict):
        return None
    for key in DEV_SCRIPTS:
        if key in scripts:
            command = _package_manager(path, data)
            scripts_text = {str(name): str(value) for name, value in scripts.items()}
            return ProposedApp(
                path.name,
                str(path),
                command,
                ["run", str(key)],
                guess_preferred_port(path, scripts_text),
            )
    return None
