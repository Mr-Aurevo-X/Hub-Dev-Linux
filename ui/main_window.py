# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from core import cross_hub, i18n, settings as app_settings, updater
from core.loopback.registry import migrate_from_localdock
from ui import compat
from ui.helpers import show_toast
from ui.nav import NavSidebar, page_titles
from ui.pages.env_page import EnvPage
from ui.pages.json_page import JsonPage
from ui.pages.loopback import LoopbackPage
from ui.pages.lua_page import LuaPage
from ui.pages.snippets_page import SnippetsPage
from ui.pages.textdiff_page import TextDiffPage
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
        self._toast = Adw.ToastOverlay()
        self._stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self._pages: dict[str, Any] = {}
        self._nav_sidebar = NavSidebar(
            settings=self._settings,
            on_page_selected=self._on_nav_page_selected,
            on_groups_changed=self._on_nav_groups_changed,
        )
        last_page = app_settings.coerce_page(self._settings.get("last_page"))
        self._ensure_page(last_page)
        titles = page_titles()
        layout = build_main_layout(
            self._nav_sidebar.widget,
            self._stack,
            page_title=titles.get(last_page, last_page),
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
        compat.set_bin_child(self._toast, layout.widget)
        compat.set_bin_child(self, self._toast)
        self._show_page(last_page, persist=False)
        self._logged_mapped = False
        self.connect("map", self._on_window_mapped)
        if not app_settings.needs_language_prompt(self._settings):
            GLib.timeout_add(2000, self._maybe_check_updates)

    def _on_window_mapped(self, *_args: object) -> None:
        if self._logged_mapped:
            return
        self._logged_mapped = True
        if app_settings.needs_language_prompt(self._settings):
            GLib.idle_add(self._prompt_language)
        else:
            GLib.idle_add(self._consume_pending_textdiff)

    def _prompt_language(self) -> bool:
        if not app_settings.needs_language_prompt(self._settings):
            return False

        def on_resp(response: str) -> None:
            if response not in {"fr", "en"}:
                return
            self._apply_language(response)
            GLib.idle_add(self._consume_pending_textdiff)
            GLib.timeout_add(400, self._maybe_check_updates)

        compat.present_alert(
            self,
            i18n.t("welcome_lang"),
            i18n.t("welcome_lang_body"),
            [("fr", "Français"), ("en", "English")],
            suggested="fr",
            on_response=on_resp,
        )
        return False

    def _consume_pending_textdiff(self) -> bool:
        paths = cross_hub.read_pending_textdiff()
        if not paths:
            return False
        cross_hub.clear_pending_textdiff()
        page = self._ensure_page("textdiff")
        receive = getattr(page, "receive_paths", None)
        if callable(receive):
            receive(paths)
        self._show_page("textdiff")
        show_toast(self._toast, i18n.t("pending_textdiff"), 4)
        return False

    def _factory(self, key: str) -> Any:
        if key == "loopback":
            return LoopbackPage(self, self._toast)
        if key == "textdiff":
            return TextDiffPage(self, self._toast)
        if key == "snippets":
            return SnippetsPage(self, self._toast)
        if key == "json":
            return JsonPage(self)
        if key == "env":
            return EnvPage(self)
        if key == "lua":
            return LuaPage(self)
        raise KeyError(key)

    def _ensure_page(self, key: str) -> Any:
        page = self._pages.get(key)
        if page is not None:
            return page
        page = self._factory(key)
        self._pages[key] = page
        widget = page.widget if hasattr(page, "widget") else page
        self._stack.add_named(widget, key)
        return page

    def _on_nav_page_selected(self, key: str) -> None:
        self._ensure_page(key)
        self._show_page(key)

    def _on_nav_groups_changed(self, expanded: dict[str, bool]) -> None:
        self._settings["nav_groups_expanded"] = expanded
        app_settings.save_settings(self._settings)

    def _show_page(self, key: str, *, persist: bool = True) -> None:
        self._ensure_page(key)
        self._stack.set_visible_child_name(key)
        titles = page_titles()
        self._layout.set_page_title(titles.get(key, key))
        if persist:
            self._settings["last_page"] = key
            app_settings.save_settings(self._settings)
        self._nav_sidebar.select_page(key, notify=False)

    def _apply_language(self, lang: str) -> None:
        i18n.set_language(lang)
        self._settings["language"] = lang
        self._settings["language_chosen"] = True
        app_settings.save_settings(self._settings)
        self._nav_sidebar.relabel()
        current = self._stack.get_visible_child_name() or "loopback"
        titles = page_titles()
        self._layout.set_page_title(titles.get(current, current))

    def _save_prefs(self, snapshot: dict[str, Any]) -> None:
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
