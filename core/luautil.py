# SPDX-License-Identifier: GPL-3.0-or-later
"""Lua pretty-print and syntax check. Never executes user Lua."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class _ScanState:
    in_short_string: bool = False
    string_quote: str = ""
    in_long_string: bool = False
    in_block_comment: bool = False
    long_level: int = 0


def _long_open_at(text: str, index: int) -> int | None:
    if index >= len(text) or text[index] != "[":
        return None
    cursor = index + 1
    while cursor < len(text) and text[cursor] == "=":
        cursor += 1
    if cursor < len(text) and text[cursor] == "[":
        return cursor - index - 1
    return None


def _find_long_close(text: str, index: int, level: int) -> int | None:
    closer = "]" + ("=" * level) + "]"
    pos = text.find(closer, index)
    if pos < 0:
        return None
    return pos + len(closer)


def _scan_line(line: str, state: _ScanState) -> tuple[int, int, int]:
    """Count function/{ opens and end/} closes outside strings. Updates state."""
    index = 0
    length = len(line)
    opens = 0
    closes = 0
    leading_closes = 0
    only_ws = True

    while index < length:
        if state.in_long_string or state.in_block_comment:
            end = _find_long_close(line, index, state.long_level)
            if end is None:
                return leading_closes, opens, closes
            index = end
            state.in_long_string = False
            state.in_block_comment = False
            only_ws = False
            continue

        if state.in_short_string:
            char = line[index]
            if char == "\\" and index + 1 < length:
                index += 2
                continue
            if char == state.string_quote:
                state.in_short_string = False
            index += 1
            continue

        char = line[index]
        if char == "-" and index + 1 < length and line[index + 1] == "-":
            long_level = _long_open_at(line, index + 2)
            if long_level is not None:
                state.in_block_comment = True
                state.long_level = long_level
                index += 2 + 2 + long_level
                only_ws = False
                continue
            break

        long_level = _long_open_at(line, index)
        if long_level is not None:
            state.in_long_string = True
            state.long_level = long_level
            index += 2 + long_level
            only_ws = False
            continue

        if char in {'"', "'"}:
            state.in_short_string = True
            state.string_quote = char
            index += 1
            only_ws = False
            continue

        if char.isspace():
            index += 1
            continue

        if char == "{":
            opens += 1
            only_ws = False
            index += 1
            continue

        if char == "}":
            closes += 1
            if only_ws:
                leading_closes += 1
            only_ws = False
            index += 1
            continue

        if char.isalpha() or char == "_":
            cursor = index + 1
            while cursor < length and (line[cursor].isalnum() or line[cursor] == "_"):
                cursor += 1
            word = line[index:cursor]
            if word == "function":
                opens += 1
            elif word == "end":
                closes += 1
                if only_ws:
                    leading_closes += 1
            only_ws = False
            index = cursor
            continue

        only_ws = False
        index += 1

    return leading_closes, opens, closes


def format_lua(text: str) -> str:
    if not text:
        return ""
    state = _ScanState()
    indent = 0
    lines: list[str] = []
    for line in text.splitlines():
        inside = state.in_long_string or state.in_block_comment or state.in_short_string
        leading, opens, closes = _scan_line(line, state)
        if inside:
            lines.append(line)
            continue
        indent = max(0, indent - leading)
        lines.append(("  " * indent) + line.strip())
        indent = max(0, indent + opens - (closes - leading))
    result = "\n".join(lines)
    if text.endswith("\n"):
        result += "\n"
    return result


def _check_with_luac(luac: str, text: str) -> list[str]:
    tmp = tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8")
    try:
        tmp.write(text)
        tmp.close()
        proc = subprocess.run(
            [luac, "-p", tmp.name],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    if proc.returncode == 0:
        return []
    message = (proc.stderr or proc.stdout or "").strip()
    return [message] if message else ["syntax error"]


def _check_with_scanner(text: str) -> list[str]:
    state = _ScanState()
    depth = 0
    errors: list[str] = []
    for lineno, line in enumerate(text.splitlines() or [""], start=1):
        _leading, opens, closes = _scan_line(line, state)
        depth += opens - closes
        if depth < 0:
            errors.append(f"line {lineno}: unexpected '}}'")
            depth = 0
    if state.in_short_string or state.in_long_string:
        errors.append("unclosed string")
    if depth > 0:
        errors.append("unbalanced '{'")
    return errors


def check_syntax(text: str) -> list[str]:
    luac = shutil.which("luac")
    if luac:
        try:
            return _check_with_luac(luac, text)
        except OSError:
            pass
    return _check_with_scanner(text)
