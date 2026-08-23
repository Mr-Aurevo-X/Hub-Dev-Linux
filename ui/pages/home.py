# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

from core import i18n


class HomePage(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self._title = Gtk.Label(label=i18n.t("home_title"), xalign=0)
        self._title.add_css_class("title-1")
        self._lede = Gtk.Label(label=i18n.t("home_lede"), xalign=0, wrap=True)
        self._lede.add_css_class("dim-label")
        self.append(self._title)
        self.append(self._lede)

    def refresh_language(self) -> None:
        self._title.set_label(i18n.t("home_title"))
        self._lede.set_label(i18n.t("home_lede"))
