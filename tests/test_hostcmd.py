# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from core.loopback import hostcmd


def test_prefix_empty_outside_flatpak(monkeypatch) -> None:
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    assert hostcmd.in_flatpak() is False
    assert hostcmd.prefix() == []
    assert hostcmd.spawn_argv("npm", ["run", "dev"]) == ["npm", "run", "dev"]


def test_prefix_and_spawn_argv_inside_flatpak(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FLATPAK_ID", "org.mraurevox.HubDev")
    assert hostcmd.prefix() == ["flatpak-spawn", "--host"]
    argv = hostcmd.spawn_argv(
        "npx",
        ["--yes", "pnpm@9.15.0", "run", "dev"],
        cwd=tmp_path,
        env={"PATH": "/host/bin", "HOST": "127.0.0.1", "HOSTNAME": "127.0.0.1"},
    )
    assert argv[:2] == ["flatpak-spawn", "--host"]
    assert f"--directory={tmp_path}" in argv
    assert "--env=PATH=/host/bin" in argv
    assert "--env=HOST=127.0.0.1" in argv
    assert argv[argv.index("--") :] == ["--", "npx", "--yes", "pnpm@9.15.0", "run", "dev"]


def test_which_uses_shutil_outside_flatpak(monkeypatch) -> None:
    monkeypatch.delenv("FLATPAK_ID", raising=False)
    monkeypatch.setattr(hostcmd.shutil, "which", lambda cmd: f"/usr/bin/{cmd}" if cmd == "npm" else None)
    assert hostcmd.which("npm") == "/usr/bin/npm"
    assert hostcmd.which("pnpm") is None


def test_which_caches_flatpak_spawn(monkeypatch) -> None:
    hostcmd._WHICH_HOST.clear()
    monkeypatch.setenv("FLATPAK_ID", "org.mraurevox.HubDev")
    calls = {"n": 0}

    class Fake:
        returncode = 0
        stdout = "/usr/bin/npm\n"

    def fake_run(*_args, **_kwargs):
        calls["n"] += 1
        return Fake()

    monkeypatch.setattr(hostcmd.subprocess, "run", fake_run)
    assert hostcmd.which("npm") == "/usr/bin/npm"
    assert hostcmd.which("npm") == "/usr/bin/npm"
    assert calls["n"] == 1
    hostcmd._WHICH_HOST.clear()


def test_which_does_not_cache_miss(monkeypatch) -> None:
    hostcmd._WHICH_HOST.clear()
    monkeypatch.setenv("FLATPAK_ID", "org.mraurevox.HubDev")
    calls = {"n": 0}

    class Fake:
        returncode = 1
        stdout = ""

    def fake_run(*_args, **_kwargs):
        calls["n"] += 1
        return Fake()

    monkeypatch.setattr(hostcmd.subprocess, "run", fake_run)
    assert hostcmd.which("pnpm") is None
    assert hostcmd.which("pnpm") is None
    assert calls["n"] == 2
    assert "pnpm" not in hostcmd._WHICH_HOST
    hostcmd._WHICH_HOST.clear()


def test_useful_log_tail_drops_npm_notice() -> None:
    raw = "npm notice run mr-x-sentinel@2.0.0 dev\nsh: ligne 1: pnpm: commande introuvable\n"
    assert "npm notice" not in hostcmd.useful_log_tail(raw)
    assert "pnpm" in hostcmd.useful_log_tail(raw)


def test_log_path_uses_data_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path = hostcmd.log_path("sentinel")
    assert path == tmp_path / "hub-dev" / "logs" / "sentinel.log"
    assert path.parent.is_dir()
    assert isinstance(path, Path)
