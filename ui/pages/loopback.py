# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import shlex
import webbrowser
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gio, Gtk  # noqa: E402

from core import i18n
from core.loopback import history, ports, registry, scanner, spawn
from ui import compat

_CSS = b"""
.loopback-tile {
  min-width: 118px;
  max-width: 150px;
  padding: 10px 8px;
  border-radius: 12px;
}
.loopback-tile:hover {
  background-color: alpha(currentColor, 0.08);
}
.loopback-tile.running {
  background-color: alpha(#6ee7a8, 0.12);
}
.loopback-root-header {
  margin-top: 8px;
  margin-bottom: 4px;
}
.loopback-tile-name {
  font-weight: 600;
}
.loopback-tile-meta {
  opacity: 0.75;
  font-size: 0.85em;
}
"""


def _set_choice(widget: Gtk.Widget, index: int) -> None:
    if hasattr(widget, "set_selected"):
        widget.set_selected(index)
        return
    setter = getattr(widget, "set_active", None)
    if callable(setter):
        setter(index)


def _ensure_css() -> None:
    display = Gdk.Display.get_default()
    if display is None:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(_CSS)
    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


class LoopbackPage(Gtk.Box):
    def __init__(self, window: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self._selected_id: str | None = None
        self.set_margin_top(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        _ensure_css()
        registry.migrate_from_localdock()
        toolbar = Gtk.Box(spacing=8)
        add_root_btn = Gtk.Button(label=i18n.t("loopback_add_root"))
        scan_btn = Gtk.Button(label=i18n.t("loopback_scan"))
        refresh_btn = Gtk.Button(label=i18n.t("loopback_refresh_ports"))
        form_btn = Gtk.Button(label=i18n.t("loopback_add_edit"))
        add_root_btn.connect("clicked", lambda *_: self._pick_root())
        scan_btn.connect("clicked", lambda *_: self._scan(notify=True))
        refresh_btn.connect("clicked", lambda *_: self._reload_ports())
        form_btn.connect("clicked", lambda *_: self._open_app_form())
        toolbar.append(add_root_btn)
        toolbar.append(scan_btn)
        toolbar.append(refresh_btn)
        toolbar.append(form_btn)

        path_row = Gtk.Box(spacing=8)
        self._path_entry = Gtk.Entry()
        self._path_entry.set_hexpand(True)
        self._path_entry.set_placeholder_text(i18n.t("loopback_paste_hint"))
        self._path_entry.connect("activate", lambda *_: self._link_typed_path())
        link_btn = Gtk.Button(label=i18n.t("loopback_link_path"))
        link_btn.add_css_class("suggested-action")
        link_btn.connect("clicked", lambda *_: self._link_typed_path())
        path_row.append(self._path_entry)
        path_row.append(link_btn)

        actions = Gtk.Box(spacing=8)
        self._open_btn = Gtk.Button(label=i18n.t("loopback_open_url"))
        self._start_btn = Gtk.Button(label=i18n.t("loopback_start"))
        self._stop_btn = Gtk.Button(label=i18n.t("loopback_stop"))
        self._remove_btn = Gtk.Button(label=i18n.t("loopback_remove"))
        self._open_btn.connect("clicked", lambda *_: self._open_selected())
        self._start_btn.connect("clicked", lambda *_: self._start_selected())
        self._stop_btn.connect("clicked", lambda *_: self._stop_selected())
        self._remove_btn.connect("clicked", lambda *_: self._remove_selected())
        for btn in (self._open_btn, self._start_btn, self._stop_btn, self._remove_btn):
            actions.append(btn)

        self._explorer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        explorer_scroll = Gtk.ScrolledWindow(min_content_height=280, vexpand=True)
        explorer_scroll.set_child(self._explorer)

        self._ports = Gtk.ListBox()
        self._ports.add_css_class("boxed-list")
        self._history_label = Gtk.Label(xalign=0, wrap=True)
        self._history_label.add_css_class("dim-label")
        self.append(toolbar)
        self.append(path_row)
        self.append(Gtk.Label(label=i18n.t("loopback_explorer"), xalign=0))
        self.append(actions)
        self.append(explorer_scroll)
        self.append(Gtk.Label(label=i18n.t("loopback_ports"), xalign=0))
        self.append(Gtk.ScrolledWindow(min_content_height=90, child=self._ports))
        self.append(Gtk.Label(label=i18n.t("loopback_history"), xalign=0))
        self.append(self._history_label)
        self._setup_drop()
        self._scan_empty_roots()
        self._reload_apps()
        self._reload_ports()
        self._reload_history()

    def _setup_drop(self) -> None:
        drop = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

    def _on_drop(self, _target: Gtk.DropTarget, value: object, _x: float, _y: float) -> bool:
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                self._apply_root(path)
                return True
        return False

    def _clear_box(self, box: Gtk.Box) -> None:
        child = box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt

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
        self._clear_box(self._explorer)
        reg = registry.Registry.load()
        groups = scanner.apps_grouped_by_root(reg.allowed_roots, reg.apps)
        if not reg.allowed_roots and not reg.apps:
            empty = Gtk.Label(label=i18n.t("loopback_no_apps"), xalign=0, wrap=True)
            empty.add_css_class("dim-label")
            self._explorer.append(empty)
            return
        any_tile = False
        for root, apps in groups:
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            header.add_css_class("loopback-root-header")
            folder = Gtk.Image.new_from_icon_name("folder-symbolic")
            folder.set_pixel_size(18)
            title = Path(root).name if root else i18n.t("loopback_apps")
            label = Gtk.Label(label=title, xalign=0, hexpand=True)
            label.add_css_class("heading")
            header.append(folder)
            header.append(label)
            if root:
                remove = Gtk.Button(label=i18n.t("loopback_remove_root"))
                remove.add_css_class("flat")
                remove.connect("clicked", lambda *_a, p=root: self._remove_root(p))
                header.append(remove)
            self._explorer.append(header)
            if not apps:
                hint = Gtk.Label(label=i18n.t("loopback_no_apps"), xalign=0, wrap=True)
                hint.add_css_class("dim-label")
                self._explorer.append(hint)
                continue
            flow = Gtk.FlowBox()
            flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
            flow.set_min_children_per_line(2)
            flow.set_max_children_per_line(8)
            flow.set_homogeneous(True)
            flow.connect("child-activated", self._on_tile_activated)
            flow.connect("selected-children-changed", self._on_tile_selected)
            for app in apps:
                flow.append(self._make_tile(app))
                any_tile = True
            self._explorer.append(flow)
        if not any_tile and reg.allowed_roots:
            pass
        self._sync_actions()

    def _make_tile(self, app: registry.AppEntry) -> Gtk.Widget:
        running = spawn.is_running(app.id)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("loopback-tile")
        if running:
            box.add_css_class("running")
        icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        icon.set_pixel_size(40)
        icon.set_halign(Gtk.Align.CENTER)
        name = Gtk.Label(label=app.name, wrap=True, justify=Gtk.Justification.CENTER)
        name.add_css_class("loopback-tile-name")
        name.set_max_width_chars(16)
        if running and app.preferred_port:
            meta_text = f"{i18n.t('loopback_running')} :{app.preferred_port}"
        elif app.preferred_port:
            meta_text = f"{i18n.t('loopback_stopped')} :{app.preferred_port}"
        else:
            meta_text = i18n.t("loopback_running") if running else i18n.t("loopback_stopped")
        meta = Gtk.Label(label=meta_text, wrap=True, justify=Gtk.Justification.CENTER)
        meta.add_css_class("loopback-tile-meta")
        box.append(icon)
        box.append(name)
        box.append(meta)
        box.set_name(app.id)
        return box

    def _on_tile_selected(self, flow: Gtk.FlowBox) -> None:
        children = flow.get_selected_children()
        if not children:
            return
        widget = children[0].get_child()
        if widget is None:
            return
        self._selected_id = widget.get_name() or None
        self._sync_actions()

    def _on_tile_activated(self, _flow: Gtk.FlowBox, child: Gtk.FlowBoxChild) -> None:
        widget = child.get_child()
        if widget is None:
            return
        self._selected_id = widget.get_name() or None
        self._sync_actions()
        app = self._selected_app()
        if app is None:
            return
        running = spawn.is_running(app.id)
        port = ports.resolve_open_port(app, is_running=running, pid=spawn.running_pid(app.id))
        if running and port:
            webbrowser.open(f"http://127.0.0.1:{port}")
            return
        self._start_selected()

    def _selected_app(self) -> registry.AppEntry | None:
        if not self._selected_id:
            return None
        reg = registry.Registry.load()
        for app in reg.apps:
            if app.id == self._selected_id:
                return app
        return None

    def _sync_actions(self) -> None:
        app = self._selected_app()
        enabled = app is not None
        running = bool(app and spawn.is_running(app.id))
        self._start_btn.set_sensitive(enabled and not running)
        self._stop_btn.set_sensitive(enabled and running)
        self._remove_btn.set_sensitive(enabled)
        self._open_btn.set_sensitive(
            bool(app)
            and ports.can_open(app, is_running=running, pid=spawn.running_pid(app.id) if app else None)
        )

    def _start_selected(self) -> None:
        app = self._selected_app()
        if app is None:
            return
        try:
            spawn.start(app)
        except (OSError, RuntimeError, ValueError) as exc:
            self._error(str(exc))
        self._reload_apps()
        self._reload_history()
        GLib.timeout_add(500, self._reload_ports)

    def _stop_selected(self) -> None:
        app = self._selected_app()
        if app is None:
            return
        try:
            spawn.stop(app.id)
        except (OSError, RuntimeError) as exc:
            self._error(str(exc))
        self._reload_apps()
        self._reload_ports()
        self._reload_history()

    def _remove_selected(self) -> None:
        app = self._selected_app()
        if app is None:
            return
        if spawn.is_running(app.id):
            try:
                spawn.stop(app.id)
            except (OSError, RuntimeError):
                pass
        registry.Registry.load().remove_app(app.id)
        self._selected_id = None
        self._reload_apps()
        self._reload_history()

    def _open_selected(self) -> None:
        app = self._selected_app()
        if app is None:
            return
        port = ports.resolve_open_port(
            app,
            is_running=spawn.is_running(app.id),
            pid=spawn.running_pid(app.id),
        )
        if port is None:
            return
        webbrowser.open(f"http://127.0.0.1:{port}")

    def _scan_empty_roots(self) -> None:
        reg = registry.Registry.load()
        if scanner.empty_linked_roots(reg.allowed_roots, reg.apps):
            self._scan(notify=False)

    def _remove_root(self, path: str) -> None:
        registry.Registry.load().remove_allowed_root(path)
        self._reload_apps()

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
        path = folder.get_path() if folder is not None else None
        if not path:
            uri = folder.get_uri() if folder is not None else ""
            if uri.startswith("file://"):
                path = Gio.File.new_for_uri(uri).get_path()
        if path:
            self._apply_root(path)

    def _link_typed_path(self) -> None:
        raw = (self._path_entry.get_text() or "").strip().strip('"').strip("'")
        if not raw:
            return
        self._apply_root(raw)

    def _apply_root(self, path: str) -> None:
        reg = registry.Registry.load()
        added = reg.add_allowed_root(path)
        if not added:
            try:
                scanner.normalize_root(path)
            except (OSError, ValueError):
                self._error(i18n.t("loopback_bad_root"))
                return
        self._path_entry.set_text("")
        self._scan(notify=False)
        self._reload_history()
        if added:
            history.append("root", path)
            self._reload_history()

    def _scan(self, *, notify: bool = False) -> None:
        reg = registry.Registry.load()
        added = reg.scan_apps()
        history.append("scan", str(added))
        if notify:
            self._info(i18n.t("loopback_scan_done", count=str(added)))
        self._reload_apps()
        self._reload_history()

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
