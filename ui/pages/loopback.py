# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import shlex
import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gio, Gtk  # noqa: E402

from core import i18n
from core.loopback import history, ports, registry, scanner, spawn
from ui import compat


def _set_choice(widget: Gtk.Widget, index: int) -> None:
    if hasattr(widget, "set_selected"):
        widget.set_selected(index)
        return
    setter = getattr(widget, "set_active", None)
    if callable(setter):
        setter(index)


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
        form_btn = Gtk.Button(label=i18n.t("loopback_add_edit"))
        add_root_btn.connect("clicked", lambda *_: self._pick_root())
        scan_btn.connect("clicked", lambda *_: self._scan())
        refresh_btn.connect("clicked", lambda *_: self._reload_ports())
        form_btn.connect("clicked", lambda *_: self._open_app_form())
        toolbar.append(add_root_btn)
        toolbar.append(scan_btn)
        toolbar.append(refresh_btn)
        toolbar.append(form_btn)
        self._roots_label = Gtk.Label(xalign=0)
        self._roots_label.add_css_class("dim-label")
        self._apps = Gtk.ListBox()
        self._apps.add_css_class("boxed-list")
        self._ports = Gtk.ListBox()
        self._ports.add_css_class("boxed-list")
        self._history_label = Gtk.Label(xalign=0, wrap=True)
        self._history_label.add_css_class("dim-label")
        self.append(toolbar)
        self.append(self._roots_label)
        self.append(Gtk.Label(label=i18n.t("loopback_apps"), xalign=0))
        self.append(Gtk.ScrolledWindow(min_content_height=180, child=self._apps))
        self.append(Gtk.Label(label=i18n.t("loopback_ports"), xalign=0))
        self.append(Gtk.ScrolledWindow(vexpand=True, child=self._ports))
        self.append(Gtk.Label(label=i18n.t("loopback_history"), xalign=0))
        self.append(self._history_label)
        self._reload_roots()
        self._reload_apps()
        self._reload_ports()
        self._reload_history()

    def _reload_roots(self) -> None:
        reg = registry.Registry.load()
        roots = ", ".join(reg.allowed_roots) if reg.allowed_roots else "—"
        self._roots_label.set_text(roots)

    def _reload_history(self) -> None:
        items = history.load()[-8:]
        if not items:
            self._history_label.set_text("—")
            return
        lines = [f"{item['ts']}  {item['event']}  {item['detail']}" for item in items]
        self._history_label.set_text("\n".join(lines))

    def _clear(self, listbox: Gtk.ListBox) -> None:
        while (row := listbox.get_row_at_index(0)) is not None:
            listbox.remove(row)

    def _reload_apps(self) -> None:
        self._clear(self._apps)
        reg = registry.Registry.load()
        for app in reg.apps:
            row = Gtk.ListBoxRow()
            row.set_name(app.id)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            running = spawn.is_running(app.id)
            status = "●" if running else "○"
            label = Gtk.Label(
                label=f"{status} [{app.profile}] {app.name} — {app.command} {' '.join(app.args)}",
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
                self._reload_history()
                GLib.timeout_add(500, self._reload_ports)

            def do_stop(_b: Gtk.Button, app_id=aid) -> None:
                try:
                    spawn.stop(app_id)
                except (OSError, RuntimeError) as exc:
                    self._error(str(exc))
                self._reload_apps()
                self._reload_ports()
                self._reload_history()

            def do_remove(_b: Gtk.Button, app_id=aid) -> None:
                if spawn.is_running(app_id):
                    try:
                        spawn.stop(app_id)
                    except (OSError, RuntimeError):
                        pass
                reg.remove_app(app_id)
                self._reload_apps()
                self._reload_history()

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

    def _selected_app(self) -> registry.AppEntry | None:
        row = self._apps.get_selected_row()
        if row is None:
            return None
        app_id = row.get_name()
        reg = registry.Registry.load()
        for app in reg.apps:
            if app.id == app_id:
                return app
        return None

    def _open_app_form(self) -> None:
        existing = self._selected_app()
        dialog = Gtk.Dialog()
        dialog.set_transient_for(self._window)
        dialog.set_modal(True)
        dialog.set_title(i18n.t("loopback_add_edit"))
        dialog.add_button(i18n.t("dialog_cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(i18n.t("dialog_ok"), Gtk.ResponseType.OK)
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_margin_start(12)
        grid.set_margin_end(12)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)

        def attach_entry(row: int, key: str, text: str) -> Gtk.Entry:
            label = Gtk.Label(label=i18n.t(key), xalign=0)
            entry = Gtk.Entry()
            entry.set_text(text)
            entry.set_hexpand(True)
            grid.attach(label, 0, row, 1, 1)
            grid.attach(entry, 1, row, 1, 1)
            return entry

        name_entry = attach_entry(0, "loopback_field_name", existing.name if existing else "")
        cwd_entry = attach_entry(1, "loopback_field_cwd", existing.cwd if existing else str(Path.home()))
        command_entry = attach_entry(2, "loopback_field_command", existing.command if existing else "")
        args_text = shlex.join(existing.args) if existing and existing.args else ""
        args_entry = attach_entry(3, "loopback_field_args", args_text)
        port_text = str(existing.preferred_port) if existing and existing.preferred_port is not None else ""
        port_entry = attach_entry(4, "loopback_field_port", port_text)
        profile_label = Gtk.Label(label=i18n.t("loopback_field_profile"), xalign=0)
        profile_labels = [i18n.t(f"profile_{key}") for key in registry.PROFILES]
        profile_widget = compat.string_choice(profile_labels)
        current_profile = existing.profile if existing else "dev"
        if current_profile in registry.PROFILES:
            _set_choice(profile_widget, registry.PROFILES.index(current_profile))
        grid.attach(profile_label, 0, 5, 1, 1)
        grid.attach(profile_widget, 1, 5, 1, 1)
        dialog.get_content_area().append(grid)
        app_id = existing.id if existing else None

        def on_response(dlg: Gtk.Dialog, response: int) -> None:
            if int(response) != int(Gtk.ResponseType.OK):
                dlg.destroy()
                return
            try:
                self._commit_app_form(
                    app_id,
                    name_entry.get_text(),
                    cwd_entry.get_text(),
                    command_entry.get_text(),
                    args_entry.get_text(),
                    port_entry.get_text(),
                    registry.PROFILES[compat.choice_index(profile_widget)]
                    if 0 <= compat.choice_index(profile_widget) < len(registry.PROFILES)
                    else "dev",
                )
            except ValueError as exc:
                self._error(str(exc))
                return
            dlg.destroy()
            self._reload_apps()

        dialog.connect("response", on_response)
        dialog.present()

    def _commit_app_form(
        self,
        app_id: str | None,
        name: str,
        cwd: str,
        command: str,
        args_text: str,
        port_text: str,
        profile: str,
    ) -> None:
        name = name.strip()
        cwd = cwd.strip()
        command = command.strip()
        if not name:
            raise ValueError(i18n.t("loopback_need_name"))
        if not command:
            raise ValueError(i18n.t("loopback_need_command"))
        args = shlex.split(args_text.strip()) if args_text.strip() else []
        port_raw = port_text.strip()
        preferred_port: int | None
        if port_raw:
            try:
                preferred_port = int(port_raw)
            except ValueError as exc:
                raise ValueError(i18n.t("loopback_bad_port")) from exc
        else:
            preferred_port = None
        reg = registry.Registry.load()
        if app_id:
            reg.update_app(
                app_id,
                name=name,
                cwd=cwd,
                command=command,
                args=args,
                preferred_port=preferred_port,
                profile=profile,
            )
            return
        reg.add_app(
            name=name,
            cwd=cwd,
            command=command,
            args=args,
            preferred_port=preferred_port,
            profile=profile,
        )

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
        history.append("scan", str(added))
        if added == 0:
            self._info(i18n.t("loopback_scan"))
        self._reload_apps()
        self._reload_history()

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
