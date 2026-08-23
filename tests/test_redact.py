# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from core import redact
from core.redact import display_detail, display_path


def test_display_path_hides_home_and_media_users(monkeypatch) -> None:
    monkeypatch.setattr(redact.Path, "home", staticmethod(lambda: Path("/home/alice")))
    assert display_path("/home/alice/Documents/proj") == "~/Documents/proj"
    hidden = display_path("/run/media/alice/DISK/Users/bob/Documents/app")
    assert "alice" not in hidden
    assert "bob" not in hidden
    assert hidden.startswith("/run/media/…/")
    assert "/Users/…" in hidden


def test_display_detail_redacts_only_paths() -> None:
    assert display_detail("scan-disk") == "scan-disk"
    assert display_detail("3") == "3"
    assert "alice" not in display_detail("/home/alice/src")
