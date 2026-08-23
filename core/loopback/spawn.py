# SPDX-License-Identifier: GPL-3.0-or-later
"""Process spawn/stop for loopback apps."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from core.loopback import history, ports
from core.loopback.registry import AppEntry, Registry

_running: dict[str, subprocess.Popen[bytes]] = {}


def is_running(app_id: str) -> bool:
    proc = _running.get(app_id)
    if proc is None:
        return False
    if proc.poll() is not None:
        _running.pop(app_id, None)
        return False
    return True


def running_pid(app_id: str) -> int | None:
    if not is_running(app_id):
        return None
    proc = _running.get(app_id)
    return None if proc is None else proc.pid


def start(entry: AppEntry) -> None:
    reg = Registry.load()
    reg.validate_command(entry.command)
    if is_running(entry.id):
        raise RuntimeError("déjà en cours")
    if entry.preferred_port and ports.is_loopback_port_open(int(entry.preferred_port)):
        history.append("already", entry.name or entry.id)
        return
    cwd = Path(entry.cwd).expanduser()
    if not cwd.is_dir():
        raise FileNotFoundError(str(cwd))
    env = os.environ.copy()
    if entry.force_loopback:
        env.setdefault("HOST", "127.0.0.1")
        env.setdefault("HOSTNAME", "127.0.0.1")
    log = Path("/tmp") / f"hub-dev-{entry.id}.log"
    with log.open("wb") as handle:
        proc = subprocess.Popen(
            [entry.command, *entry.args],
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(0.2)
    if proc.poll() is not None:
        tail = log.read_text(encoding="utf-8", errors="replace")[-400:]
        raise RuntimeError(f"arrêt immédiat: {tail}")
    _running[entry.id] = proc
    history.append("start", entry.name or entry.id)


def stop(app_id: str) -> None:
    proc = _running.pop(app_id, None)
    if proc is None:
        raise RuntimeError("pas en cours")
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
    history.append("stop", app_id)
