# 🎵 AARPO Metronome

A cross-platform **terminal metronome** with a full TUI (built on
[Textual](https://textual.textualize.io/)). Inspired by the
[Violinspiration online metronome](https://violinspiration.com/free-online-metronome/).

```
        TEMPO (BPM)              Time signature   4/4   (4 beats per bar)
       ┌─┐ ┌─┐ ┌─┐               Subdivision      1×    Quarter notes
       │ │ │ │ │ │  ◀── big      Accent           ON    beats: 1
       └─┘ └─┘ └─┘   readout
         Allegro

   20 ━━━━━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━ 300

              · • ● ✦ ● • ·       ◀── sonar click pulse (expands + fades per click)

        ◆     ●     ●     ●      ◀── live beat visual (down-beat accented)
        ▮  ▯  ▯  ▯                ◀── subdivision strip
```

## Features

- 🥁 **Tempo control** — 20–300 BPM, fine (±1) and coarse (±5 / ±10) steps
- 🎼 **Italian tempo markings** — Largo, Andante, Allegro, Presto…
- 🔔 **Optional accents** — emphasise the down-beat, or toggle the accent on *any*
  beat with the number keys
- 🎵 **Subdivisions** — quarter / eighth / triplet / sixteenth clicks per beat
- 👆 **Tap tempo** — tap a key to set the BPM by feel
- 💾 **Presets** — save and recall your favourite setups
- 🌈 **Animated visuals** — a **sonar-style click pulse** (expanding, fading rings
  colour-coded per accent / beat / subdivision) plus pulsing beat indicators and a
  live subdivision strip
- 🔈 **Bundled click sounds** — synthesized on first run, no external files needed
- 🖥️ **Runs anywhere** — Windows, macOS, Linux

## Quick start — double-click to launch 🖱️

No commands needed. A terminal UI needs a terminal window, so each launcher opens
one for you and runs the app inside it. (Python 3 must be installed once — see
[Requirements](#requirements).)

| OS          | Double-click this                | Notes                                                            |
|-------------|----------------------------------|-----------------------------------------------------------------|
| **macOS**   | `AARPO Metronome.command`        | Opens Terminal automatically. First time: right-click → **Open** to clear the Gatekeeper warning. |
| **Windows** | `AARPO Metronome.bat`            | Opens a console window and runs.                                 |
| **Ubuntu/Linux** | run `./install-linux.sh` once | Adds a **AARPO Metronome** icon to your apps menu and Desktop. Then launch it like any app. (Or double-click `start-linux.sh`.) |

> First launch creates a local `.venv` and installs dependencies automatically;
> it takes a few seconds. Every launch after that is instant.

## Quick start — from a terminal

**macOS / Linux**
```bash
./run.sh
```

**Windows**
```bat
run.bat
```

### Run it as a Python module (if you prefer)
```bash
pip install -r requirements.txt
python -m aarpo_metronome
```

## Controls

| Key            | Action                                  |
|----------------|-----------------------------------------|
| `Space`        | Start / stop                            |
| `↑` / `↓`      | BPM ± 1                                 |
| `←` / `→`      | BPM ± 5                                 |
| `PgUp`/`PgDn`  | BPM ± 10                                |
| `t`            | Tap tempo                               |
| `b`            | Cycle beats per bar (1–12)              |
| `v`            | Cycle subdivision (quarter→sixteenth)   |
| `a`            | Toggle accents on/off                   |
| `1`–`9`        | Toggle the accent on that beat          |
| `s`            | Save current setup as a preset          |
| `l`            | Load / cycle through saved presets      |
| `r`            | Reset to defaults                       |
| `q`            | Quit                                    |

Presets are stored in `~/.aarpo_metronome/presets.json`.

## Build a standalone binary (no Python needed by end users)

Build **once per OS**, then the resulting file runs natively with nothing else
installed. PyInstaller can't cross-compile, so build on each OS you want to ship to.

**One-double-click build:**

| OS          | Double-click            | Output                        |
|-------------|-------------------------|-------------------------------|
| **macOS**   | `build-mac.command`     | `dist/aarpo-metronome`        |
| **Windows** | `build-windows.bat`     | `dist/aarpo-metronome.exe`    |
| **Linux**   | `./build-linux.sh`      | `dist/aarpo-metronome`        |

Or from a terminal:
```bash
pip install -r requirements.txt pyinstaller
python build.py
```

The output in `dist/` bundles Python, all dependencies, and the click sounds into a
single file. Ship just that file — double-click it (Windows/macOS) or run
`./dist/aarpo-metronome` and it works out of the box.

> **CPU note (macOS):** the binary matches the Mac it's built on — build on Apple
> Silicon for M-series, on Intel for Intel Macs.

> **Verified:** the Linux binary was tested from a clean environment with no Python
> on PATH and rendered the full UI with zero errors.

## How it works

- **`engine.py`** — a dedicated timing thread with an absolute-time, drift-corrected
  scheduler, so the beat stays steady even while the UI repaints.
- **`audio.py`** — low-latency playback via `pygame.mixer`, with an automatic
  *silent visual-only* fallback if no audio device is available.
- **`assets.py`** — generates the click sounds with the standard library (no binary
  assets committed).
- **`app.py`** — the Textual UI and keybindings, including the `ClickVisualizer`
  sonar pulse (a ~30 fps frame timer expands and fades a ring on every click) and
  the `BeatVisualizer` beat row.

All Python lives in the `aarpo_metronome/` package; run it with `python -m aarpo_metronome`.

## Requirements

- Python 3.9+
- [`textual`](https://pypi.org/project/textual/), [`pygame`](https://pypi.org/project/pygame/)
  (installed automatically by the launchers)

## License

MIT
