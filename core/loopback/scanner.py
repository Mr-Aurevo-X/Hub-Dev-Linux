# SPDX-License-Identifier: GPL-3.0-or-later
"""Project scanner — detect launchable localhost servers."""

from __future__ import annotations

import json
import os
import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.loopback.ports import guess_preferred_port

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "dist-site",
    "target",
    "venv",
    ".venv",
    ".next",
    ".turbo",
    ".vercel",
    ".cursor",
    "graphify-out",
    "__pycache__",
    "coverage",
    ".cache",
    ".npm",
    ".cargo",
    ".rustup",
    ".Trash",
    "site-packages",
    "vendor",
    "snap",
    ".local",
    "timeshift",
    "lost+found",
}
DEV_SCRIPT_PRIORITY = (
    "dev:local:all",
    "dev:local",
    "dev",
    "start:dev",
    "serve",
    "preview",
    "start",
    "storybook",
    "dev:server",
    "web",
)
_SERVER_HINTS = (
    "vite",
    "next",
    "nuxt",
    "remix",
    "astro",
    "webpack-dev-server",
    "webpack serve",
    "react-scripts start",
    "ng serve",
    "nest start",
    "http-server",
    "live-server",
    "storybook",
    "nodemon",
    "tsx watch",
    "expo",
    "docusaurus",
    "gatsby",
    "hugo server",
    "jekyll serve",
    "parcel",
    "snowpack",
)
_NON_SERVER_KEYS = {"lint", "test", "build", "typecheck", "format", "deploy", "clean", "tsc"}
_COMPOSE_FILES = ("compose.yaml", "compose.yml", "docker-compose.yml", "docker-compose.yaml")
_COMPOSE_PORT = re.compile(r"""['"]?(?:127\.0\.0\.1:|\[::1\]:)?(\d{2,5}):\d+""")
_MAKE_TARGET = re.compile(r"^(dev|serve|start)\s*:", re.M)
_VIRTUAL_FS = {
    "proc",
    "sysfs",
    "devtmpfs",
    "tmpfs",
    "cgroup",
    "cgroup2",
    "overlay",
    "squashfs",
    "autofs",
    "debugfs",
    "tracefs",
    "securityfs",
    "pstore",
    "efivarfs",
    "fusectl",
    "bpf",
}
_SKIP_MOUNT = {"/", "/boot", "/boot/efi", "/boot/efi2"}
_DISK_MAX_DEPTH = 12
StopCheck = Callable[[], bool]


@dataclass
class ProposedApp:
    name: str
    cwd: str
    command: str
    args: list[str]
    preferred_port: int | None = None


def normalize_root(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"not a directory: {resolved}")
    if resolved.name in SKIP_DIRS:
        raise ValueError(f"skipped directory: {resolved.name}")
    return resolved


def empty_linked_roots(roots: list[str], apps: list[Any]) -> list[str]:
    return [root for root, group in apps_grouped_by_root(roots, apps) if root and not group]


def apps_grouped_by_root(
    roots: list[str],
    apps: list[Any],
) -> list[tuple[str, list[Any]]]:
    used: set[str] = set()
    groups: list[tuple[str, list[Any]]] = []
    for root in roots:
        try:
            resolved = Path(root).expanduser().resolve()
        except OSError:
            resolved = Path(root)
        group: list[Any] = []
        for app in apps:
            if app.id in used:
                continue
            try:
                cwd = Path(app.cwd).expanduser().resolve()
            except OSError:
                continue
            if cwd == resolved or resolved in cwd.parents:
                group.append(app)
                used.add(app.id)
        groups.append((str(resolved), group))
    leftover = [app for app in apps if app.id not in used]
    if leftover:
        groups.append(("", leftover))
    return groups


def is_launchable(proposal: ProposedApp) -> bool:
    if proposal.preferred_port is None:
        return False
    cwd = Path(proposal.cwd)
    if not cwd.is_dir():
        return False
    command = proposal.command
    direct = Path(command)
    if direct.is_file() and os.access(direct, os.X_OK):
        return True
    relative = cwd / command
    if relative.is_file() and os.access(relative, os.X_OK):
        return True
    return shutil.which(command) is not None


