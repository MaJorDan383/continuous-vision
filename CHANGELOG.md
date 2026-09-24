# Changelog

## [Unreleased]

### Injection cadence is now configurable
- **Added: `CV_VISION_INJECT_MODE`** — `on_change` (default), `always`, `on_mention`, `tool_only`.
  The injection gates were hardcoded to "inject whenever the loop is running and the reading is
  fresh", so an unchanged screen was re-sent on every turn for the life of a session, and every
  copy was persisted with its turn. `on_change` compares the *descriptions* against what that
  session was last sent (not the rendered block — its header carries the frame age, which differs
  every turn), and re-sends unchanged content after 10 minutes so a static screen is still
  re-anchored. `on_mention` waits for the user's own turn to point at the screen. Invalid values
  log a warning once and fall back to the default; the two hard gates (running + fresh) are
  unchanged in every mode.
- **Changed: the default is `on_change`, not "every turn".** Users who want the old behaviour set
  `CV_VISION_INJECT_MODE=always`.
- **Known limit: `tool_only` injects nothing in this build.** The mode is reserved for
  deployments that expose a live-view tool; this plugin registers none, so it logs a warning
  instead of pretending to work.
- **Fixed: the privacy section now discloses the transcript copy.** Descriptions were documented
  as persisting in `log.jsonl`, but an injected block rides the turn's user message and the host
  stores those exact bytes in the session database (`api_content` sidecar), so deleting
  `log.jsonl` does not remove them from your sessions.

### Release hardening (before the first public release)
- **Fixed: unloading the plugin never stopped the watch.** The agent half registered
  `plugin_unload` as a hook, but that name is not in the host's hook registry, so the callback
  was never dispatched — `hermes plugins validate` failed and a disabled plugin left its capture
  loop (and an open camera) running. It now uses `ctx.on_unload()` and asks for a stop through
  the state directory the two halves already share, because the agent half runs in a different
  process and cannot stop the backend's engine directly. The loop consumes `stop_request` on its
  next tick, releases the source, and publishes a terminal `running: false` status so context
  injection ends at once instead of at the end of the freshness window.
- **Fixed: the config table was incomplete.** `CV_PREVIEW_MAX_AGE_S` (the preview-refresh cadence)
  and `CV_VISION_MAX_WIDTH` had no row, and the intake precedence is now spelled out as
  `_vision_intake()` applies it — `CV_VISION_MAX_EDGE` (older alias `CV_VISION_MAX_WIDTH`), with
  `CV_VISION_MAX_PIXELS` taking precedence over the edge caps. Every variable the code reads is now
  in the table, and the `CV_*` variables are described as read from the backend process environment
  (not `config.yaml`).
- **Fixed: `pyproject.toml` shipped an invented author email and three dead repository URLs.**
  Email removed; URLs corrected to the real repository.
- **Fixed: `plugin.yaml` declared a `repository` key that is not in the manifest schema.** Unknown
  fields are warned about and ignored, so every load logged an unknown-field warning and the real
  repository link was never surfaced — the key is `homepage`.
- **Fixed: the README never said how to enable the plugin.** Standalone plugins load only when
  their key is in `plugins.enabled`, so a copied-in directory stays inert; the install steps now
  include `hermes plugins enable continuous-vision`.
- **Changed: the plugin is opt-in.** It captures screen content, so nothing happens until you
  enable it. (An earlier note here credited a `defaultEnabled` manifest key — no such field exists
  in the schema; the opt-in comes from `plugins.enabled`.)
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
