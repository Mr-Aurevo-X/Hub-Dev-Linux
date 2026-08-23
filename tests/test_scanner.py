# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

from core.loopback import scanner, toolchain
from core.loopback.registry import AppEntry, Registry


def _no_pnpm_which(cmd: str, path: str | None = None) -> str | None:
    if path:
        return None
    if cmd in {"npm", "npx"}:
        return f"/usr/bin/{cmd}"
    return None


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
    assert "battler-x" not in names
    root = next(item for item in hits if item.cwd == str(tmp_path))
    assert root.command in {"pnpm", "npm"}
    assert root.args == ["run", "dev:local"]


def test_scan_skips_test_fixtures(tmp_path) -> None:
    fixture = tmp_path / "tests" / "fixtures" / "vite-app"
    _write_pkg(fixture, {"dev": "vite --port 3001"})
    (fixture / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    assert scanner.scan_root(tmp_path) == []


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


def test_scan_skips_lint_only_package(tmp_path) -> None:
    _write_pkg(tmp_path, {"lint": "eslint .", "test": "vitest"})
    assert scanner.scan_root(tmp_path) == []


def test_scan_finds_preview_and_reads_port(tmp_path) -> None:
    _write_pkg(tmp_path, {"preview": "vite preview --port 4173"})
    hits = scanner.scan_root(tmp_path)
    assert len(hits) == 1
    assert hits[0].args == ["run", "preview"]
    assert hits[0].preferred_port == 4173


def test_scan_finds_flask_and_fastapi(tmp_path) -> None:
    flask_dir = tmp_path / "flask-app"
    flask_dir.mkdir()
    (flask_dir / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n", encoding="utf-8")
    api = tmp_path / "api"
    api.mkdir()
    (api / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    hits = {item.name: item for item in scanner.scan_root(tmp_path)}
    assert hits["flask-app"].command in {"python", "python3"}
    assert hits["flask-app"].preferred_port == 5000
    assert "flask" in " ".join(hits["flask-app"].args).lower() or hits["flask-app"].args[0] == "-m"
    assert hits["api"].preferred_port == 8000
    assert "uvicorn" in " ".join([hits["api"].command, *hits["api"].args])


def test_scan_prefers_node_hub_over_compose(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(scanner.shutil, "which", _no_pnpm_which)
    monkeypatch.setattr(toolchain.shutil, "which", _no_pnpm_which)
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "mr-x-sentinel",
                "packageManager": "pnpm@9.15.0",
                "scripts": {"dev": "pnpm run docker:up && pnpm --filter @sentinel/dashboard dev"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        "services:\n  db:\n    ports:\n      - '127.0.0.1:5433:5432'\n",
        encoding="utf-8",
    )
    dash = tmp_path / "apps" / "dashboard"
    _write_pkg(dash, {"dev": "next dev -p 3000"})
    hits = scanner.scan_root(tmp_path)
    assert len(hits) == 1
    assert hits[0].command == "npx"
    assert hits[0].preferred_port == 3000


def test_scan_finds_artisan_and_compose(tmp_path) -> None:
    artisan = tmp_path / "laravel"
    artisan.mkdir()
    (artisan / "artisan").write_text("#!/usr/bin/env php\n", encoding="utf-8")
    compose = tmp_path / "stack"
    compose.mkdir()
    (compose / "compose.yaml").write_text(
        "services:\n  web:\n    ports:\n      - '127.0.0.1:8088:80'\n",
        encoding="utf-8",
    )
    hits = {item.name: item for item in scanner.scan_root(tmp_path)}
    assert hits["laravel"].command == "php"
    assert hits["laravel"].args[:2] == ["artisan", "serve"]
    assert hits["laravel"].preferred_port == 8000
    assert hits["stack"].preferred_port == 8088
    assert hits["stack"].command in {"docker", "docker-compose"}


def test_is_launchable_requires_command_and_port(tmp_path, monkeypatch) -> None:
    from core.loopback.scanner import ProposedApp

    app = ProposedApp("demo", str(tmp_path), "pnpm", ["run", "dev"], 5173)
    monkeypatch.setattr(scanner.shutil, "which", lambda cmd: None)
    assert scanner.is_launchable(app) is False
    monkeypatch.setattr(scanner.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    assert scanner.is_launchable(app) is True
    no_port = ProposedApp("demo", str(tmp_path), "pnpm", ["run", "dev"], None)
    assert scanner.is_launchable(no_port) is False


def test_scan_reads_port_from_dev_local_script(tmp_path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "dev-local.mjs").write_text(
        "const port = Number(process.env.PORT || 4180)\n",
        encoding="utf-8",
    )
    _write_pkg(tmp_path, {"dev:local": "node scripts/dev-local.mjs"}, pnpm=True)
    (tmp_path / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    hits = scanner.scan_root(tmp_path)
    assert len(hits) == 1
    assert hits[0].args == ["run", "dev:local"]
    assert hits[0].preferred_port == 4180
    assert hits[0].command in {"pnpm", "npm", "yarn", "bun"}


def test_scan_skips_workspace_games_when_hub_exists(tmp_path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "dev-local.mjs").write_text(
        "const port = Number(process.env.PORT || 4180)\n",
        encoding="utf-8",
    )
    _write_pkg(tmp_path, {"dev:local": "node scripts/dev-local.mjs"}, pnpm=True)
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'games/*'\n", encoding="utf-8")
    game = tmp_path / "games" / "battler-x"
    _write_pkg(game, {"dev": "vite"}, pnpm=True)
    (game / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    hits = scanner.scan_root(tmp_path)
    names = {item.name for item in hits}
    assert tmp_path.name in names
    assert "battler-x" not in names
    assert hits[0].preferred_port == 4180


def test_scan_skips_games_when_parent_has_dev_local_without_workspace(tmp_path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "dev-local.mjs").write_text(
        "const port = Number(process.env.PORT || 4180)\n",
        encoding="utf-8",
    )
    _write_pkg(tmp_path, {"dev:local": "node scripts/dev-local.mjs"})
    game = tmp_path / "games" / "battler-x"
    _write_pkg(game, {"dev": "vite"})
    (game / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    hits = scanner.scan_root(tmp_path)
    assert {item.name for item in hits} == {tmp_path.name}
    assert hits[0].preferred_port == 4180


def test_scan_apps_replaces_stale_games_under_root(tmp_path, monkeypatch) -> None:
    from core.loopback.registry import AppEntry, Registry

    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    lounge = tmp_path / "lounge"
    keep_dir = tmp_path / "keep-app"
    (lounge / "scripts").mkdir(parents=True)
    (lounge / "scripts" / "dev-local.mjs").write_text(
        "const port = Number(process.env.PORT || 4180)\n",
        encoding="utf-8",
    )
    _write_pkg(lounge, {"dev:local": "node scripts/dev-local.mjs"})
    game = lounge / "games" / "battler-x"
    _write_pkg(game, {"dev": "vite"})
    (game / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    keep_dir.mkdir()
    reg = Registry.default_empty()
    reg.allowed_roots = [str(lounge)]
    reg.apps = [
        AppEntry(id="hub", name="old-hub", cwd=str(lounge), command="npm", args=["run", "dev"], preferred_port=5173),
        AppEntry(id="battler-x", name="battler-x", cwd=str(game), command="npm", args=["run", "dev"], preferred_port=5173),
        AppEntry(id="keep", name="keep", cwd=str(keep_dir), command="npm", args=["run", "dev"]),
    ]
    reg.save()
    loaded = Registry.load()
    loaded.scan_apps()
    apps = Registry.load().apps
    names = {app.name for app in apps}
    assert "battler-x" not in names
    hub = next(app for app in apps if Path(app.cwd).resolve() == lounge.resolve())
    assert hub.args == ["run", "dev:local"]
    assert hub.preferred_port == 4180
    assert "keep" in names


def test_scan_uses_npx_when_scripts_need_pnpm(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(scanner.shutil, "which", _no_pnpm_which)
    monkeypatch.setattr(toolchain.shutil, "which", _no_pnpm_which)
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "mr-x-sentinel",
                "packageManager": "pnpm@9.15.0",
                "scripts": {
                    "dev": 'pnpm run docker:up && pnpm --filter @sentinel/dashboard dev',
                    "docker:up": "docker compose up -d",
                },
            }
        ),
        encoding="utf-8",
    )
    dash = tmp_path / "apps" / "dashboard"
    _write_pkg(dash, {"dev": "next dev -p 3000"})
    hits = scanner.scan_root(tmp_path)
    assert len(hits) == 1
    assert hits[0].command == "npx"
    assert hits[0].args[:3] == ["--yes", "pnpm@9.15.0", "run"]
    assert hits[0].args[-1] == "dev"
    assert hits[0].preferred_port == 3000
    assert "dashboard" not in {item.name for item in hits}


def test_scan_apps_refreshes_existing_outside_roots(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    monkeypatch.setattr(scanner.shutil, "which", _no_pnpm_which)
    monkeypatch.setattr(toolchain.shutil, "which", _no_pnpm_which)
    lounge = tmp_path / "lounge"
    (lounge / "scripts").mkdir(parents=True)
    (lounge / "scripts" / "dev-local.mjs").write_text(
        "const port = Number(process.env.PORT || 4180)\n",
        encoding="utf-8",
    )
    _write_pkg(lounge, {"dev:local": "node scripts/dev-local.mjs"})
    sentinel = tmp_path / "Discord Bot" / "Sentinel"
    dash = sentinel / "apps" / "dashboard"
    sentinel.mkdir(parents=True)
    (sentinel / "pnpm-workspace.yaml").write_text("packages:\n  - 'apps/*'\n", encoding="utf-8")
    (sentinel / "package.json").write_text(
        json.dumps(
            {
                "name": "mr-x-sentinel",
                "packageManager": "pnpm@9.15.0",
                "scripts": {
                    "dev": "pnpm run docker:up && pnpm --filter @sentinel/dashboard dev",
                    "docker:up": "docker compose up -d",
                },
            }
        ),
        encoding="utf-8",
    )
    _write_pkg(dash, {"dev": "next dev -p 3000"})
    reg = Registry.default_empty()
    reg.allowed_roots = [str(lounge)]
    reg.apps = [
        AppEntry(
            id="sentinel",
            name="Sentinel",
            cwd=str(sentinel),
            command="npm",
            args=["run", "dev"],
            preferred_port=None,
        ),
        AppEntry(
            id="dashboard",
            name="dashboard",
            cwd=str(dash),
            command="npm",
            args=["run", "dev"],
            preferred_port=3000,
        ),
    ]
    reg.save()
    Registry.load().scan_apps()
    apps = Registry.load().apps
    names = {app.name for app in apps}
    assert "dashboard" not in names
    sent = next(app for app in apps if Path(app.cwd).resolve() == sentinel.resolve())
    assert sent.command == "npx"
    assert sent.args[:3] == ["--yes", "pnpm@9.15.0", "run"]
    assert sent.preferred_port == 3000


def test_scan_disk_only_keeps_launchable(tmp_path, monkeypatch) -> None:
    _write_pkg(tmp_path / "ok", {"dev": "vite"}, pnpm=True)
    (tmp_path / "ok" / "vite.config.ts").write_text("export default {}\n", encoding="utf-8")
    _write_pkg(tmp_path / "lint-only", {"lint": "eslint ."})
    monkeypatch.setattr(scanner.shutil, "which", lambda cmd: f"/usr/bin/{cmd}" if cmd in {"pnpm", "npm"} else None)
    hits = scanner.scan_disk(roots=[tmp_path], require_launchable=True)
    names = {item.name for item in hits}
    assert "ok" in names
    assert "lint-only" not in names
    assert all(item.preferred_port for item in hits)
    assert all(item.command and item.args for item in hits)
