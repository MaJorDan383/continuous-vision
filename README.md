# Continuous Vision

Continuous Vision is a Hermes plugin that keeps a live view of your screen, windows, and cameras, and feeds fresh descriptions to Hermes before each response. It turns your desktop into a persistent context source so Hermes can see what's on your screen, which window is focused, and what your cameras see — without you having to screenshot every time.

## Features

- **Monitor capture** — grabs frames from all connected displays via DWM
- **Window capture** — captures specific applications by window handle
- **Camera capture** — enumerates cameras (DSHOW) and grabs frames
- **Vision routing** — sends frames to the configured vision model automatically
- **Pre-LLM context injection** — adds live descriptions to every assistant response via the `pre_llm_call` hook
- **Desktop pane** — shows a live preview with monitor/window/camera picker, vision model candidates, and pin support

## Installation

Source, issues and releases: **https://github.com/MaJorDan383/continuous-vision**

### Requirements
- **Windows 10/11** (the capture stack uses Win32/DWM/DirectShow — no Linux/macOS support)
- Python 3.9+
- Hermes **0.21.4 or newer** (declared as `requires_hermes` in `plugin.yaml`; the loader refuses
  to load the plugin rather than half-work on an older tree)
- Python packages `opencv-python-headless`, `Pillow`, `openai` (declared in `pyproject.toml`).
  Hermes offers to install a plugin's declared dependencies when you enable it; if capture
  reports a missing dependency instead, install them into the environment that runs Hermes:
  `pip install opencv-python-headless Pillow openai`

### Quick install
Copy the plugin directory into your Hermes plugins folder:

**PowerShell (Windows):**
```powershell
Copy-Item -Recurse continuous-vision "$env:LOCALAPPDATA\hermes\plugins\continuous-vision"
```

**Git Bash / MSYS:**
```bash
cp -r continuous-vision/ "$LOCALAPPDATA/hermes/plugins/continuous-vision/"
```

If you run Hermes with a custom `HERMES_HOME`, use `$HERMES_HOME/plugins/continuous-vision` instead.

## Configuration

The plugin reads environment variables for tuning. They are read from the process that runs
the Hermes backend (the desktop app inherits your user environment):

| Variable | Default | Description |
|----------|---------|-------------|
| `CV_VISION_TIMEOUT_S` | `60` | Timeout (seconds) for a single vision API call |
| `CV_VISION_ATTEMPTS` | `2` | Attempts per frame before reporting failure |
| `CV_VISION_MAX_WIDTH` | `1024` | Max width of the frame sent to the model |
| `CV_VISION_SQUARE` | _(unset)_ | Force a square intake (auto-enabled for CLIP-style encoders) |
| `CV_VISION_PROMPT` | _(built-in)_ | Prompt sent with each frame for description |
| `CV_PREVIEW_MAX_AGE_S` | `6.0` | How stale the frame behind the pane preview may get while nothing moves (matches the pane's own 6s poll) |
| `CV_SOURCE_FAILURE_LIMIT` | `3` | Consecutive capture failures before the watch stops |
| `CV_CAMERA_MAX_INDEX` | `4` | Highest DirectShow camera index to probe |
| `CV_CAMERA_CACHE_S` | `600` | Seconds the enumerated camera list stays cached |
| `CV_CAMERA_PROBE_TIMEOUT_S` | `5.0` | Timeout (seconds) for detecting one camera |
| `CV_CAMERA_PROBE_WAVE` | `2` | Camera probe waves before giving up |

Choosing the vision model is **not** an environment variable: pin it from the desktop pane,
which writes `vision_model.json` into the plugin's state directory. An empty pin restores
automatic routing to whatever model the live session is running.

## Usage

The plugin loads with Hermes but **never picks a source for you**: watching starts only when you
choose a display, window, or camera in the desktop pane. The pane shows:

1. **Monitor picker** — click a monitor to preview its frame
2. **Window picker** — select an application window to capture
3. **Camera picker** — switch between connected cameras
4. **Vision candidates** — model suggestions based on intake size
5. **Pin button** — lock a specific vision model for the session
6. **Status** — live status of the capture engine, frame count, source info

Once a source is selected, descriptions are injected into Hermes context before each response,
giving the assistant a live view of your screen.

## Security & Privacy

This plugin captures screen content and enumerates window titles. Key facts:

- **The plugin's routes are served by the Hermes dashboard** at
  `/api/plugins/continuous-vision/*`, so they are reachable wherever that dashboard is
  reachable. Access control is inherited from the dashboard's own auth and binding: if the
  dashboard is reachable at an address, these routes are reachable there too. Do not expose the
  Hermes dashboard to an untrusted network while watching a source.
- **Do not expose the Hermes dashboard to an untrusted network while watching a source.** Treat
  a running watch as screen-sharing: whatever is in the watched region is readable through the
  preview and status routes.
- **Window titles and screen content are visible** to anything that can reach the dashboard.
- **Camera access is opt-in** — a camera is opened only when explicitly selected, and the
  device is released on stop so its LED does not stay lit.
- **Descriptions persist on disk** — `log.jsonl` in the plugin's state
  directory keeps recent descriptions. Delete it to clear that history.
- **Frames leave this machine.** Each changed frame is encoded and sent to whichever
  vision-capable model the live session is running, with the built-in prompt. On a cloud
  provider that is a third-party API. Nothing is captured or sent while no source is selected,
  and stopping the watch ends it immediately.
- **Every described frame is a model call** — billed and rate-limited like any other call on
  that model. A busy screen at a short interval can mean hundreds of calls an hour; raise the
  interval or pin a cheaper vision model if that matters to you.
- **A watching session costs more tokens per turn.** While the watch is running and the newest
  description is under 90 seconds old, up to ~1200 characters are injected into the turn.

## Language of descriptions

Frames are sent to the session's vision-capable model with a prompt asking for a concise
**English** description. That is a prompt instruction, not a filter: the pipeline stores and
injects whatever the model returns, including non-English text
(`tests/test_vision_pipeline.py::test_vision_description_passes_through_model_output` asserts
exactly that pass-through). If descriptions arrive in another language, the model or the prompt
(`CV_VISION_PROMPT`) is the thing to change — the plugin will not silently drop or translate a
response.

## License

MIT License. See the `LICENSE` file for details.

## Development

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
