# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import pytest

from core.loopback import spawn
from core.loopback.ports import PortRow
from core.loopback.registry import AppEntry, Registry


def test_stop_kills_host_port_without_popen(monkeypatch) -> None:
    killed: list[tuple[int, bool]] = []
    rows = [PortRow(port=4180, pid=4242, process_name="node", addr="127.0.0.1", is_loopback=True)]

    def list_ports() -> list[PortRow]:
        return list(rows)

    def fake_kill(pid: int, *, force: bool = False) -> None:
        killed.append((pid, force))
        rows.clear()

    monkeypatch.setattr(spawn.ports, "list_loopback_ports", list_ports)
    monkeypatch.setattr(spawn.ports, "kill_pid", fake_kill)
    monkeypatch.setattr(
        Registry,
        "load",
        classmethod(
            lambda cls: Registry(
                apps=[AppEntry(id="demo", name="Demo App", cwd="/tmp", command="npm", preferred_port=4180)]
            )
        ),
    )
    spawn._running.clear()
    spawn.stop("demo")
    assert killed == [(4242, False)]


def test_stop_without_proc_or_port_raises(monkeypatch) -> None:
    monkeypatch.setattr(Registry, "load", classmethod(lambda cls: Registry(apps=[])))
    spawn._running.clear()
    with pytest.raises(RuntimeError, match="pas en cours"):
        spawn.stop("missing")


def test_pids_on_port() -> None:
    from core.loopback import ports

    rows = [
        PortRow(port=4180, pid=1, process_name="node", addr="127.0.0.1", is_loopback=True),
        PortRow(port=3000, pid=2, process_name="next", addr="127.0.0.1", is_loopback=True),
    ]
    assert ports.pids_on_port(4180, rows=rows) == [1]
    assert ports.pids_on_port(9, rows=rows) == []
