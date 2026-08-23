# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve Node package managers missing from the desktop PATH."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def extra_bin_dirs() -> list[Path]:
    home = Path.home()
    raw = [
        os.environ.get("PNPM_HOME"),
        str(home / ".local" / "share" / "pnpm"),
        str(home / ".local" / "bin"),
        str(home / ".volta" / "bin"),
        str(home / ".local" / "share" / "fnm" / "aliases" / "default" / "bin"),
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for item in raw:
        if not item:
            continue
        path = Path(item)
        try:
            if not path.is_dir():
                continue
            key = str(path.resolve())
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def which_pnpm() -> str | None:
    found = shutil.which("pnpm")
    if found:
        return found
    for directory in extra_bin_dirs():
        candidate = directory / "pnpm"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def cache_bin() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "hub-dev" / "bin"


def pnpm_version_for(cwd: Path) -> str:
    pkg = cwd / "package.json"
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "9"
    if not isinstance(data, dict):
        return "9"
    manager = str(data.get("packageManager") or "")
    if manager.startswith("pnpm@"):
        return manager.split("@", 1)[1].split("+")[0] or "9"
    return "9"


def ensure_pnpm_shim(version: str = "9") -> Path | None:
    existing = which_pnpm()
    if existing:
        return Path(existing)
    npx = shutil.which("npx")
    corepack = shutil.which("corepack")
    if not npx and not corepack:
        return None
    directory = cache_bin()
    directory.mkdir(parents=True, exist_ok=True)
    shim = directory / "pnpm"
    if corepack:
        payload = f"#!/bin/sh\nexec {corepack} pnpm \"$@\"\n"
    else:
        payload = f"#!/bin/sh\nexec {npx} --yes pnpm@{version} \"$@\"\n"
    if not shim.is_file() or shim.read_text(encoding="utf-8") != payload:
        shim.write_text(payload, encoding="utf-8")
        shim.chmod(0o755)
    return shim


def prepare_env(env: dict[str, str], *, cwd: Path) -> dict[str, str]:
    prepared = dict(env)
    prepend: list[str] = []
    shim = ensure_pnpm_shim(pnpm_version_for(cwd))
    if shim is not None:
        prepend.append(str(shim.parent))
    prepend.extend(str(path) for path in extra_bin_dirs())
    seen: set[str] = set()
    unique: list[str] = []
    for item in prepend:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    if unique:
        prepared["PATH"] = os.pathsep.join([*unique, prepared.get("PATH", "")])
    return prepared
