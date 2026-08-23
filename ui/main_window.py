# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from core import i18n, settings as app_settings, updater
from core.loopback.registry import migrate_from_localdock
from ui.nav import NavSidebar, page_titles
from ui.pages.loopback import LoopbackPage
from ui_kit.dialogs.update import present as present_update_dialog
from ui_kit.shell import ShellLayout, build_main_layout


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application) -> None:
        super().__init__(application=application, title=updater.app_display_name())
        self.add_css_class("uni-window")
        self.set_default_size(1100, 720)
        migrate_from_localdock()
        self._settings = app_settings.load_settings()
        i18n.set_language(str(self._settings.get("language") or "fr"))
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._pages = {"loopback": LoopbackPage(self)}
        for key, page in self._pages.items():
            self._stack.add_named(page, key)
        self._nav_sidebar = NavSidebar(
            settings=self._settings,
            on_page_selected=self._on_nav_page_selected,
            on_groups_changed=self._on_nav_groups_changed,
        )
        titles = page_titles()
        layout = build_main_layout(
            self._nav_sidebar.widget,
            self._stack,
            page_title=titles["loopback"],
            lang=i18n.language(),
        )
        layout.attach_chrome_buttons(
            self,
            on_check_updates=self._manual_check_updates,
            on_language_toggle=self._apply_language,
            current_language=i18n.language(),
            settings_snapshot=self._settings,
            current_version=updater.local_version(),
            on_settings_save=self._save_prefs,
        )
        self._layout: ShellLayout = layout
        self.set_content(layout.widget)
        self._nav_sidebar.select_page("loopback", notify=False)
        GLib.timeout_add(2000, self._maybe_check_updates)

    def _on_nav_page_selected(self, key: str) -> None:
        if key not in self._pages:
            return
        self._show_page(key)

    def _on_nav_groups_changed(self, expanded: dict[str, bool]) -> None:
        self._settings["nav_groups_expanded"] = expanded
        app_settings.save_settings(self._settings)

    def _show_page(self, key: str) -> None:
        self._stack.set_visible_child_name(key)
        titles = page_titles()
        self._layout.set_page_title(titles.get(key, key))
        self._settings["last_page"] = key
        app_settings.save_settings(self._settings)
        self._nav_sidebar.select_page(key, notify=False)

    def _apply_language(self, lang: str) -> None:
        i18n.set_language(lang)
        self._settings["language"] = lang
        app_settings.save_settings(self._settings)
        self._nav_sidebar.relabel()
        current = self._stack.get_visible_child_name() or "loopback"
        titles = page_titles()
        self._layout.set_page_title(titles.get(current, current))

    def _save_prefs(self, snapshot: dict) -> None:
        self._settings.update(snapshot)
        app_settings.save_settings(self._settings)

    def _maybe_check_updates(self) -> bool:
        info = updater.check_for_update()
        if info:
            present_update_dialog(
                self,
                "",
                updater.format_update_dialog_commands(info),
                updater.format_update_dialog_body(info),
                new_version=str(info.get("version") or "?"),
            )
        return False

    def _manual_check_updates(self) -> None:
        info = updater.check_for_update(raise_on_error=True)
        if not info:
            return
        present_update_dialog(
            self,
            "",
            updater.format_update_dialog_commands(info),
            updater.format_update_dialog_body(info),
            new_version=str(info.get("version") or "?"),
        )
