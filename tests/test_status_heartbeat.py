"""A status file is a claim, not proof.

The loop runs in the dashboard/serve process; the agent half that gates context injection on
`running` runs in the agent process and has only this file to go on. So the file must carry a
heartbeat, and the backend must heal the file a process that DIED left behind (a killed backend
never reaches the terminal write at the end of the loop).

No desktop session, no camera and no model are needed: these drive the engine's own publisher and
the reconciliation helper with the paths redirected into a temp dir.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

import plugin_api  # noqa: E402


@pytest.fixture
def status_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "status.json"
    monkeypatch.setattr(plugin_api, "STATUS_PATH", path)
    monkeypatch.setattr(plugin_api, "LOG_PATH", tmp_path / "log.jsonl")
    return path


def _claim(path: Path, *, running: bool = True, heartbeat: float | None = None, **extra) -> None:
    """Write the kind of status file a process leaves behind."""
    payload = {
        "running": running,
        "last_at": time.time(),
        "source_label": "Monitor 1",
        "recent": [{"description": "A terminal showing pytest output."}],
        "v": 1,
        **extra,
    }
    if heartbeat is not None:
        payload["heartbeat_at"] = heartbeat
    path.write_text(json.dumps(payload), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_every_publish_refreshes_the_heartbeat(status_file: Path) -> None:
    """The heartbeat is written on every tick, whatever the tick did."""
    engine = plugin_api._Engine()
    engine._publish()
    first = _read(status_file)
    assert first["heartbeat_at"] == pytest.approx(time.time(), abs=5), "no heartbeat on the file"
    engine._publish()
    assert _read(status_file)["heartbeat_at"] >= first["heartbeat_at"]


def test_a_live_watch_is_never_clobbered(status_file: Path) -> None:
    _claim(status_file, heartbeat=time.time())
    assert plugin_api.reconcile_stale_status() is None
    assert _read(status_file)["running"] is True


def test_a_dead_loop_is_corrected_when_the_backend_wakes(status_file: Path) -> None:
    """The bug this exists for: a killed backend leaves `running: true` on disk for good."""
    _claim(status_file, heartbeat=time.time() - (plugin_api.STATUS_HEARTBEAT_MAX_AGE_S + 5))
    corrected = plugin_api.reconcile_stale_status()
    assert corrected is not None and "gone" in corrected["error"]
    after = _read(status_file)
    assert after["running"] is False and after["stale"] is True
    # and it is recorded, not silently rewritten
    events = [json.loads(line) for line in (status_file.parent / "log.jsonl").read_text().splitlines()]
    assert any(e.get("event") == "stale_status_corrected" for e in events)


def test_a_writer_too_old_to_heartbeat_is_judged_by_the_file_mtime(status_file: Path) -> None:
    """Older writers never wrote `heartbeat_at`; their own mtime is the next best evidence."""
    _claim(status_file)  # no heartbeat_at, just written -> fresh mtime
    assert plugin_api.reconcile_stale_status() is None
    _claim(status_file)
    old = time.time() - (plugin_api.STATUS_HEARTBEAT_MAX_AGE_S + 60)
    os.utime(status_file, (old, old))
    assert plugin_api.reconcile_stale_status() is not None
    assert _read(status_file)["running"] is False


def test_a_stopped_or_unreadable_file_is_left_alone(status_file: Path) -> None:
    _claim(status_file, running=False)
    assert plugin_api.reconcile_stale_status() is None
    assert _read(status_file)["running"] is False
    status_file.write_text("{ this is not json", encoding="utf-8")
    assert plugin_api.reconcile_stale_status() is None
    assert status_file.read_text(encoding="utf-8") == "{ this is not json"
    status_file.unlink()
    assert plugin_api.reconcile_stale_status() is None


def test_a_crash_inside_the_loop_still_publishes_a_terminal_state(
    status_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bug seen live: a loop died and left `running: true` on disk for twenty hours."""
    engine = plugin_api._Engine()
    monkeypatch.setattr(plugin_api, "release_camera", lambda: None)

    def boom() -> None:
        raise RuntimeError("the vision model returned garbage")

    monkeypatch.setattr(engine, "_run", boom)
    engine._run_guarded()  # must not raise out of the thread boundary
    after = _read(status_file)
    assert after["running"] is False and after["heartbeat_at"] is not None
    assert "garbage" in after["error"]
    events = [
        json.loads(line) for line in (status_file.parent / "log.jsonl").read_text().splitlines()
    ]
    crashed = [e for e in events if e.get("event") == "loop_crashed"]
    assert crashed and "RuntimeError" in crashed[-1]["error"] and crashed[-1]["trace"]


def test_a_failing_release_does_not_eat_the_terminal_write(
    status_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Releasing the source is best-effort; the truth about the loop is not."""
    engine = plugin_api._Engine()
    monkeypatch.setattr(engine, "_run", lambda: None)

    def no_camera() -> None:
        raise OSError("no camera to release")

    monkeypatch.setattr(plugin_api, "release_camera", no_camera)
    engine._run_guarded()
    assert _read(status_file)["running"] is False