def scan_root(
    root: Path,
    max_depth: int = 8,
    *,
    should_stop: StopCheck | None = None,
) -> list[ProposedApp]:
    proposals: list[ProposedApp] = []
    try:
        start = normalize_root(root)
    except ValueError:
        start = Path(root)
        if not start.is_dir():
            return []
    _scan_dir(start, 0, max_depth, proposals, should_stop)
    return proposals


def disk_scan_roots() -> list[Path]:
    candidates = [
        Path.home(),
        Path("/home"),
        Path("/opt"),
        Path("/srv"),
        Path("/var/www"),
        Path("/mnt"),
        Path("/media"),
    ]
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace")
    except OSError:
        mounts = ""
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        dest, fstype = parts[1], parts[2]
        if fstype in _VIRTUAL_FS or dest in _SKIP_MOUNT:
            continue
        candidates.append(Path(dest))
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in candidates:
        try:
            resolved = raw.expanduser().resolve()
        except OSError:
            continue
        if not resolved.is_dir() or resolved.name in SKIP_DIRS:
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        roots.append(resolved)
    return roots


def scan_disk(
    *,
    roots: list[Path] | None = None,
    require_launchable: bool = True,
    max_depth: int = _DISK_MAX_DEPTH,
    should_stop: StopCheck | None = None,
) -> list[ProposedApp]:
    start_roots = list(roots) if roots is not None else disk_scan_roots()
    seen: set[tuple[str, str]] = set()
    out: list[ProposedApp] = []
    for root in start_roots:
        if should_stop and should_stop():
            break
        for proposal in scan_root(root, max_depth=max_depth, should_stop=should_stop):
            key = (proposal.cwd, proposal.command)
            if key in seen:
                continue
            if require_launchable and not is_launchable(proposal):
                continue
            if proposal.preferred_port is None:
                continue
            if not proposal.command or not proposal.args:
                continue
            seen.add(key)
            out.append(proposal)
    return out


def detect_in_dir(path: Path) -> list[ProposedApp]:
    found: list[ProposedApp] = []
    for detector in (_detect_node, _detect_python, _detect_php, _detect_compose, _detect_rails, _detect_make):
        proposal = detector(path)
        if proposal is not None:
            found.append(proposal)
    return found


def _scan_dir(
    path: Path,
    depth: int,
    max_depth: int,
    out: list[ProposedApp],
    should_stop: StopCheck | None,
) -> None:
    if should_stop and should_stop():
        return
    if depth > max_depth:
        return
    out.extend(detect_in_dir(path))
    if depth == max_depth:
        return
    try:
        children = list(path.iterdir())
    except OSError:
        return
    for child in children:
        if should_stop and should_stop():
            return
        try:
            if child.is_symlink() or not child.is_dir() or child.name in SKIP_DIRS:
                continue
        except OSError:
            continue
        _scan_dir(child, depth + 1, max_depth, out, should_stop)


