# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import json

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core import i18n


def _buffer_text(view: Gtk.TextView) -> str:
    buf = view.get_buffer()
    start, end = buf.get_start_iter(), buf.get_end_iter()
    return buf.get_text(start, end, True)


class JsonPage(Gtk.Box):
    def __init__(self, window: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self.set_margin_top(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        toolbar = Gtk.Box(spacing=8)
        pretty_btn = Gtk.Button(label=i18n.t("json_pretty"))
        minify_btn = Gtk.Button(label=i18n.t("json_minify"))
        pretty_btn.connect("clicked", lambda *_: self._pretty())
        minify_btn.connect("clicked", lambda *_: self._minify())
        toolbar.append(pretty_btn)
        toolbar.append(minify_btn)
        self._view = Gtk.TextView()
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.NONE)
        self._view.get_buffer().set_text('{\n  "example": true\n}')
        scroll = Gtk.ScrolledWindow(vexpand=True, child=self._view)
        self.append(toolbar)
        self.append(scroll)

    def _pretty(self) -> None:
        try:
            data = json.loads(_buffer_text(self._view))
        except json.JSONDecodeError as exc:
            self._error(str(exc))
            return
        self._view.get_buffer().set_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    def _minify(self) -> None:
        try:
            data = json.loads(_buffer_text(self._view))
        except json.JSONDecodeError as exc:
            self._error(str(exc))
            return
        self._view.get_buffer().set_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))

    def _error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._window, message_type=Gtk.MessageType.ERROR, text=message)
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()
