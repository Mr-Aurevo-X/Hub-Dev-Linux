# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import os

from core.loopback import toolchain


def test_prepare_env_prepends_pnpm_shim_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("PNPM_HOME", raising=False)
    monkeypatch.setattr(
        toolchain.shutil,
        "which",
        lambda cmd, path=None: "/usr/bin/npx" if cmd == "npx" and not path else None,
    )
    monkeypatch.setattr(toolchain, "extra_bin_dirs", lambda: [])
    env = toolchain.prepare_env({"PATH": "/usr/bin"}, cwd=tmp_path)
    shim = tmp_path / "cache" / "hub-dev" / "bin" / "pnpm"
    assert shim.is_file()
    assert os.access(shim, os.X_OK)
    assert str(shim.parent) in env["PATH"].split(os.pathsep)
    assert "pnpm@9" in shim.read_text(encoding="utf-8")


def test_pnpm_version_from_package_manager(tmp_path) -> None:
    (tmp_path / "package.json").write_text(
        '{"packageManager":"pnpm@9.15.0"}',
        encoding="utf-8",
    )
    assert toolchain.pnpm_version_for(tmp_path) == "9.15.0"
    assert toolchain.pnpm_version_for(tmp_path / "missing") == "9"
