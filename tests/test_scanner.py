# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json

from core.loopback import scanner
from core.loopback.registry import Registry


def _write_pkg(path, scripts: dict[str, str], *, pnpm: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "package.json").write_text(
        json.dumps({"name": path.name, "scripts": scripts}),
        encoding="utf-8",
    )
    if pnpm:
        (path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")


def test_scan_finds_dev_local_and_nested_game(tmp_path) -> None:
    _write_pkg(tmp_path, {"dev:local": "node scripts/dev-local.mjs"}, pnpm=True)
    game = tmp_path / "games" / "battler-x"
    _write_pkg(game, {"dev": "vite"}, pnpm=True)
    hits = scanner.scan_root(tmp_path)
    names = {item.name for item in hits}
    assert tmp_path.name in names
    assert "battler-x" in names
    root = next(item for item in hits if item.cwd == str(tmp_path))
    assert root.command == "pnpm"
    assert root.args == ["run", "dev:local"]


def test_scan_skips_node_modules(tmp_path) -> None:
    nested = tmp_path / "node_modules" / "vite"
    _write_pkg(nested, {"dev": "echo"})
    assert scanner.scan_root(tmp_path) == []


def test_normalize_root_resolves_symlink(tmp_path) -> None:
    real = tmp_path / "Users" / "proj"
    real.mkdir(parents=True)
    alias = tmp_path / "Documents and Settings"
    alias.symlink_to(tmp_path / "Users")
    linked = alias / "proj"
    assert scanner.normalize_root(linked) == real.resolve()


def test_add_allowed_root_dedupes_and_rejects_skip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    real = tmp_path / "Users" / "proj"
    real.mkdir(parents=True)
    alias = tmp_path / "Documents and Settings"
    alias.symlink_to(tmp_path / "Users")
    reg = Registry.default_empty()
    reg.allowed_roots = []
    assert reg.add_allowed_root(str(alias / "proj")) is True
    assert reg.add_allowed_root(str(real)) is False
    assert len(reg.allowed_roots) == 1
    junk = tmp_path / "node_modules"
    junk.mkdir()
    assert reg.add_allowed_root(str(junk)) is False


def test_empty_linked_roots(tmp_path) -> None:
    root = tmp_path / "lounge"
    root.mkdir()
    from core.loopback.registry import AppEntry

    apps = [AppEntry(id="other", name="other", cwd=str(tmp_path / "elsewhere"), command="npm")]
    assert scanner.empty_linked_roots([str(root)], apps) == [str(root.resolve())]


def test_apps_grouped_by_root(tmp_path) -> None:
    root = tmp_path / "lounge"
    game = root / "games" / "factory-x"
    game.mkdir(parents=True)
    from core.loopback.registry import AppEntry

    apps = [
        AppEntry(id="factory-x", name="factory-x", cwd=str(game), command="pnpm"),
        AppEntry(id="other", name="other", cwd=str(tmp_path / "elsewhere"), command="npm"),
    ]
    groups = scanner.apps_grouped_by_root([str(root)], apps)
    assert groups[0][0] == str(root.resolve())
    assert [a.id for a in groups[0][1]] == ["factory-x"]
    assert groups[1][1][0].id == "other"
