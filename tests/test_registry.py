# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

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
