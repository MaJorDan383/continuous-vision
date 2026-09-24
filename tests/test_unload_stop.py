"""The unload path crosses two processes, so it crosses two modules.

The plugin's agent half (``__init__.py``) is unloaded inside Hermes' process; the capture loop
runs in the plugin's backend (``dashboard/plugin_api.py``). Neither can call into the other, so
the stop travels as a file in the state directory they share. These tests drive the real writer
and the real consumer rather than a stand-in.

Not covered here: real frame capture, opening/releasing a camera, and the pane. Those need a
live Windows desktop session.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR / "dashboard"))

import plugin_api  # noqa: E402  (the runtime puts dashboard/ on the path the same way)

_spec = importlib.util.spec_from_file_location("continuous_vision_agent_half", PLUGIN_DIR / "__init__.py")
cv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cv)


@pytest.fixture
def shared_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Both halves pointed at one throwaway state directory."""
    stop = tmp_path / "stop_request"
    monkeypatch.setattr(cv, "_STATE_DIR", tmp_path)
    monkeypatch.setattr(cv, "_STOP_REQUEST", stop)
    monkeypatch.setattr(plugin_api, "STOP_REQUEST_PATH", stop)
    monkeypatch.setattr(plugin_api, "STATUS_PATH", tmp_path / "status.json")
    monkeypatch.setattr(plugin_api, "LOG_PATH", tmp_path / "log.jsonl")
    return stop


def test_the_request_is_consumed_exactly_once(shared_state: Path) -> None:
    assert plugin_api._consume_stop_request() is False, "nothing is outstanding to begin with"
    cv.on_unload()  # the agent half is unloaded
    assert shared_state.exists()
    assert plugin_api._consume_stop_request() is True
    assert not shared_state.exists(), "the request is consumed, not left behind"
    assert plugin_api._consume_stop_request() is False, "a stale request must not stop a later watch"


def test_the_loop_honours_the_request_without_capturing_a_frame(
    shared_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard sits at the top of the loop, before any capture — so this test needs no
    source, no camera and no model, and still exercises the real loop body plus the wrapper the
    thread actually runs (`_run_guarded`, which owns the terminal write on every exit path)."""
    monkeypatch.setattr(plugin_api, "release_camera", lambda: None)  # nothing was opened
    cv.on_unload()
    engine = plugin_api._Engine()
    engine._run_guarded()  # returns as soon as it sees the request

    assert engine._stop.is_set()
    assert "unloaded" in engine.last_error
    assert engine._thread is None, "the loop must not have opened a capture source"

    terminal = json.loads((shared_state.parent / "status.json").read_text(encoding="utf-8"))
    assert terminal["running"] is False, "a stopped watch must not keep injecting context"
