# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from core import envutil, i18n
from core import settings as app_settings


def test_parse_and_format_env() -> None:
    data = envutil.parse_env("A=1\n# comment\nB=two\n")
    assert data == {"A": "1", "B": "two"}
    assert envutil.format_env(data) == "A=1\nB=two\n"


def test_coerce_page_aliases() -> None:
    assert app_settings.PAGE_KEYS == ("loopback", "textdiff", "snippets", "json", "env", "lua")
    assert app_settings.coerce_page("json_stub") == "json"
    assert app_settings.coerce_page("env_stub") == "env"
    assert app_settings.coerce_page("json") == "json"
    assert app_settings.coerce_page("env") == "env"
    assert app_settings.coerce_page("lua") == "lua"
    assert app_settings.coerce_page("unknown") == "loopback"


def test_nav_registry() -> None:
    from ui.nav import nav_pages, validate_nav_registry

    validate_nav_registry()
    keys = tuple(key for key, _label in nav_pages())
    assert set(keys) == set(app_settings.PAGE_KEYS)
    assert "json" in keys
    assert "env" in keys
    assert "lua" in keys
    assert "json_stub" not in keys
    assert "env_stub" not in keys


def test_i18n_json_env_title_aliases() -> None:
    i18n.set_language("fr")
    assert i18n.t("json_title") == "JSON"
    assert i18n.t("env_title") == ".env"
    assert i18n.t("lua_title") == "Lua"
    assert i18n.t("json_stub_title") == "JSON"
    assert i18n.t("env_stub_title") == ".env"


def test_format_lua_indents_function_and_table() -> None:
    from core.luautil import format_lua

    out = format_lua("function foo()\nreturn {a=1}\nend\n")
    lines = out.splitlines()
    ret = next(line for line in lines if "return" in line)
    end = next(line for line in lines if line.strip() == "end")
    assert ret.startswith((" ", "\t"))
    assert not end.startswith((" ", "\t"))


def test_format_lua_does_not_break_strings() -> None:
    from core.luautil import format_lua

    src = 's = "function { end }"\n'
    out = format_lua(src)
    assert '"function { end }"' in out


def test_check_syntax_ok() -> None:
    from core.luautil import check_syntax

    assert check_syntax("return { a = 1 }") == []


def test_check_syntax_reports_unbalanced() -> None:
    from core.luautil import check_syntax

    errors = check_syntax("return { a = 1")
    assert isinstance(errors, list)
    assert errors


def test_history_append_load(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from core.loopback import history

    history.append("start", "demo-app")
    items = history.load()
    assert len(items) == 1
    assert items[0]["event"] == "start"
    assert items[0]["detail"] == "demo-app"
    assert items[0]["ts"]


def test_history_caps_at_200(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from core.loopback import history

    for index in range(205):
        history.append("scan", str(index))
    items = history.load()
    assert len(items) == 200
    assert items[0]["detail"] == "5"
    assert items[-1]["detail"] == "204"
