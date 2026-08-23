# SPDX-License-Identifier: GPL-3.0-or-later
"""GitHub release check + copy-paste install commands."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

FLATPAK_ID = "org.mraurevox.HubDev"
RELEASE_REPO = "Mr-Aurevo-X/Hub-Dev-Linux"
RELEASES_API = f"https://api.github.com/repos/{RELEASE_REPO}/releases"
RELEASES_LATEST_API = f"{RELEASES_API}/latest"
RELEASES_LIST_API = f"{RELEASES_API}?per_page=5"
ASSET_NAME = f"{FLATPAK_ID}.flatpak"
_TRANSIENT_HTTP = frozenset({502, 503, 504})


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


def _http_json(url: str, timeout: float = 12.0) -> object:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Hub Dev"},
    )
    last_error: BaseException | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in _TRANSIENT_HTTP and attempt < 2:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            raise
    if last_error is None:
        raise urllib.error.URLError("GitHub release unavailable")
    raise last_error


def _fetch_latest() -> dict | None:
    last_error: BaseException | None = None
    for url in (RELEASES_LATEST_API, RELEASES_LIST_API):
        try:
            data = _http_json(url)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in _TRANSIENT_HTTP:
                continue
            return None
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return None
        parsed = parse_latest_release(data)
        if parsed is not None:
            return parsed
    _ = last_error
    return None


def parse_latest_release(data: object) -> dict | None:
    if isinstance(data, dict):
        release = data
    elif isinstance(data, list) and data:
        first = data[0]
        if not isinstance(first, dict):
            return None
        release = first
    else:
        return None
    tag = str(release.get("tag_name") or "").lstrip("vV")
    url = ""
    for asset in release.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        if asset.get("name") == ASSET_NAME:
            url = str(asset.get("browser_download_url") or "")
            break
    if not tag or not url:
        return None
    return {"version": tag, "flatpak_url": url, "html_url": str(release.get("html_url") or "")}


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
    url = str(info.get("flatpak_url") or "")
    return (
        f"rm -f {ASSET_NAME}\n"
        f"wget --no-continue -O {ASSET_NAME} \\\n  {url}\n"
        f"flatpak install --user -y --reinstall ./{ASSET_NAME}\n"
        f"flatpak run {FLATPAK_ID}"
    )


def format_update_dialog_body(info: dict) -> str:
    return f"{app_display_name()} {local_version()} → {info.get('version', '?')}"
