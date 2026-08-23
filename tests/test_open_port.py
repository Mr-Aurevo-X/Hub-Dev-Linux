# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from core.loopback.ports import PortRow, guess_preferred_port, resolve_open_port
from core.loopback.registry import AppEntry


def test_guess_preferred_port_vite_and_next(tmp_path) -> None:
    vite = tmp_path / "vite-app"
    vite.mkdir()
    (vite / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    assert guess_preferred_port(vite) == 5173
    nxt = tmp_path / "next-app"
    nxt.mkdir()
    (nxt / "next.config.mjs").write_text("export default {}\n", encoding="utf-8")
    assert guess_preferred_port(nxt) == 3000


def test_guess_preferred_port_from_script_text(tmp_path) -> None:
    root = tmp_path / "lounge"
    root.mkdir()
    assert guess_preferred_port(root, scripts={"dev:local": "node scripts/dev.mjs --port 4173"}) == 4173


def test_resolve_open_port_prefers_declared() -> None:
    app = AppEntry(id="a", name="a", cwd="/tmp", command="pnpm", preferred_port=5173)
    assert resolve_open_port(app, is_running=False, rows=[]) == 5173


def test_resolve_open_port_matches_pid_then_cwd(tmp_path) -> None:
    app = AppEntry(id="game", name="game", cwd=str(tmp_path), command="pnpm")
    rows = [PortRow(port=5173, pid=4242, process_name="node", addr="127.0.0.1", is_loopback=True)]
    assert resolve_open_port(app, is_running=True, pid=4242, rows=rows) == 5173


def test_resolve_open_port_running_fallback_node() -> None:
    app = AppEntry(id="x", name="x", cwd="/nope", command="pnpm", args=["run", "dev:local"])
    assert resolve_open_port(app, is_running=True, rows=[]) == 5173


def test_can_open_when_running_or_guessed(tmp_path) -> None:
    from core.loopback.ports import can_open

    (tmp_path / "vite.config.js").write_text("", encoding="utf-8")
    stopped = AppEntry(id="s", name="s", cwd=str(tmp_path), command="pnpm")
    running = AppEntry(id="r", name="r", cwd="/missing", command="npm")
    bare = AppEntry(id="b", name="b", cwd="/missing", command="python")
    assert can_open(stopped, is_running=False, rows=[]) is True
    assert can_open(running, is_running=True, rows=[]) is True
    assert can_open(bare, is_running=False, rows=[]) is False
