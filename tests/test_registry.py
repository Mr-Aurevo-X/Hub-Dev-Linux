# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest

from core.loopback.registry import AppEntry, Registry


def test_registry_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    reg = Registry.default_empty()
    reg.apps.append(
        AppEntry(id="demo", name="Demo", cwd="/tmp", command="python", args=["-m", "http.server", "8765"])
    )
    reg.save()
    loaded = Registry.load()
    assert len(loaded.apps) == 1
    assert loaded.apps[0].id == "demo"
    assert loaded.apps[0].profile == "dev"


def test_add_app_validates_and_defaults_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    reg = Registry.default_empty()
    app_id = reg.add_app(name="Demo", cwd="/tmp", command="python", args=["-V"])
    assert app_id
    loaded = Registry.load()
    assert len(loaded.apps) == 1
    assert loaded.apps[0].id == app_id
    assert loaded.apps[0].name == "Demo"
    assert loaded.apps[0].command == "python"
    assert loaded.apps[0].args == ["-V"]
    assert loaded.apps[0].profile == "dev"


def test_add_app_rejects_bad_command(tmp_path, monkeypatch):
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    reg = Registry.default_empty()
    with pytest.raises(ValueError):
        reg.add_app(name="Bad", cwd="/tmp", command="echo;rm")


def test_update_app_and_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    reg = Registry.default_empty()
    app_id = reg.add_app(name="Demo", cwd="/tmp", command="python", profile="preview")
    assert Registry.load().apps[0].profile == "preview"
    ok = reg.update_app(app_id, name="Renamed", command="python3", profile="prod", preferred_port=8080)
    assert ok is True
    loaded = Registry.load()
    assert loaded.apps[0].name == "Renamed"
    assert loaded.apps[0].command == "python3"
    assert loaded.apps[0].profile == "prod"
    assert loaded.apps[0].preferred_port == 8080
    assert reg.update_app("missing", name="Nope") is False


def test_clear_scan_wipes_apps_and_roots(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(Registry, "path", classmethod(lambda cls: tmp_path / "apps.json"))
    reg = Registry.default_empty()
    reg.allowed_roots = [str(tmp_path)]
    reg.apps = [AppEntry(id="demo", name="Demo", cwd=str(tmp_path), command="npm", args=["run", "dev"])]
    reg.save()
    count = Registry.load().clear_scan()
    loaded = Registry.load()
    assert count == 1
    assert loaded.apps == []
    assert loaded.allowed_roots == []
