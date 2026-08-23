# SPDX-License-Identifier: GPL-3.0-or-later
"""Run loopback tools on the host when Hub Dev is inside Flatpak."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from core.paths import data_dir

_FORWARDED_ENV = ("PATH", "HOST", "HOSTNAME")


def in_flatpak() -> bool:
    return bool(os.environ.get("FLATPAK_ID"))


def prefix() -> list[str]:
    return ["flatpak-spawn", "--host"] if in_flatpak() else []


def which(command: str) -> str | None:
    if not in_flatpak():
        return shutil.which(command)
    try:
        out = subprocess.run(
            ["flatpak-spawn", "--host", "--", "which", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    line = (out.stdout or "").strip().splitlines()
    if out.returncode != 0 or not line:
        return None
    return line[0]


def spawn_argv(
    command: str,
    args: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> list[str]:
    if not in_flatpak():
        return [command, *args]
    line = ["flatpak-spawn", "--host"]
    if cwd is not None:
        line.append(f"--directory={cwd}")
    if env:
        for key in _FORWARDED_ENV:
            value = env.get(key)
            if value:
                line.append(f"--env={key}={value}")
    line.append("--")
    line.extend([command, *args])
    return line


def run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
    argv = [*prefix(), "--", *args] if prefix() else list(args)
    return subprocess.run(argv, **kwargs)  # type: ignore[call-overload]


def log_path(app_id: str) -> Path:
    directory = data_dir() / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{app_id}.log"


def useful_log_tail(text: str, limit: int = 400) -> str:
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lower().startswith("npm notice")
    ]
    blob = "\n".join(lines) if lines else text
    return blob[-limit:].strip()
