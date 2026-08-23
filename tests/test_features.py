# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from core import envutil


def test_parse_and_format_env() -> None:
    data = envutil.parse_env("A=1\n# comment\nB=two\n")
    assert data == {"A": "1", "B": "two"}
    assert envutil.format_env(data) == "A=1\nB=two\n"


def test_nav_registry() -> None:
    from ui.nav import validate_nav_registry

    validate_nav_registry()
