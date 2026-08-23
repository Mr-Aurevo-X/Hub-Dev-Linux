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
_COMMON_PORTS = (5173, 3000, 4173, 8080, 4321, 8000, 24678)
_NODE_COMMANDS = {"npm", "pnpm", "yarn", "node", "vite"}


@dataclass
class PortRow:
    port: int
    pid: int
    process_name: str
    addr: str
    is_loopback: bool


def guess_preferred_port(path: str | Path, scripts: dict[str, str] | None = None) -> int | None:
    root = Path(path)
    for name in ("vite.config.ts", "vite.config.js", "vite.config.mjs"):
        if (root / name).is_file():
            return 5173
    for name in ("next.config.js", "next.config.mjs", "next.config.ts"):
        if (root / name).is_file():
            return 3000
    blob = " ".join(str(value) for value in (scripts or {}).values())
    for port in _COMMON_PORTS:
        if str(port) in blob:
            return port
    return None


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
