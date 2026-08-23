# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path

from gi.repository import Gtk

from core import i18n
from core import snippets
from ui import compat
from ui.helpers import show_toast
from ui.pages import common


class SnippetsPage:
    def __init__(self, window: Gtk.Window, toast: Gtk.Widget) -> None:
        self._window = window
        self._toast = toast
        self.widget = self._build()
        self._reload()

    def _build(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        common.padded(box)
        self._name = Gtk.Entry(placeholder_text=i18n.t("snippets_name"))
        self._tags = Gtk.Entry(placeholder_text=i18n.t("snippets_tags"))
        self._filter_tag = Gtk.Entry(placeholder_text=i18n.t("snippets_filter"))
        box.append(self._name)
        box.append(self._tags)
        box.append(self._filter_tag)
        self._body = Gtk.TextView()
        self._body.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        box.append(common.scrolled(self._body))
        save = Gtk.Button(label=i18n.t("snippets_save"))
        save.add_css_class("suggested-action")
        save.connect("clicked", lambda *_: self._save())
        copy = Gtk.Button(label=i18n.t("copy"))
        copy.connect("clicked", lambda *_: self._copy())
        delete = Gtk.Button(label=i18n.t("snippets_delete"))
        delete.connect("clicked", lambda *_: self._delete())
        filter_btn = Gtk.Button(label=i18n.t("snippets_filter_go"))
        filter_btn.connect("clicked", lambda *_: self._reload())
        export_btn = Gtk.Button(label=i18n.t("snippets_export"))
        export_btn.connect("clicked", lambda *_: self._export_json())
        import_btn = Gtk.Button(label=i18n.t("snippets_import"))
        import_btn.connect("clicked", lambda *_: compat.open_files(self._window, self._import_json))
        box.append(
            common.prefs_group(
                i18n.t("group_actions"),
                [
                    common.action_row(i18n.t("snippets_save"), save),
                    common.action_row(i18n.t("copy"), copy),
                    common.action_row(i18n.t("snippets_delete"), delete),
                    common.action_row(i18n.t("snippets_filter_go"), filter_btn),
                    common.action_row(i18n.t("snippets_export"), export_btn),
                    common.action_row(i18n.t("snippets_import"), import_btn),
                ],
            )
        )
        self._list = Gtk.ListBox()
        self._list.add_css_class("boxed-list")
        self._list.connect("row-activated", self._open_row)
        box.append(self._list)
        return common.scrolled(box)

    def _text(self) -> str:
        buf = self._body.get_buffer()
        return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)

    def _reload(self) -> None:
        common.clear_list(self._list)
        self._names: list[str] = []
        items = snippets.filter_by_tag(self._filter_tag.get_text())
        for item in items:
            self._names.append(item["name"])
            row = Gtk.ListBoxRow()
            tags = item.get("tags") or ""
            label = f"{item['name']} [{tags}]" if tags else item["name"]
            lab = Gtk.Label(label=label, xalign=0, wrap=True)
            lab.set_margin_start(10)
            lab.set_margin_end(10)
            lab.set_margin_top(6)
            lab.set_margin_bottom(6)
            row.set_child(lab)
            self._list.append(row)

    def _open_row(self, _box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        idx = row.get_index()
        if idx < 0 or idx >= len(self._names):
            return
        name = self._names[idx]
        self._name.set_text(name)
        try:
            self._body.get_buffer().set_text(snippets.get(name))
            for item in snippets.filter_by_tag(""):
                if item["name"] == name:
                    self._tags.set_text(item.get("tags") or "")
                    break
        except snippets.SnippetError as exc:
            show_toast(self._toast, str(exc), 5)

    def _save(self) -> None:
        try:
            snippets.put(self._name.get_text(), self._text(), tags=self._tags.get_text())
        except snippets.SnippetError as exc:
            show_toast(self._toast, str(exc), 5)
            return
        self._reload()
        show_toast(self._toast, i18n.t("prefs_saved"))

    def _copy(self) -> None:
        common.copy_text(self._text(), self._toast)

    def _delete(self) -> None:
        try:
            snippets.delete(self._name.get_text())
        except snippets.SnippetError as exc:
            show_toast(self._toast, str(exc), 5)
            return
        self._name.set_text("")
        self._body.get_buffer().set_text("")
        self._reload()
        show_toast(self._toast, "OK")

    def _export_json(self) -> None:
        text = snippets.export_json()
        compat.save_file(self._window, "snippets.json", lambda dest: dest.write_text(text, encoding="utf-8"))

    def _import_json(self, paths: list[Path]) -> None:
        if not paths:
            return
        try:
            payload = paths[0].read_text(encoding="utf-8")
            added = snippets.import_json(payload)
        except (OSError, snippets.SnippetError) as exc:
            show_toast(self._toast, str(exc), 6)
            return
        self._reload()
        show_toast(self._toast, f"{added} OK")
