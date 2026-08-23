# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core import envutil, i18n


def _buffer_text(view: Gtk.TextView) -> str:
    buf = view.get_buffer()
    start, end = buf.get_start_iter(), buf.get_end_iter()
    return buf.get_text(start, end, True)


class EnvPage(Gtk.Box):
    def __init__(self, window: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self.set_margin_top(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        toolbar = Gtk.Box(spacing=8)
        sort_btn = Gtk.Button(label=i18n.t("env_sort"))
        validate_btn = Gtk.Button(label=i18n.t("env_validate"))
        toolbar.append(sort_btn)
        toolbar.append(validate_btn)
        self._view = Gtk.TextView()
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.NONE)
        self._view.get_buffer().set_text("APP_ENV=development\nPORT=3000\n")
        scroll = Gtk.ScrolledWindow(vexpand=True, child=self._view)
        sort_btn.connect("clicked", lambda *_: self._sort())
        validate_btn.connect("clicked", lambda *_: self._validate())
        self.append(toolbar)
        self.append(scroll)

    def _sort(self) -> None:
        try:
            data = envutil.parse_env(_buffer_text(self._view))
        except envutil.EnvError as exc:
            self._error(str(exc))
            return
        self._view.get_buffer().set_text(envutil.format_env(data))

    def _validate(self) -> None:
        try:
            envutil.parse_env(_buffer_text(self._view))
        except envutil.EnvError as exc:
            self._error(str(exc))
            return
        dialog = Gtk.MessageDialog(
            transient_for=self._window,
            message_type=Gtk.MessageType.INFO,
            text=i18n.t("env_ok"),
        )
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()

    def _error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._window, message_type=Gtk.MessageType.ERROR, text=message)
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()
