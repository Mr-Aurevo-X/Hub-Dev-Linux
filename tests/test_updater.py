# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from core import updater


def test_parse_latest_release_requires_flatpak_asset() -> None:
    assert updater.parse_latest_release([]) is None
    assert (
        updater.parse_latest_release(
            [{"tag_name": "v1.2.0", "html_url": "https://example.test/r", "assets": []}]
        )
        is None
    )
    info = updater.parse_latest_release(
        [
            {
                "tag_name": "v1.2.0",
                "html_url": "https://example.test/r",
                "assets": [
                    {
                        "name": "org.mraurevox.HubDev.flatpak",
                        "browser_download_url": "https://example.test/org.mraurevox.HubDev.flatpak",
                    }
                ],
            }
        ]
    )
    assert info is not None
    assert info["version"] == "1.2.0"
    assert info["flatpak_url"].endswith("org.mraurevox.HubDev.flatpak")
    commands = updater.format_update_dialog_commands(info)
    assert "rm -f org.mraurevox.HubDev.flatpak" in commands
    assert "wget --no-continue -O org.mraurevox.HubDev.flatpak" in commands
    assert "https://example.test/org.mraurevox.HubDev.flatpak" in commands
    assert "flatpak install --user -y --reinstall ./org.mraurevox.HubDev.flatpak" in commands
    body = updater.format_update_dialog_body(info)
    assert "http" not in body
    assert "Lounge" not in body
    assert "1.2.0" in body


def test_check_for_update_none_without_newer_asset(monkeypatch) -> None:
    monkeypatch.setattr(updater, "local_version", lambda: "1.2.0")
    monkeypatch.setattr(updater, "_fetch_latest", lambda: None)
    assert updater.check_for_update() is None
    monkeypatch.setattr(
        updater,
        "_fetch_latest",
        lambda: {
            "version": "1.2.0",
            "flatpak_url": "https://example.test/org.mraurevox.HubDev.flatpak",
            "html_url": "https://example.test/r",
        },
    )
    assert updater.check_for_update() is None
    monkeypatch.setattr(
        updater,
        "_fetch_latest",
        lambda: {
            "version": "1.2.1",
            "flatpak_url": "https://example.test/org.mraurevox.HubDev.flatpak",
            "html_url": "https://example.test/r",
        },
    )
    found = updater.check_for_update()
    assert found is not None
    assert found["version"] == "1.2.1"
