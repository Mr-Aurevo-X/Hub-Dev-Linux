# SPDX-License-Identifier: GPL-3.0-or-later
"""App registry (apps.json) — port of localdock-core registry."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from core.loopback import history, scanner
from core.paths import config_dir

REGISTRY_VERSION = 1
PROFILES = ("dev", "preview", "prod")
_ALLOWED_CMD = re.compile(r"^[a-zA-Z0-9_./+-]+$")
_UNSET = object()


def _coerce_profile(value: object) -> str:
    key = str(value or "dev").strip().lower()
    return key if key in PROFILES else "dev"


def _slug_id(name: str) -> str:
    app_id = name.lower().replace(" ", "-").replace("_", "-")
    return app_id or "app"


@dataclass
class AppEntry:
    id: str
    name: str
    cwd: str
    command: str
    args: list[str] = field(default_factory=list)
    preferred_port: int | None = None
    force_loopback: bool = True
    enabled: bool = True
    profile: str = "dev"


@dataclass
class Registry:
    version: int = REGISTRY_VERSION
    allowed_roots: list[str] = field(default_factory=list)
    apps: list[AppEntry] = field(default_factory=list)

    @staticmethod
    def path() -> Path:
        return config_dir() / "apps.json"

    @classmethod
    def load(cls) -> Registry:
        path = cls.path()
        if not path.is_file():
            return cls.default_empty()
        data = json.loads(path.read_text(encoding="utf-8"))
        roots = [str(x) for x in data.get("allowed_roots", [])]
        apps = []
        for raw in data.get("apps", []):
            apps.append(
                AppEntry(
                    id=str(raw["id"]),
                    name=str(raw.get("name") or raw["id"]),
                    cwd=str(raw["cwd"]),
                    command=str(raw["command"]),
                    args=[str(a) for a in raw.get("args", [])],
                    preferred_port=raw.get("preferred_port"),
                    force_loopback=bool(raw.get("force_loopback", True)),
                    enabled=bool(raw.get("enabled", True)),
                    profile=_coerce_profile(raw.get("profile")),
                )
            )
        loaded = cls(version=int(data.get("version", REGISTRY_VERSION)), allowed_roots=roots, apps=apps)
        loaded.prune_roots()
        return loaded

    @classmethod
    def default_empty(cls) -> Registry:
        home = str(Path.home())
        return cls(allowed_roots=[home], apps=[])

    def save(self) -> None:
        path = self.path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": REGISTRY_VERSION,
            "allowed_roots": self.allowed_roots,
            "apps": [
                {
                    "id": a.id,
                    "name": a.name,
                    "cwd": a.cwd,
                    "command": a.command,
                    "args": a.args,
                    "preferred_port": a.preferred_port,
                    "force_loopback": a.force_loopback,
                    "enabled": a.enabled,
                    "profile": _coerce_profile(a.profile),
                }
                for a in self.apps
            ],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def validate_command(self, command: str) -> None:
        if not command or not _ALLOWED_CMD.match(command.split("/")[-1]):
            raise ValueError(f"commande refusée: {command!r}")

    def _unique_id(self, base: str) -> str:
        app_id = base
        index = 2
        while any(app.id == app_id for app in self.apps):
            app_id = f"{base}-{index}"
            index += 1
        return app_id

    def add_app(
        self,
        *,
        name: str,
        cwd: str,
        command: str,
        args: list[str] | None = None,
        preferred_port: int | None = None,
        profile: str = "dev",
        force_loopback: bool = True,
        enabled: bool = True,
    ) -> str:
        self.validate_command(command)
        app_id = self._unique_id(_slug_id(name))
        self.apps.append(
            AppEntry(
                id=app_id,
                name=name,
                cwd=cwd,
                command=command,
                args=list(args or []),
                preferred_port=preferred_port,
                force_loopback=force_loopback,
                enabled=enabled,
                profile=_coerce_profile(profile),
            )
        )
        self.save()
        return app_id

    def update_app(
        self,
        app_id: str,
        *,
        name: str | None = None,
        cwd: str | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        preferred_port: object = _UNSET,
        profile: str | None = None,
    ) -> bool:
        for app in self.apps:
            if app.id != app_id:
                continue
            if command is not None:
                self.validate_command(command)
                app.command = command
            if name is not None:
                app.name = name
            if cwd is not None:
                app.cwd = cwd
            if args is not None:
                app.args = list(args)
            if preferred_port is not _UNSET:
                app.preferred_port = preferred_port if preferred_port is None else int(preferred_port)
            if profile is not None:
                app.profile = _coerce_profile(profile)
            self.save()
            return True
        return False

    def add_allowed_root(self, path: str) -> bool:
        try:
            resolved = str(scanner.normalize_root(path))
        except (OSError, ValueError):
            return False
        existing = []
        for root in self.allowed_roots:
            try:
                existing.append(str(Path(root).expanduser().resolve()))
            except OSError:
                existing.append(root)
        if resolved in existing:
            return False
        self.allowed_roots = [r for r in self.allowed_roots if Path(r).name not in scanner.SKIP_DIRS]
        self.allowed_roots.append(resolved)
        self.save()
        return True

    def prune_roots(self) -> bool:
        kept: list[str] = []
        seen: set[str] = set()
        changed = False
        for root in self.allowed_roots:
            raw = Path(root)
            if raw.name in scanner.SKIP_DIRS:
                changed = True
                continue
            try:
                key = str(raw.expanduser().resolve()) if raw.exists() else str(raw)
            except OSError:
                key = str(raw)
            if key in seen:
                changed = True
                continue
            seen.add(key)
            kept.append(key)
        if kept != self.allowed_roots:
            self.allowed_roots = kept
            self.save()
            return True
        return changed

    def remove_allowed_root(self, path: str) -> bool:
        try:
            target = str(Path(path).expanduser().resolve())
        except OSError:
            target = path
        before = len(self.allowed_roots)
        kept: list[str] = []
        for root in self.allowed_roots:
            try:
                key = str(Path(root).expanduser().resolve())
            except OSError:
                key = root
            if key != target and root != path:
                kept.append(root)
        if len(kept) == before:
            return False
        self.allowed_roots = kept
        self.save()
        return True

    def scan_apps(self) -> int:
        roots = [Path(raw) for raw in self.allowed_roots if Path(raw).is_dir()]
        if not roots:
            return 0
        proposals = [item for root in roots for item in scanner.scan_root(root) if scanner.is_launchable(item)]
        return self._ingest(proposals)

    def scan_disk(self, should_stop: scanner.StopCheck | None = None) -> int:
        return self._ingest(scanner.scan_disk(require_launchable=True, should_stop=should_stop))

    def _cwd_key(self, raw: str) -> str:
        try:
            return str(Path(raw).expanduser().resolve())
        except OSError:
            return raw

    def _ingest(self, proposals: Iterable[scanner.ProposedApp]) -> int:
        wanted = {self._cwd_key(item.cwd): item for item in proposals}
        kept: list[AppEntry] = []
        seen: set[str] = set()
        for app in self.apps:
            key = self._cwd_key(app.cwd)
            if scanner.is_workspace_member_of_hub(Path(app.cwd)):
                continue
            if key in seen:
                continue
            seen.add(key)
            kept.append(app)
        self.apps = kept
        added = 0
        for key, proposal in wanted.items():
            existing = next((app for app in self.apps if self._cwd_key(app.cwd) == key), None)
            if existing is not None:
                self.update_app(
                    existing.id,
                    name=proposal.name,
                    cwd=proposal.cwd,
                    command=proposal.command,
                    args=proposal.args,
                    preferred_port=proposal.preferred_port,
                )
                continue
            try:
                add_app_from_proposal(proposal, self)
                self.apps = type(self).load().apps
                added += 1
            except ValueError:
                continue
        self.save()
        return added

    def remove_app(self, app_id: str) -> bool:
        before = len(self.apps)
        self.apps = [a for a in self.apps if a.id != app_id]
        if len(self.apps) != before:
            self.save()
            history.append("remove", app_id)
            return True
        return False


def add_app_from_proposal(proposal: scanner.ProposedApp, reg: Registry | None = None) -> str:
    reg = reg or Registry.load()
    return reg.add_app(
        name=proposal.name,
        cwd=proposal.cwd,
        command=proposal.command,
        args=proposal.args,
        preferred_port=proposal.preferred_port,
    )


def migrate_from_localdock() -> None:
    legacy = [
        Path.home() / ".config" / "LocalDock" / "apps.json",
        Path.home() / ".var" / "app" / "org.mraurevox.LocalDock" / "config" / "LocalDock" / "apps.json",
    ]
    dest = Registry.path()
    if dest.is_file():
        return
    for src in legacy:
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            return
