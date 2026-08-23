#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Hub Dev — GTK 4 hub."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.display_env import apply_safe_display_env

apply_safe_display_env()

import gi  # noqa: E402

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib  # noqa: E402

if os.environ.get("GDK_BACKEND") == "x11":
    try:
        Gdk.set_allowed_backends("x11")
    except Exception:  # noqa: BLE001
        pass

from ui_kit.bootstrap import ensure_ui_kit_on_path  # noqa: E402

ensure_ui_kit_on_path(_ROOT)

from core import i18n, settings as app_settings  # noqa: E402
from core.migrate import run_first_launch_migration  # noqa: E402
from ui.main_window import MainWindow  # noqa: E402


class HubApp(Adw.Application):
    def __init__(self) -> None:
        flags = getattr(Gio.ApplicationFlags, "NON_UNIQUE", None) or Gio.ApplicationFlags.DEFAULT_FLAGS
        super().__init__(application_id="org.mraurevox.HubDev", flags=flags)
        self._window: MainWindow | None = None

    def do_activate(self) -> None:  # noqa: N802
        style = Adw.StyleManager.get_default()
        style.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        from ui_kit.theme import apply_theme

        apply_theme(config_app_id="hub-dev")
        run_first_launch_migration()
        cfg = app_settings.load_settings()
        i18n.set_language(str(cfg.get("language") or "fr"))
        if self._window is None:
            self._window = MainWindow(application=self)
            self.add_window(self._window)
        self._window.present()


def main(argv: list[str] | None = None) -> int:
    return HubApp().run(argv or sys.argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
