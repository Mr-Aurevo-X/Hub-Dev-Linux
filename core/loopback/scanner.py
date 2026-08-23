# SPDX-License-Identifier: GPL-3.0-or-later
"""Project scanner — detect launchable localhost servers."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.loopback import hostcmd, toolchain
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
    ".vscode",
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
    "netns",
    ".snapshots",
    ".var",
    "AppData",
    "Windows",
    "Windows.old",
    "Program Files",
    "Program Files (x86)",
    "ProgramData",
    "$Recycle.Bin",
    "System Volume Information",
    "Recovery",
    "PerfLogs",
    "Application Data",
    "Local Settings",
}
DEV_SCRIPT_PRIORITY = (
    "dev:local",
    "dev:local:all",
    "dev",
    "start:dev",
    "serve",
    "preview",
    "start",
    "storybook",
    "dev:server",
    "web",
)
_HUB_SCRIPTS = ("dev:local", "dev:local:all")
_WORKSPACE_MARKERS = ("pnpm-workspace.yaml", "lerna.json", "turbo.json")
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
    "nsfs",
    "rpc_pipefs",
    "mqueue",
    "hugetlbfs",
    "configfs",
    "devpts",
    "binfmt_misc",
}
_SKIP_MOUNT = {"/", "/boot", "/boot/efi", "/boot/efi2", "/run/host", "/run/host/root"}
_SKIP_PATH_TOKENS = (
    "/run/host",
    "/docker/netns",
    "/run/docker/",
    "/var/lib/docker/",
    "/.snapshots",
    "/run/flatpak",
)
_USER_DISK_PREFIXES = ("/run/media/", "/media/", "/mnt/")
_FIXED_DISK_ROOTS = (
    Path("/home"),
    Path("/opt"),
    Path("/srv"),
    Path("/var/www"),
    Path("/mnt"),
    Path("/media"),
)
_DETECT_MARKERS = frozenset(
    {
        "package.json",
        "manage.py",
        "app.py",
        "main.py",
        "wsgi.py",
        "artisan",
        "Gemfile",
        "Makefile",
        "compose.yaml",
        "compose.yml",
        "docker-compose.yml",
        "docker-compose.yaml",
    }
)
_DISK_MAX_DEPTH = 12
StopCheck = Callable[[], bool]
ProgressCb = Callable[[str], None]


@dataclass
class ProposedApp:
    name: str
    cwd: str
    command: str
    args: list[str]
    preferred_port: int | None = None


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def should_skip_path(path: str | Path) -> bool:
    raw = str(path).replace("\\", "/")
    if any(token in raw for token in _SKIP_PATH_TOKENS):
        return True
    return Path(path).name in SKIP_DIRS


def unescape_mount(dest: str) -> str:
    return (
        dest.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def parse_proc_mounts(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append((unescape_mount(parts[1]), parts[2]))
    return rows


def is_user_disk_mount(dest: str, fstype: str) -> bool:
    if fstype in _VIRTUAL_FS or fstype.startswith(("fuse.portal", "fuse.gvfs")):
        return False
    if dest in _SKIP_MOUNT or should_skip_path(dest):
        return False
    return dest.startswith(_USER_DISK_PREFIXES)


def extra_mount_roots(text: str) -> list[Path]:
    return [Path(dest) for dest, fstype in parse_proc_mounts(text) if is_user_disk_mount(dest, fstype)]


def collapse_nested_roots(roots: list[Path]) -> list[Path]:
    kept: list[Path] = []
    for root in sorted(roots, key=lambda path: (len(path.parts), str(path))):
        if any(root == parent or parent in root.parents for parent in kept):
            continue
        kept.append(root)
    return kept


def normalize_root(path: str | Path) -> Path:
    try:
        resolved = Path(path).expanduser().resolve()
    except OSError as exc:
        raise ValueError(f"not a directory: {path}") from exc
    if not _is_dir(resolved):
        raise ValueError(f"not a directory: {resolved}")
    if should_skip_path(resolved):
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
    if not _is_dir(cwd):
        return False
    command = proposal.command
    direct = Path(command)
    if direct.is_file() and os.access(direct, os.X_OK):
        return True
    relative = cwd / command
    if relative.is_file() and os.access(relative, os.X_OK):
        return True
    return hostcmd.which(command) is not None


def scan_root(
    root: Path,
    max_depth: int = 8,
    *,
    should_stop: StopCheck | None = None,
    on_progress: ProgressCb | None = None,
) -> list[ProposedApp]:
    proposals: list[ProposedApp] = []
    try:
        start = normalize_root(root)
    except ValueError:
        start = Path(root)
        if should_skip_path(start) or not _is_dir(start):
            return []
    try:
        _scan_dir(start, 0, max_depth, proposals, should_stop, on_progress)
    except OSError:
        return proposals
    return proposals


def disk_scan_roots() -> list[Path]:
    try:
        mounts = Path("/proc/mounts").read_text(encoding="utf-8", errors="replace")
    except OSError:
        mounts = ""
    candidates = [Path.home(), *_FIXED_DISK_ROOTS, *extra_mount_roots(mounts)]
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in candidates:
        try:
            resolved = raw.expanduser().resolve()
        except OSError:
            continue
        if should_skip_path(resolved) or not _is_dir(resolved):
            continue
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        roots.append(resolved)
    return collapse_nested_roots(roots)


def scan_disk(
    *,
    roots: list[Path] | None = None,
    require_launchable: bool = True,
    max_depth: int = _DISK_MAX_DEPTH,
    should_stop: StopCheck | None = None,
    on_progress: ProgressCb | None = None,
) -> list[ProposedApp]:
    start_roots = list(roots) if roots is not None else disk_scan_roots()
    seen: set[tuple[str, str]] = set()
    out: list[ProposedApp] = []
    for root in start_roots:
        if should_stop and should_stop():
            break
        try:
            found = scan_root(
                root,
                max_depth=max_depth,
                should_stop=should_stop,
                on_progress=on_progress,
            )
        except OSError:
            continue
        for proposal in found:
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
    for detector in (_detect_node, _detect_python, _detect_php, _detect_compose, _detect_rails, _detect_make):
        proposal = detector(path)
        if proposal is not None:
            return [proposal]
    return []


def _scan_dir(
    path: Path,
    depth: int,
    max_depth: int,
    out: list[ProposedApp],
    should_stop: StopCheck | None,
    on_progress: ProgressCb | None = None,
) -> None:
    if should_stop and should_stop():
        return
    if depth > max_depth:
        return
    if on_progress is not None:
        on_progress(str(path))
    try:
        entries = list(os.scandir(path))
    except OSError:
        return
    names = {entry.name for entry in entries}
    if names & _DETECT_MARKERS:
        out.extend(detect_in_dir(path))
    if depth == max_depth:
        return
    for entry in entries:
        if should_stop and should_stop():
            return
        try:
            if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                continue
        except OSError:
            continue
        child = Path(entry.path)
        if should_skip_path(child):
            continue
        if entry.name == "fixtures" and path.name in {"test", "tests"}:
            continue
        _scan_dir(child, depth + 1, max_depth, out, should_stop, on_progress)


def _read_head(path: Path, limit: int = 12000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _preferred_package_manager(path: Path, data: dict[object, object]) -> str:
    manager = str(data.get("packageManager") or "")
    if manager.startswith("bun") or (path / "bun.lockb").is_file() or (path / "bun.lock").is_file():
        return "bun"
    if manager.startswith("pnpm") or (path / "pnpm-lock.yaml").is_file() or (path / "pnpm-workspace.yaml").is_file():
        return "pnpm"
    if manager.startswith("yarn") or (path / "yarn.lock").is_file():
        return "yarn"
    return "npm"


def _package_manager(path: Path, data: dict[object, object]) -> str:
    preferred = _preferred_package_manager(path, data)
    order = [preferred]
    for extra in ("pnpm", "npm", "yarn", "bun"):
        if extra not in order:
            order.append(extra)
    for command in order:
        if hostcmd.which(command):
            return command
    return preferred


def _pnpm_version(data: dict[object, object]) -> str:
    manager = str(data.get("packageManager") or "")
    if manager.startswith("pnpm@"):
        return manager.split("@", 1)[1].split("+")[0]
    return "9"


def _node_launch(path: Path, data: dict[object, object], picked: str, scripts: dict[str, str]) -> tuple[str, list[str]] | None:
    body = scripts.get(picked, "")
    if "pnpm" in body:
        found = toolchain.which_pnpm()
        if found:
            return found, ["run", picked]
        if hostcmd.which("corepack"):
            return "corepack", ["pnpm", "run", picked]
        if hostcmd.which("npx"):
            return "npx", ["--yes", f"pnpm@{_pnpm_version(data)}", "run", picked]
        return None
    command = _package_manager(path, data)
    if not hostcmd.which(command) and not Path(command).is_file():
        return None
    return command, ["run", picked]


def _port_from_workspace_apps(root: Path) -> int | None:
    for rel in ("apps", "packages"):
        base = root / rel
        if not base.is_dir():
            continue
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            scripts = _package_scripts(child)
            if not scripts:
                continue
            picked = _pick_script(scripts)
            port = guess_preferred_port(child, scripts, picked=picked)
            if port:
                return port
    return None


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


def _package_scripts(path: Path) -> dict[str, str]:
    pkg = path / "package.json"
    if not pkg.is_file():
        return {}
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    scripts = data.get("scripts") or {}
    if not isinstance(scripts, dict):
        return {}
    return {str(name): str(value) for name, value in scripts.items()}


def _has_hub_script(path: Path) -> bool:
    scripts = _package_scripts(path)
    if any(key in scripts for key in _HUB_SCRIPTS):
        return True
    if not (path / "pnpm-workspace.yaml").is_file() and not (path / "pnpm-workspace.yml").is_file():
        return False
    body = scripts.get("dev", "")
    return any(token in body for token in ("pnpm --filter", "pnpm -r", "docker:up", "docker compose"))


def is_covered_by_hub(path: Path) -> bool:
    current = Path(path)
    return any(_has_hub_script(parent) for parent in current.parents)


def is_workspace_member_of_hub(path: Path) -> bool:
    return is_covered_by_hub(path)


def _detect_node(path: Path) -> ProposedApp | None:
    if is_covered_by_hub(path):
        return None
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
    launch = _node_launch(path, data, picked, scripts_text)
    if launch is None:
        return None
    command, args = launch
    port = guess_preferred_port(path, scripts_text, picked=picked) or _port_from_workspace_apps(path)
    return ProposedApp(path.name, str(path), command, args, port)


def _python_cmd(path: Path) -> str:
    for rel in (".venv/bin/python", "venv/bin/python"):
        candidate = path / rel
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    if hostcmd.which("python3"):
        return "python3"
    if hostcmd.which("python"):
        return "python"
    return "python3"


def _detect_python(path: Path) -> ProposedApp | None:
    django = path / "manage.py"
    py_files = [name for name in ("app.py", "main.py", "wsgi.py") if (path / name).is_file()]
    if not django.is_file() and not py_files:
        return None
    command = _python_cmd(path)
    if django.is_file():
        return ProposedApp(path.name, str(path), command, ["manage.py", "runserver", "127.0.0.1:8000"], 8000)
    for name in py_files:
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
        command = "docker-compose" if hostcmd.which("docker-compose") and not hostcmd.which("docker") else "docker"
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
