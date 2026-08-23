# SPDX-License-Identifier: GPL-3.0-or-later
"""App registry (apps.json) — port of localdock-core registry."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from core.loopback import scanner
from core.paths import config_dir

REGISTRY_VERSION = 1
_ALLOWED_CMD = re.compile(r"^[a-zA-Z0-9_./+-]+$")


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
                )
            )
        return cls(version=int(data.get("version", REGISTRY_VERSION)), allowed_roots=roots, apps=apps)

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
                }
                for a in self.apps
            ],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def validate_command(self, command: str) -> None:
        if not command or not _ALLOWED_CMD.match(command.split("/")[-1]):
            raise ValueError(f"commande refusée: {command!r}")

    def add_allowed_root(self, path: str) -> None:
        resolved = str(Path(path).expanduser().resolve())
        if resolved not in self.allowed_roots:
            self.allowed_roots.append(resolved)
            self.save()

    def remove_app(self, app_id: str) -> bool:
        before = len(self.apps)
        self.apps = [a for a in self.apps if a.id != app_id]
        if len(self.apps) != before:
            self.save()
            return True
        return False


def add_app_from_proposal(proposal: scanner.ProposedApp, reg: Registry | None = None) -> str:
    reg = reg or Registry.load()
    app_id = proposal.name.lower().replace(" ", "-").replace("_", "-")
    base = app_id
    n = 2
    while any(a.id == app_id for a in reg.apps):
        app_id = f"{base}-{n}"
        n += 1
    entry = AppEntry(
        id=app_id,
        name=proposal.name,
        cwd=proposal.cwd,
        command=proposal.command,
        args=proposal.args,
        preferred_port=proposal.preferred_port,
    )
    reg.validate_command(entry.command)
    reg.apps.append(entry)
    reg.save()
    return app_id


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
