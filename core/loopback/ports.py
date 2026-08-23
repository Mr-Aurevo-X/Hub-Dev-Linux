# SPDX-License-Identifier: GPL-3.0-or-later
"""Loopback port listing via ss."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

_LINE = re.compile(r"^\s*\w+\s+\w+\s+\w+\s+(\S+):(\d+)\s+\S+:\*\s+users:\(\(\"([^\"]+)\",pid=(\d+)")


@dataclass
class PortRow:
    port: int
    pid: int
    process_name: str
    addr: str
    is_loopback: bool


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
    import os
    import signal

    os.kill(pid, signal.SIGTERM)
