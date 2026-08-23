# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

from core import updater


def _dev_release_item(version: str) -> dict:
    return {
        "tag_name": f"v{version}",
        "html_url": f"https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/tag/v{version}",
        "assets": [
            {
                "name": "org.mraurevox.HubDev.flatpak",
                "browser_download_url": (
                    "https://github.com/Mr-Aurevo-X/Hub-Dev-Linux/releases/download/"
                    f"v{version}/org.mraurevox.HubDev.flatpak"
                ),
            }
        ],
    }


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


def test_parse_latest_release_accepts_github_latest_object() -> None:
    info = updater.parse_latest_release(_dev_release_item("1.2.8"))
    assert info is not None
    assert info["version"] == "1.2.8"
    assert info["flatpak_url"].endswith("org.mraurevox.HubDev.flatpak")


def test_fetch_latest_uses_latest_endpoint(monkeypatch) -> None:
    calls: list[str] = []
    payload = json.dumps(_dev_release_item("1.2.8")).encode()

    class FakeResp:
        def read(self) -> bytes:
            return payload

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_a: object) -> bool:
            return False

    def fake_urlopen(req: urllib.request.Request, context=None, timeout: float = 12) -> FakeResp:
        calls.append(req.full_url)
        return FakeResp()

    monkeypatch.setattr(updater.urllib.request, "urlopen", fake_urlopen)
    info = updater._fetch_latest()
    assert info is not None
    assert info["version"] == "1.2.8"
    assert calls[0] == updater.RELEASES_LATEST_API


def test_fetch_latest_falls_back_after_504(monkeypatch) -> None:
    calls: list[str] = []
    payload = json.dumps([_dev_release_item("1.2.8")]).encode()

    class FakeResp:
        def read(self) -> bytes:
            return payload

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *_a: object) -> bool:
            return False

    def fake_urlopen(req: urllib.request.Request, context=None, timeout: float = 12) -> FakeResp:
        calls.append(req.full_url)
        if req.full_url.endswith("/latest"):
            raise urllib.error.HTTPError(
                req.full_url, 504, "Gateway Time-out", hdrs=None, fp=io.BytesIO()
            )
        return FakeResp()

    monkeypatch.setattr(updater.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(updater.time, "sleep", lambda _s: None)
    info = updater._fetch_latest()
    assert info is not None
    assert info["version"] == "1.2.8"
    assert calls[0] == updater.RELEASES_LATEST_API
    assert updater.RELEASES_LIST_API in calls
