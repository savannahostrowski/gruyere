import importlib
import re
from contextlib import contextmanager
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from readchar import key
from rich.console import Console

from gruyere.main import Process


@pytest.fixture
def cli_session(monkeypatch):
    """Drive real key handlers and refreshes without terminal or process I/O."""
    module = importlib.import_module("gruyere.main")
    processes = [
        Process(101, 1080, "alice", "proxy", "proxy"),
        Process(102, 3000, "bob", "web", "web"),
    ]
    monkeypatch.setattr(module, "get_processes", lambda: processes.copy())
    monkeypatch.setattr(
        module, "kill_process", lambda pid: pytest.fail("Unexpected kill")
    )
    monkeypatch.setattr(module, "Console", lambda: Console(file=StringIO()))
    monkeypatch.setattr(module, "_clear_screen", lambda: None)

    live = SimpleNamespace(renderable=None)
    live.update = lambda renderable: setattr(live, "renderable", renderable)

    @contextmanager
    def open_live(renderable, **kwargs):
        live.update(renderable)
        yield live

    monkeypatch.setattr(module, "Live", open_live)
    refresh_loops = []

    def make_thread(*, target, daemon):
        refresh_loops.append(target)
        return SimpleNamespace(start=lambda: None)

    monkeypatch.setattr(module, "threading", SimpleNamespace(Thread=make_thread))
    clock = SimpleNamespace(now=0.0, sleep=None)
    clock.time = lambda: clock.now
    monkeypatch.setattr(module, "time", clock)

    class RefreshDone(Exception):
        pass

    def run(keys, **filters):
        keys = iter(keys)
        views = []

        def capture():
            output = StringIO()
            Console(file=output, width=160).print(live.renderable)
            views.append(output.getvalue())

        def readkey():
            capture()
            ch = next(keys)
            while ch == "refresh":
                clock.now += 3.0
                clock.sleep = Mock(side_effect=[None, RefreshDone])
                with pytest.raises(RefreshDone):
                    refresh_loops[-1]()
                capture()
                ch = next(keys)
            return ch

        monkeypatch.setattr(module, "readkey", readkey)
        options = dict(
            port=None, user=None, command=None, refresh_rate=10, details=False
        )
        options.update(filters)
        with pytest.raises(StopIteration):
            module.main(**options)
        return [
            [int(port) for port in re.findall(r"Port: (\d+)", view)] for view in views
        ]

    return run


@pytest.mark.parametrize(
    "filters, initial",
    [
        ({"port": 1080}, [1080]),
        ({"user": "alice"}, [1080]),
        ({"command": "proxy"}, [1080]),
        ({"port": 1080, "user": "alice", "command": "proxy"}, [1080]),
        ({"port": 9999}, []),
    ],
)
def test_backspace_clears_cli_filters_across_refreshes(cli_session, filters, initial):
    assert cli_session([key.BACKSPACE, "refresh"], **filters) == [
        initial,
        [1080, 3000],
        [1080, 3000],
    ]


def test_backspace_on_empty_interactive_filter_clears_cli_filters(cli_session):
    assert cli_session(["/", key.BACKSPACE, "refresh"], port=1080) == [
        [1080],
        [1080],
        [1080, 3000],
        [1080, 3000],
    ]


def test_interactive_edits_keep_cli_filters_consistent_with_refreshes(cli_session):
    assert cli_session(["/", "3", "refresh", key.BACKSPACE, "refresh"], port=1080) == [
        [1080],
        [1080],
        [],
        [],
        [1080],
        [1080],
    ]


def test_leaving_unmatched_interactive_filter_preserves_cli_filters(cli_session):
    assert cli_session(["/", "z", key.ENTER, "refresh"], port=1080) == [
        [1080],
        [1080],
        [],
        [1080],
        [1080],
    ]


def test_killing_a_process_preserves_cli_filters(cli_session, monkeypatch):
    module = importlib.import_module("gruyere.main")

    def kill_process(pid):
        assert pid == 101
        remaining = [Process(102, 3000, "bob", "web", "web")]
        monkeypatch.setattr(module, "get_processes", lambda: remaining)

    monkeypatch.setattr(module, "kill_process", kill_process)
    assert cli_session([key.ENTER, "y", "refresh"], port=1080) == [
        [1080],
        [1080],
        [],
        [],
    ]
