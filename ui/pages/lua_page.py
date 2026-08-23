# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core import i18n
from core.luautil import check_syntax, format_lua


def _buffer_text(view: Gtk.TextView) -> str:
    buf = view.get_buffer()
    start, end = buf.get_start_iter(), buf.get_end_iter()
    return buf.get_text(start, end, True)


class LuaPage(Gtk.Box):
    def __init__(self, window: Gtk.Window) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self.set_margin_top(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        toolbar = Gtk.Box(spacing=8)
        pretty_btn = Gtk.Button(label=i18n.t("lua_pretty"))
        check_btn = Gtk.Button(label=i18n.t("lua_check"))
        pretty_btn.connect("clicked", lambda *_: self._pretty())
        check_btn.connect("clicked", lambda *_: self._check())
        toolbar.append(pretty_btn)
        toolbar.append(check_btn)
        self._view = Gtk.TextView()
        self._view.set_monospace(True)
        self._view.set_wrap_mode(Gtk.WrapMode.NONE)
        self._view.get_buffer().set_text("function hello()\n  return { ok = true }\nend\n")
        scroll = Gtk.ScrolledWindow(vexpand=True, child=self._view)
        self.append(toolbar)
        self.append(scroll)

    def _pretty(self) -> None:
        self._view.get_buffer().set_text(format_lua(_buffer_text(self._view)))

    def _check(self) -> None:
        errors = check_syntax(_buffer_text(self._view))
        if not errors:
            dialog = Gtk.MessageDialog(
                transient_for=self._window,
                message_type=Gtk.MessageType.INFO,
                text=i18n.t("lua_ok"),
            )
            dialog.connect("response", lambda d, *_: d.destroy())
            dialog.present()
            return
        self._error("\n".join(errors))

    def _error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(transient_for=self._window, message_type=Gtk.MessageType.ERROR, text=message)
        dialog.connect("response", lambda d, *_: d.destroy())
        dialog.present()
