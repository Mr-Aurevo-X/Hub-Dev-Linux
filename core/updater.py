# SPDX-License-Identifier: GPL-3.0-or-later
"""GitHub release check + copy-paste install commands."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

FLATPAK_ID = "org.mraurevox.HubDev"
RELEASE_REPO = "Mr-Aurevo-X/Hub-Dev"
RELEASES_API = f"https://api.github.com/repos/{RELEASE_REPO}/releases"
ASSET_NAME = f"{FLATPAK_ID}.flatpak"


def local_version() -> str:
    for candidate in (
        Path(__file__).resolve().parents[1] / "VERSION",
        Path(f"/app/share/hub-dev/VERSION"),
    ):
        try:
            if candidate.is_file():
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text
        except OSError:
            continue
    return "1.0.0"


def app_display_name() -> str:
    return "Hub Dev"


def _fetch_latest() -> dict | None:
    req = urllib.request.Request(
        RELEASES_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Hub Dev"},
    )
    try:
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    if not isinstance(data, list) or not data:
        return None
    release = data[0]
    tag = str(release.get("tag_name") or "").lstrip("vV")
    url = ""
    for asset in release.get("assets") or []:
        if asset.get("name") == ASSET_NAME:
            url = str(asset.get("browser_download_url") or "")
            break
    if not url:
        return None
    return {"version": tag, "flatpak_url": url, "html_url": release.get("html_url", "")}


def check_for_update(*, raise_on_error: bool = False) -> dict | None:
    info = _fetch_latest()
    if info is None:
        if raise_on_error:
            raise RuntimeError("GitHub release unavailable")
        return None
    remote = str(info["version"])
    local = local_version()
    if _semver_gt(remote, local):
        return info
    return None


def _semver_gt(a: str, b: str) -> bool:
    def parts(v: str) -> list[int]:
        return [int(x) for x in v.split(".")[:3] if x.isdigit()]

    pa, pb = parts(a), parts(b)
    for i in range(3):
        if pa[i] > pb[i]:
            return True
        if pa[i] < pb[i]:
            return False
    return False


def format_update_dialog_commands(info: dict) -> str:
    url = info.get("flatpak_url") or ""
    return f"flatpak install --user -y {url}"


def format_update_dialog_body(info: dict) -> str:
    return (
        f"{app_display_name()} — local {local_version()} → {info.get('version', '?')}\n"
        f"{info.get('html_url', '')}"
    )