def _read_head(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _package_manager(path: Path, data: dict[object, object]) -> str:
    manager = str(data.get("packageManager") or "")
    if manager.startswith("bun") or (path / "bun.lockb").is_file() or (path / "bun.lock").is_file():
        return "bun"
    if manager.startswith("pnpm") or (path / "pnpm-lock.yaml").is_file() or (path / "pnpm-workspace.yaml").is_file():
        return "pnpm"
    if manager.startswith("yarn") or (path / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _script_is_server(name: str, body: str) -> bool:
    key = name.lower()
    base = key.split(":", 1)[0]
    if key in _NON_SERVER_KEYS or (base in _NON_SERVER_KEYS and base not in {"start", "dev"}):
        return False
    blob = body.lower()
    if any(hint in blob for hint in _SERVER_HINTS):
        return True
    if "serve " in blob or blob.strip() == "serve":
        return True
    return base in {"dev", "start", "serve", "preview", "storybook", "web"} and "eslint" not in blob


def _pick_script(scripts: dict[object, object]) -> str | None:
    typed = {str(name): str(value) for name, value in scripts.items()}
    for key in DEV_SCRIPT_PRIORITY:
        if key in typed and _script_is_server(key, typed[key]):
            return key
    for key, value in typed.items():
        if _script_is_server(key, value):
            return key
    return None


def _detect_node(path: Path) -> ProposedApp | None:
    pkg = path / "package.json"
    if not pkg.is_file():
        return None
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts") or {}
    if not isinstance(scripts, dict):
        return None
    picked = _pick_script(scripts)
    if picked is None:
        return None
    scripts_text = {str(name): str(value) for name, value in scripts.items()}
    return ProposedApp(
        path.name,
        str(path),
        _package_manager(path, data),
        ["run", picked],
        guess_preferred_port(path, scripts_text),
    )


def _python_cmd(path: Path) -> str:
    for rel in (".venv/bin/python", "venv/bin/python"):
        candidate = path / rel
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    if shutil.which("python3"):
        return "python3"
    if shutil.which("python"):
        return "python"
    return "python3"


def _detect_python(path: Path) -> ProposedApp | None:
    command = _python_cmd(path)
    if (path / "manage.py").is_file():
        return ProposedApp(path.name, str(path), command, ["manage.py", "runserver", "127.0.0.1:8000"], 8000)
    for name in ("app.py", "main.py", "wsgi.py"):
        text = _read_head(path / name)
        if not text:
            continue
        module = name[:-3]
        lowered = text.lower()
        if "fastapi" in lowered:
            return ProposedApp(
                path.name,
                str(path),
                command,
                ["-m", "uvicorn", f"{module}:app", "--host", "127.0.0.1", "--port", "8000"],
                8000,
            )
        if "flask" in lowered:
            return ProposedApp(
                path.name,
                str(path),
                command,
                ["-m", "flask", "--app", name, "run", "--host=127.0.0.1", "--port=5000"],
                5000,
            )
        if "streamlit" in lowered:
            return ProposedApp(
                path.name,
                str(path),
                command,
                ["-m", "streamlit", "run", name, "--server.address", "127.0.0.1"],
                8501,
            )
    return None


def _detect_php(path: Path) -> ProposedApp | None:
    if not (path / "artisan").is_file():
        return None
    return ProposedApp(path.name, str(path), "php", ["artisan", "serve", "--host=127.0.0.1", "--port=8000"], 8000)


def _detect_compose(path: Path) -> ProposedApp | None:
    for name in _COMPOSE_FILES:
        text = _read_head(path / name, 40000)
        if not text:
            continue
        match = _COMPOSE_PORT.search(text)
        if match is None:
            continue
        port = int(match.group(1))
        command = "docker-compose" if shutil.which("docker-compose") and not shutil.which("docker") else "docker"
        args = ["up"] if command == "docker-compose" else ["compose", "up"]
        return ProposedApp(path.name, str(path), command, args, port)
    return None


def _detect_rails(path: Path) -> ProposedApp | None:
    rails_bin = path / "bin" / "rails"
    gemfile = path / "Gemfile"
    if rails_bin.is_file():
        command = "bin/rails"
    elif gemfile.is_file() and "rails" in _read_head(gemfile, 4000).lower():
        command = "rails"
    else:
        return None
    port = guess_preferred_port(path) or 3000
    return ProposedApp(path.name, str(path), command, ["server", "-b", "127.0.0.1", "-p", str(port)], port)


def _detect_make(path: Path) -> ProposedApp | None:
    text = _read_head(path / "Makefile")
    if not text:
        return None
    match = _MAKE_TARGET.search(text)
    if match is None:
        return None
    port = guess_preferred_port(path)
    if port is None:
        flagged = re.search(r"(?:--port|-p|:)\s*(\d{4,5})", text)
        port = int(flagged.group(1)) if flagged else None
    if port is None:
        return None
    return ProposedApp(path.name, str(path), "make", [match.group(1)], port)
