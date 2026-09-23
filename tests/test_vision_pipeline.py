"""Smoke tests for the describe pipeline: it returns what the model returned.

Both the routing decision and the model call are stubbed, so these tests pass on a fresh
checkout with **no config, no keys, and no running model** — they exercise the real
``_describe`` entry point with only its two live edges replaced.

They do NOT assert a particular output language: the pipeline passes through whatever the
model returns, including non-English. Asking for English is a prompt instruction, not a
filter (see the README, "Language of descriptions").
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

import plugin_api  # noqa: E402


def _make_png() -> bytes:
    img = Image.new("RGB", (100, 100), (0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def test_frame() -> bytes:
    return _make_png()


def test_vision_description_passes_through_model_output(
    test_frame: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_describe() returns whatever _describe_with_model() returns, including
    non-English text — there is no English gate in the pipeline."""

    def mock_describe(png: bytes, route: dict) -> str:
        del png, route
        return (
            "此为屏幕截图，显示一个带有多个选项卡的浏览器窗口，以及一个框架内的图像。"
        )

    monkeypatch.setattr(plugin_api, "_describe_with_model", mock_describe)
    monkeypatch.setattr(
        "plugin_api._route",
        lambda session_id="": {
            "provider": "test",
            "model": "hermes-lang-test",
            "base_url": "http://127.0.0.1:1",
            "supports_vision": True,
        },
    )

    description = plugin_api._describe(test_frame)
    desc = description.strip()

    assert desc, "description must not be empty"
    assert len(desc) >= 10, f"Expected a real sentence, got {desc!r}"
    # The pipeline does NOT reject non-English — it passes through.
    assert "此为屏幕截图" in desc


def test_vision_description_rejects_no_model_configured(
    test_frame: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When nothing in the session can accept images, _describe() raises
    clearly rather than silently doing nothing."""

    monkeypatch.setattr(
        "plugin_api._route",
        lambda session_id="": {"provider": "test", "model": "", "base_url": "", "supports_vision": False},
    )

    with pytest.raises(RuntimeError, match="no model configured"):
        plugin_api._describe(test_frame)


def test_vision_description_rejects_no_vision_support(
    test_frame: bytes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the configured model cannot accept images, _describe() raises
    _NeedsVisionModel so the caller can offer a different model."""

    monkeypatch.setattr(
        "plugin_api._route",
        lambda session_id="": {
            "provider": "test",
            "model": "text-only-model",
            "base_url": "http://127.0.0.1:1",
            "supports_vision": False,
        },
    )

    with pytest.raises(plugin_api._NeedsVisionModel):
        plugin_api._describe(test_frame)
