# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

from gi.repository import Gtk

from core import i18n
from core import textutil
from ui import compat
from ui.helpers import show_toast
from ui.pages import common


class TextDiffPage:
    def __init__(self, window: Gtk.Window, toast: Gtk.Widget) -> None:
        self._window = window
        self._toast = toast
        self._path_a: Path | None = None
        self._path_b: Path | None = None
        self.widget = self._build()

    def receive_paths(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._set_a(paths[:1])
        if len(paths) > 1:
            self._set_b(paths[1:2])

    def _build(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        common.padded(box)
        a_btn = Gtk.Button(label=i18n.t("textdiff_a"))
        a_btn.connect("clicked", lambda *_: compat.open_files(self._window, self._set_a))
        b_btn = Gtk.Button(label=i18n.t("textdiff_b"))
        b_btn.connect("clicked", lambda *_: compat.open_files(self._window, self._set_b))
        box.append(
            common.prefs_group(
                i18n.t("group_files"),
                [
                    common.action_row(i18n.t("textdiff_a"), a_btn),
                    common.action_row(i18n.t("textdiff_b"), b_btn),
                ],
            )
        )
        self._label_a = Gtk.Label(label="A —", wrap=True, xalign=0)
        self._label_b = Gtk.Label(label="B —", wrap=True, xalign=0)
        box.append(self._label_a)
        box.append(self._label_b)
        self._ignore_ws = Gtk.CheckButton(label=i18n.t("textdiff_ignore_ws"))
        self._ignore_eol = Gtk.CheckButton(label=i18n.t("textdiff_ignore_eol"))
        self._ignore_ws.connect("toggled", lambda *_: self._refresh())
        self._ignore_eol.connect("toggled", lambda *_: self._refresh())
        box.append(self._ignore_ws)
        box.append(self._ignore_eol)
        cols = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._left = Gtk.TextView()
        self._right = Gtk.TextView()
        for view in (self._left, self._right):
            view.set_editable(False)
            view.set_monospace(True)
            view.set_wrap_mode(Gtk.WrapMode.NONE)
            view.set_hexpand(True)
            cols.append(common.scrolled(view))
        cols.set_vexpand(True)
        box.append(cols)
        compat.enable_file_drop(box, self.receive_paths)
        return common.scrolled(box)

    def _set_a(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._path_a = paths[0]
        self._label_a.set_text(f"A — {self._path_a}")
        self._refresh()

    def _set_b(self, paths: list[Path]) -> None:
        if not paths:
            return
        self._path_b = paths[0]
        self._label_b.set_text(f"B — {self._path_b}")
        self._refresh()

    def _refresh(self) -> None:
        if self._path_a is None or self._path_b is None:
            return
        try:
            left = self._path_a.read_text(encoding="utf-8")
            right = self._path_b.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            show_toast(self._toast, str(exc), 6)
            return
        left_lines: list[str] = []
        right_lines: list[str] = []
        for mark, line in textutil.lined_diff_options(
            left,
            right,
            ignore_ws=self._ignore_ws.get_active(),
            ignore_eol=self._ignore_eol.get_active(),
        ):
            if mark == " ":
                left_lines.append(f"  {line}")
                right_lines.append(f"  {line}")
            elif mark == "-":
                left_lines.append(f"- {line}")
                right_lines.append("")
            elif mark == "+":
                left_lines.append("")
                right_lines.append(f"+ {line}")
        self._left.get_buffer().set_text("\n".join(left_lines))
        self._right.get_buffer().set_text("\n".join(right_lines))
