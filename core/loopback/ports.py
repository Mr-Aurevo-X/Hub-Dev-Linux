# SPDX-License-Identifier: GPL-3.0-or-later
"""Loopback port listing via ss."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_LINE = re.compile(r"^\s*\w+\s+\w+\s+\w+\s+(\S+):(\d+)\s+\S+:\*\s+users:\(\(\"([^\"]+)\",pid=(\d+)")
_COMMON_PORTS = (5173, 3000, 4173, 8080, 4321, 8000, 24678, 5000, 4200, 6006, 8501, 7860)
_NODE_COMMANDS = {"npm", "pnpm", "yarn", "bun", "node", "vite"}
_PORT_FLAG = re.compile(r"(?:--port|-p|--listen)\s*[=\s]+(\d{2,5})", re.I)
_CONFIG_PORT = re.compile(r"\bport\s*[:=]\s*(\d{2,5})\b")
_ENV_PORT = re.compile(r"^(?:PORT|VITE_PORT|DEV_PORT|APP_PORT|HTTP_PORT)\s*=\s*(\d{2,5})\s*$", re.M)
_NODE_SCRIPT = re.compile(r"(?:node|tsx|ts-node)\s+([^\s]+\.(?:mjs|cjs|js|ts))")
_ENV_OR_PORT = re.compile(r"process\.env\.PORT\s*\|\|\s*(\d{2,5})")
_LISTEN_PORT = re.compile(r"\.listen\(\s*(\d{2,5})")
_PORT_ASSIGN = re.compile(r"\bport\s*=\s*(?:Number\([^)]*?\|\|\s*)?(\d{2,5})", re.I)
_ENV_FILES = (".env", ".env.local", ".env.development")
_VITE_CONFIGS = ("vite.config.ts", "vite.config.js", "vite.config.mjs")
_NEXT_CONFIGS = ("next.config.js", "next.config.mjs", "next.config.ts")
_PORT_CONFIGS = _VITE_CONFIGS + _NEXT_CONFIGS + ("astro.config.mjs", "nuxt.config.ts", "nuxt.config.js")


@dataclass
class PortRow:
    port: int
    pid: int
    process_name: str
    addr: str
    is_loopback: bool


def _valid_port(raw: str | int) -> int | None:
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return None
    if 1 <= port <= 65535:
        return port
    return None


def _read_text(path: Path, limit: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _port_from_scripts(scripts: dict[str, str] | None) -> int | None:
    blob = " ".join(str(value) for value in (scripts or {}).values())
    flagged = _PORT_FLAG.search(blob)
    if flagged:
        return _valid_port(flagged.group(1))
    for port in _COMMON_PORTS:
        if str(port) in blob:
            return port
    return None


def _port_from_env(root: Path) -> int | None:
    for name in _ENV_FILES:
        match = _ENV_PORT.search(_read_text(root / name, 8000))
        if match:
            return _valid_port(match.group(1))
    return None


def _port_from_config_literal(root: Path) -> int | None:
    for name in _PORT_CONFIGS:
        match = _CONFIG_PORT.search(_read_text(root / name))
        if match:
            return _valid_port(match.group(1))
    return None


def _scoped_scripts(scripts: dict[str, str] | None, picked: str | None) -> dict[str, str] | None:
    if not scripts:
        return scripts
    if picked and picked in scripts:
        return {picked: scripts[picked]}
    return scripts


def _port_from_launch_file(root: Path, scripts: dict[str, str] | None) -> int | None:
    blob = " ".join(str(value) for value in (scripts or {}).values())
    match = _NODE_SCRIPT.search(blob)
    if match is None:
        return None
    text = _read_text(root / match.group(1), 40000)
    for regex in (_ENV_OR_PORT, _LISTEN_PORT, _PORT_ASSIGN):
        found = regex.search(text)
        if found:
            return _valid_port(found.group(1))
    return None


def _framework_default_port(root: Path, scripts: dict[str, str] | None) -> int | None:
    names = " ".join(str(key) for key in (scripts or {}))
    blob = " ".join(str(value) for value in (scripts or {}).values())
    text = f"{names} {blob}".lower()
    if "dev:local" in text:
        return None
    if any((root / name).is_file() for name in _VITE_CONFIGS) or "vite" in text:
        return 5173
    if any((root / name).is_file() for name in _NEXT_CONFIGS) or "next" in text:
        return 3000
    if (root / "nuxt.config.ts").is_file() or (root / "nuxt.config.js").is_file() or "nuxt" in text:
        return 3000
    if (root / "astro.config.mjs").is_file() or "astro" in text:
        return 4321
    if "storybook" in text:
        return 6006
    if "ng serve" in text or "angular" in text:
        return 4200
    if (root / "manage.py").is_file() or (root / "artisan").is_file():
        return 8000
    return None


def guess_preferred_port(
    path: str | Path,
    scripts: dict[str, str] | None = None,
    picked: str | None = None,
) -> int | None:
    root = Path(path)
    scoped = _scoped_scripts(scripts, picked)
    return (
        _port_from_scripts(scoped)
        or _port_from_launch_file(root, scoped)
        or _port_from_env(root)
        or _port_from_config_literal(root)
        or _framework_default_port(root, scoped)
    )


def is_loopback_port_open(port: int, rows: list[PortRow] | None = None) -> bool:
    listed = list(rows) if rows is not None else list_loopback_ports()
    return any(row.port == int(port) for row in listed)


def _pid_cwd(pid: int) -> Path | None:
    try:
        return Path(f"/proc/{pid}/cwd").resolve()
    except OSError:
        return None


def resolve_open_port(
    app: Any,
    *,
    is_running: bool = False,
    pid: int | None = None,
    rows: list[PortRow] | None = None,
) -> int | None:
    preferred = getattr(app, "preferred_port", None)
    if preferred:
        return int(preferred)
    listed = list(rows) if rows is not None else (list_loopback_ports() if is_running else [])
    if pid is not None:
        for row in listed:
            if row.pid == pid:
                return row.port
    cwd: Path | None
    try:
        cwd = Path(getattr(app, "cwd", "")).expanduser().resolve()
    except OSError:
        cwd = None
    if cwd is not None:
        for row in listed:
            proc_cwd = _pid_cwd(row.pid)
            if proc_cwd is not None and proc_cwd == cwd:
                return row.port
    guessed = guess_preferred_port(Path(getattr(app, "cwd", ".") or "."))
    if guessed:
        return guessed
    args = " ".join(str(part) for part in (getattr(app, "args", None) or []))
    command = str(getattr(app, "command", "") or "")
    if is_running and (command in _NODE_COMMANDS or "dev:local" in args):
        return 5173
    return None


def can_open(
    app: Any,
    *,
    is_running: bool = False,
    pid: int | None = None,
    rows: list[PortRow] | None = None,
) -> bool:
    return resolve_open_port(app, is_running=is_running, pid=pid, rows=rows) is not None


def list_loopback_ports() -> list[PortRow]:
    if not shutil.which("ss"):
        return []
    try:
        out = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    rows: list[PortRow] = []
    for line in out.stdout.splitlines():
        m = _LINE.match(line)
        if not m:
            continue
        addr, port_s, name, pid_s = m.groups()
        is_loopback = addr.startswith("127.") or addr == "::1" or addr == "[::1]"
        if not is_loopback:
            continue
        rows.append(PortRow(int(port_s), int(pid_s), name, addr, is_loopback))
    rows.sort(key=lambda r: r.port)
    return rows


def kill_pid(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)
