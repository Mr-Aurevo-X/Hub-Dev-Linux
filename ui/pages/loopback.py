# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio, Gtk  # noqa: E402

from core import i18n
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
        add_root_btn = Gtk.Button(label=i18n.t("loopback_add_root"))
        scan_btn = Gtk.Button(label=i18n.t("loopback_scan"))
        refresh_btn = Gtk.Button(label=i18n.t("loopback_refresh_ports"))
        add_root_btn.connect("clicked", lambda *_: self._pick_root())
        scan_btn.connect("clicked", lambda *_: self._scan())
        refresh_btn.connect("clicked", lambda *_: self._reload_ports())
        toolbar.append(add_root_btn)
        toolbar.append(scan_btn)
        toolbar.append(refresh_btn)
        self._roots_label = Gtk.Label(xalign=0)
        self._roots_label.add_css_class("dim-label")
        self._apps = Gtk.ListBox()
        self._apps.add_css_class("boxed-list")
        self._ports = Gtk.ListBox()
        self._ports.add_css_class("boxed-list")
        self.append(toolbar)
        self.append(self._roots_label)
        self.append(Gtk.Label(label=i18n.t("loopback_apps"), xalign=0))
        self.append(Gtk.ScrolledWindow(min_content_height=180, child=self._apps))
        self.append(Gtk.Label(label=i18n.t("loopback_ports"), xalign=0))
        self.append(Gtk.ScrolledWindow(vexpand=True, child=self._ports))
        self._reload_roots()
        self._reload_apps()
        self._reload_ports()

    def _reload_roots(self) -> None:
        reg = registry.Registry.load()
        roots = ", ".join(reg.allowed_roots) if reg.allowed_roots else "—"
        self._roots_label.set_text(roots)

    def _clear(self, listbox: Gtk.ListBox) -> None:
        while (row := listbox.get_row_at_index(0)) is not None:
            listbox.remove(row)

    def _reload_apps(self) -> None:
        self._clear(self._apps)
        reg = registry.Registry.load()
        for app in reg.apps:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            running = spawn.is_running(app.id)
            status = "●" if running else "○"
            label = Gtk.Label(
                label=f"{status} {app.name} — {app.command} {' '.join(app.args)}",
                xalign=0,
                hexpand=True,
            )
            start = Gtk.Button(label=i18n.t("loopback_start"))
            stop = Gtk.Button(label=i18n.t("loopback_stop"))
            remove = Gtk.Button(label=i18n.t("loopback_remove"))
            open_btn = Gtk.Button(label=i18n.t("loopback_open_url"))
            open_btn.set_sensitive(app.preferred_port is not None)
            aid = app.id
            entry = app

            def do_start(_b: Gtk.Button, e=entry) -> None:
                try:
                    spawn.start(e)
                except (OSError, RuntimeError, ValueError) as exc:
                    self._error(str(exc))
                self._reload_apps()
                GLib.timeout_add(500, self._reload_ports)

            def do_stop(_b: Gtk.Button, app_id=aid) -> None:
                try:
                    spawn.stop(app_id)
                except (OSError, RuntimeError) as exc:
                    self._error(str(exc))
                self._reload_apps()
                self._reload_ports()

            def do_remove(_b: Gtk.Button, app_id=aid) -> None:
                if spawn.is_running(app_id):
                    try:
                        spawn.stop(app_id)
                    except (OSError, RuntimeError):
                        pass
                reg.remove_app(app_id)
                self._reload_apps()

            def do_open(_b: Gtk.Button, e=entry) -> None:
                if e.preferred_port:
                    webbrowser.open(f"http://127.0.0.1:{e.preferred_port}")

            start.connect("clicked", do_start)
            stop.connect("clicked", do_stop)
            remove.connect("clicked", do_remove)
            open_btn.connect("clicked", do_open)
            box.append(label)
            box.append(open_btn)
            box.append(start)
            box.append(stop)
            box.append(remove)
            row.set_child(box)
            self._apps.append(row)

    def _reload_ports(self) -> bool:
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
        return False

    def _pick_root(self) -> None:
        dialog = Gtk.FileDialog(title=i18n.t("loopback_add_root"))
        dialog.select_folder(self._window, None, self._on_root_picked)

    def _on_root_picked(self, dialog: Gtk.FileDialog, result: Gio.AsyncResult) -> None:
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        path = folder.get_path()
        if not path:
            return
        reg = registry.Registry.load()
        reg.add_allowed_root(path)
        self._reload_roots()

    def _scan(self) -> None:
        reg = registry.Registry.load()
        roots = [Path(p) for p in reg.allowed_roots if Path(p).is_dir()]
        if not roots:
            roots = [Path.home()]
        added = 0
        for root in roots:
            for proposal in scanner.scan_root(root):
                if any(a.cwd == proposal.cwd and a.command == proposal.command for a in reg.apps):
                    continue
                try:
                    registry.add_app_from_proposal(proposal, reg)
                    reg = registry.Registry.load()
                    added += 1
                except ValueError:
                    continue
        if added == 0:
            self._info(i18n.t("loopback_scan"))
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

    def _info(self, message: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._window, message_type=Gtk.MessageType.INFO, text=message)
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()
