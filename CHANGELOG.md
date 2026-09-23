# Changelog

## [Unreleased]

### Release hardening (before the first public release)
- **Fixed: unloading the plugin never stopped the watch.** The agent half registered
  `plugin_unload` as a hook, but that name is not in the host's hook registry, so the callback
  was never dispatched — `hermes plugins validate` failed and a disabled plugin left its capture
  loop (and an open camera) running. It now uses `ctx.on_unload()` and asks for a stop through
  the state directory the two halves already share, because the agent half runs in a different
  process and cannot stop the backend's engine directly. The loop consumes `stop_request` on its
  next tick, releases the source, and publishes a terminal `running: false` status so context
  injection ends at once instead of at the end of the freshness window.
- **Fixed: the documented config table disagreed with the source.**
  `CV_VISION_MAX_EDGE` and `CV_VISION_MAX_PIXELS` were documented but never read (setting them
  did nothing, silently); the real knob is `CV_VISION_MAX_WIDTH`, and `CV_PREVIEW_MAX_AGE_S` was
  undocumented. The table is now generated from what the code reads, and the `CV_*` variables are
  described as read from the backend process environment (not `config.yaml`).
- **Fixed: `pyproject.toml` shipped an invented author email and three dead repository URLs.**
  Email removed; URLs corrected to the real repository.
- **Changed: the plugin now ships off** (`defaultEnabled: false`). It captures screen content, so
  it is opt-in; an explicit user choice always wins over this default.
- **Changed: the "English verification" claim is gone.** The pipeline asks for English in the
  prompt and passes through whatever the model returns — including non-English — so the README
  now states that contract instead of claiming a gate that does not exist.
- **Changed: the privacy section discloses what the README never said** — frames go to the
  session's model (a third-party API on a cloud provider), every described frame is a billable
  call, and a watching session injects up to ~1200 characters into every turn.
- **Added: `requires_hermes: ">=0.21.4"`** so older trees fail closed instead of half-loading.
- **Added: tests** for the unload path and the injection gates (`test_unload_stop.py`,
  `test_context_injection.py`); `test_english_vision.py` became `test_vision_pipeline.py`, since
  it asserts language pass-through rather than English. `run_tests.py` no longer installs pytest
  into the running interpreter.
- `desktop/plugin.js`: hardcoded `#e5484d` fallbacks replaced by the app's `--ui-danger` token.

### Changed
- Frame diffing runs on a 64x64 fingerprint of a box-reduced copy instead of a PNG round trip, and the
  intake resize + PNG encode happen only when a frame actually changes (or the preview copy goes
  stale). Per-tick cost on a 4K display: ~290 ms -> ~115 ms of CPU.
- `/preview` serves JPEG (~3x smaller payload, much faster to encode) and reuses the encoded preview
  for an unchanged frame, so the pane's 6 s poll costs ~2 ms instead of ~30 ms.
- `/preview?hwnd=` resizes inside the capture thread at the requested width instead of encoding a
  full-size PNG and shrinking it on the way out (~4x faster per picker row).

### Fixed
- `_write_json` used a fixed `<name>.tmp` path, so two writers (the engine thread plus a probe, a CLI
  call or a second start) collided and a tick died with `PermissionError`. The temp name now carries
  pid + a random suffix, and the final swap retries briefly for readers holding the target — 8 threads
  x 25 writes: 100 collisions before, 0 after.

## [1.0.0] - 2026-09-21

### Added
- Monitor, Window, and Camera frame capture capabilities for Windows
- Live desktop pane preview with device pickers
- Intelligent vision model routing
- Pre-LLM context injection hook for live descriptions
- Language pass-through verified by test (the pipeline asks for English in the prompt and does
  not gate on it)
