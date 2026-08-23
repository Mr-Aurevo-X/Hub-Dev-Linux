# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core.loopback import ports, registry, scanner, spawn


class LoopbackPage(Gtk.Box):
    def __init__(self, window: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self.set_margin_top(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        registry.migrate_from_localdock()
        toolbar = Gtk.Box(spacing=8)
        scan_btn = Gtk.Button(label="Scanner racine")
        refresh_btn = Gtk.Button(label="Actualiser ports")
        toolbar.append(scan_btn)
        toolbar.append(refresh_btn)
        self._apps = Gtk.ListBox()
        self._apps.add_css_class("boxed-list")
        self._ports = Gtk.ListBox()
        self._ports.add_css_class("boxed-list")
        scan_btn.connect("clicked", lambda *_: self._scan())
        refresh_btn.connect("clicked", lambda *_: self._reload_ports())
        self.append(toolbar)
        self.append(Gtk.Label(label="Applications enregistrées", xalign=0))
        self.append(Gtk.ScrolledWindow(min_content_height=180, child=self._apps))
        self.append(Gtk.Label(label="Ports loopback", xalign=0))
        self.append(Gtk.ScrolledWindow(vexpand=True, child=self._ports))
        self._reload_apps()
        self._reload_ports()

    def _clear(self, listbox: Gtk.ListBox) -> None:
        while (row := listbox.get_row_at_index(0)) is not None:
            listbox.remove(row)

    def _reload_apps(self) -> None:
        self._clear(self._apps)
        reg = registry.Registry.load()
        for app in reg.apps:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            label = Gtk.Label(label=f"{app.name} — {app.command} {' '.join(app.args)}", xalign=0, hexpand=True)
            start = Gtk.Button(label="Start")
            stop = Gtk.Button(label="Stop")
            aid = app.id

            def do_start(_b: Gtk.Button, entry=app) -> None:
                try:
                    spawn.start(entry)
                except (OSError, RuntimeError, ValueError) as exc:
                    self._error(str(exc))

            def do_stop(_b: Gtk.Button, app_id=aid) -> None:
                try:
                    spawn.stop(app_id)
                except (OSError, RuntimeError) as exc:
                    self._error(str(exc))

            start.connect("clicked", do_start)
            stop.connect("clicked", do_stop)
            box.append(label)
            box.append(start)
            box.append(stop)
            row.set_child(box)
            self._apps.append(row)

    def _reload_ports(self) -> None:
        self._clear(self._ports)
        for row in ports.list_loopback_ports():
            item = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            text = Gtk.Label(label=f":{row.port} {row.process_name} (pid {row.pid})", xalign=0, hexpand=True)
            kill = Gtk.Button(label="Kill")
            pid = row.pid
            kill.connect("clicked", lambda *_a, p=pid: self._kill(p))
            box.append(text)
            box.append(kill)
            item.set_child(box)
            self._ports.append(item)

    def _scan(self) -> None:
        from pathlib import Path

        reg = registry.Registry.load()
        root = Path.home() / "Documents"
        if not root.is_dir():
            root = Path.home()
        for proposal in scanner.scan_root(root):
            app_id = proposal.name.lower().replace(" ", "-")
            if any(a.id == app_id for a in reg.apps):
                continue
            reg.apps.append(
                registry.AppEntry(
                    id=app_id,
                    name=proposal.name,
                    cwd=proposal.cwd,
                    command=proposal.command,
                    args=proposal.args,
                    preferred_port=proposal.preferred_port,
                )
            )
        reg.save()
        self._reload_apps()

    def _kill(self, pid: int) -> None:
        try:
            ports.kill_pid(pid)
        except OSError as exc:
            self._error(str(exc))
        self._reload_ports()

    def _error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._window, message_type=Gtk.MessageType.ERROR, text=message)
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()
