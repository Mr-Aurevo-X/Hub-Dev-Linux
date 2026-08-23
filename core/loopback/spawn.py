# SPDX-License-Identifier: GPL-3.0-or-later
"""Process spawn/stop for loopback apps."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

from core.loopback import history, hostcmd, ports, toolchain
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


def _stop_helper(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        if hostcmd.in_flatpak():
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.terminate()
        except OSError:
            return
    try:
        proc.wait(timeout=0.8)
    except subprocess.TimeoutExpired:
        try:
            if hostcmd.in_flatpak():
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            try:
                proc.kill()
            except OSError:
                return


def _kill_port_listeners(port: int) -> None:
    for force in (False, True):
        pids = ports.pids_on_port(port)
        if not pids:
            return
        for pid in pids:
            try:
                ports.kill_pid(pid, force=force)
            except OSError:
                continue
        if not force:
            time.sleep(0.15)


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
    env = toolchain.prepare_env(os.environ.copy(), cwd=cwd)
    if entry.force_loopback:
        env.setdefault("HOST", "127.0.0.1")
        env.setdefault("HOSTNAME", "127.0.0.1")
    log = hostcmd.log_path(entry.id)
    argv = hostcmd.spawn_argv(entry.command, entry.args, cwd=cwd, env=env)
    with log.open("wb") as handle:
        proc = subprocess.Popen(
            argv,
            cwd=None if hostcmd.in_flatpak() else cwd,
            env=None if hostcmd.in_flatpak() else env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    time.sleep(0.2)
    if proc.poll() is not None:
        tail = hostcmd.useful_log_tail(log.read_text(encoding="utf-8", errors="replace"))
        raise RuntimeError(f"arrêt immédiat: {tail}")
    _running[entry.id] = proc
    history.append("start", entry.name or entry.id)


def stop(app_id: str) -> None:
    entry = next((app for app in Registry.load().apps if app.id == app_id), None)
    proc = _running.pop(app_id, None)
    if proc is not None:
        _stop_helper(proc)
    port = entry.preferred_port if entry is not None else None
    if port:
        _kill_port_listeners(int(port))
    elif proc is None:
        raise RuntimeError("pas en cours")
    history.append("stop", (entry.name if entry is not None else None) or app_id)
