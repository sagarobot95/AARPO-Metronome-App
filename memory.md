# AARPO Metronome — Developer Handoff / Memory

> Read this fully before changing anything. It captures decisions, gotchas, and
> hard-won lessons that are NOT obvious from the code. Written for the next agent
> or developer taking over.

---

## 1. What this is

**AARPO Metronome** — a cross-platform **terminal (TUI) metronome** built with
[Textual](https://textual.textualize.io/). "AARPO" is the **user's band**; the app
is branded for them (logo, colours). The user (`sagarobot95`, Ubuntu, often inside
VS Code) wanted a metronome they could send to a bandmate on **macOS**, plus a
flashy beat **visualiser** that can play a custom image/GIF.

- **Repo:** https://github.com/sagarobot95/AARPO-Metronome-App  (branch `main`)
- **Workspace path:** `/home/krissagar95/smart_metrnome app`  ← NOTE the **space**
  and the **typo** ("metrnome"). Quote paths everywhere. The Python package is
  correctly named `aarpo_metronome`.
- **Git auth:** push works via an **SSH key already on the machine**
  (`~/.ssh/github_id_ed25519`, configured in `~/.ssh/config` for github.com, authed
  as `sagarobot95`). The remote `origin` is the **SSH** URL
  (`git@github.com:...`). There is **no** `gh` CLI, no token, no credential helper.
  Just `git push origin main`.

---

## 2. Tech stack & dependencies

- **Python 3.9+** (dev machine has 3.12). Runtime deps in `requirements.txt` /
  `pyproject.toml`:
  - `textual` — the TUI framework
  - `pygame` — low-latency audio (click playback)
  - `pillow` — image/GIF loading & processing for the visualiser
  - `textual-image` — **optional** real pixel-graphics (Kitty/iTerm2/Sixel) for the
    visualiser; falls back gracefully if absent/unsupported
- **PyInstaller** (build-only) for standalone binaries.
- A working venv already exists at `./.venv` (gitignored). Activate with
  `. .venv/bin/activate`. It also has `pyinstaller`, `cairosvg` (for test
  screenshots) installed.

---

## 3. Architecture (package `aarpo_metronome/`)

| File | Responsibility |
|------|----------------|
| `engine.py` | **Timing engine.** Dedicated daemon thread, absolute-time drift-corrected scheduler (`next_time += interval`, never `sleep(interval)`). Plays audio FIRST, then fires the UI callback, so UI work never delays a beat. Measured ~0.1ms jitter. `MIN_BPM=20`, `MAX_BPM=300`. |
| `audio.py` | **Cross-platform audio.** `PygameBackend` (preloads click WAVs, low-latency, steals channels) with automatic `SilentBackend` fallback (visual-only) if no audio device. Suppresses pygame banner + stderr. |
| `assets.py` | **Click sound generation.** Synthesizes 3 WAVs (`accent`/`beat`/`subdivision`) with stdlib `wave`+`math` (no numpy). `get_asset_dir()` resolves package `assets/` dir or `sys._MEIPASS/assets` when frozen, or a writable user dir. `visualiser_default.png` (the AARPO logo, the default visualiser image) lives here too. |
| `tempo.py` | Italian tempo markings (Largo…Prestissimo) + subdivision labels (Quarter/Eighth/Triplet/Sixteenth). `MAX_SUBDIVISIONS=4`. |
| `presets.py` | Save/load presets to `~/.aarpo_metronome/presets.json`. |
| `app.py` | **The whole TUI** (807 lines). `MetronomeApp` + two visualiser widgets. This is where ~all visualiser iteration happened. See §5. |
| `__main__.py` | `python -m aarpo_metronome` entry (relative import). |
| `launch.py` (repo root) | **PyInstaller entry** — uses ABSOLUTE import `from aarpo_metronome.app import main`. See gotcha §6. |

---

## 4. Features & keybindings

Core: BPM (20–300), Italian tempo markings, time signature (beats/bar 1–12),
subdivisions (quarter→sixteenth), per-beat accents, tap tempo, presets, two
visualisers.

| Key | Action |
|-----|--------|
| `Space` | Start/stop |
| `↑`/`↓` | BPM ±1 · `←`/`→` ±5 · `PgUp`/`PgDn` ±10 |
| `t` | Tap tempo (avg of last ~6 taps, resets after 2s gap) |
| `b` | Cycle beats/bar · `v` cycle subdivision |
| `a` | Toggle accents · `1`–`9` toggle accent on that beat |
| `i` | Cycle visualiser background: rings → AARPO default → user media → rings |
| `,` / `.` | Visualiser image dimmer / brighter (`_brightness` 0.3–1.4) |
| `s` save preset · `l` load/cycle presets · `r` reset · `q` quit |

---

## 5. The visualiser (the part that got iterated to death)

There are TWO widgets in `app.py`:

- **`BeatVisualizer`** — the small row of beat dots + subdivision pips under the
  main visual. Unchanged for a while; simple.
- **`ClickVisualizer`** — the big centre visual. THIS is the one that evolved a lot.
  Read its docstring. It has **three render paths**:

  1. **rings** (no media loaded) — sonar "ping": each click fires an expanding,
     fading ring of dots (`●`/`•`/`·`), colour-coded accent=red/beat=green/
     subdivision=cyan. Uses `_pings` list + `_render_rings()`. Cell-space geometry
     (`_ensure_geometry`, x halved so circles look round).
  2. **half-block image/GIF** (media loaded, no graphics protocol) — renders the
     image with the **`▀` upper-half-block** trick: top half = foreground colour
     (top pixel), bottom half = background colour (bottom pixel) → 2 vertical
     pixels per character cell. Frames resampled in `_ensure_image()` to
     `w × (2h)` px, **letterboxed (contain) on black** so the whole image shows
     (NOT cropped — user explicitly wanted the full image). `_render_image()`.
  3. **real pixel graphics** (media loaded AND terminal supports Kitty/iTerm/Sixel)
     — `_render_graphics()` hands the PIL frame to `textual_image`'s `Image`
     renderable → true pixel resolution. Auto-detected at import (`GRAPHICS_AVAILABLE`).

  **Media handling:** `visualiser_img/` folder (sibling of the package when run from
  source, sibling of the executable when frozen — see `visualiser_dir()`). Newest
  file used on startup. **Animated GIFs play as a looping animation** (frames loaded
  via `ImageSequence`, sampled to ≤`MAX_FRAMES=120`, advanced by their own ms
  durations in `_frame()` at `FPS=30` timer rate). Still images shown static. Each
  click adds a **uniform brightness flash** (`_flash`, decays) — this REPLACED an
  earlier "wave over the image" effect that the user disliked. Frames composited
  onto **black** on load (fixes GIF transparency showing as a checkerboard).

  **Adaptive resolution:** `_dims()` reads `self.content_size` and the grid fills
  whatever cells the widget gets (capped `MAX_COLS=220`, `MAX_ROWS=80`). The CSS
  makes `#main` span the terminal (`width:98% height:100%`) and `ClickVisualizer`
  `height:1fr` so it fills leftover space. Margins were trimmed and the logo made a
  one-liner to hand more rows to the image.

### The hard truth about visualiser resolution (don't re-litigate)
A terminal renders **character cells, not pixels**. With half-blocks the ceiling is
`columns × (2 × rows)`. At the user's 142×36 terminal the image is only ~133×42 px →
looks blocky. **This cannot be beaten in the text-cell path** (half-block is already
max colour resolution per cell; quadrant/sextant/braille can't do per-subcell
colour). The only real fixes, both documented in README:
- **Zoom out the terminal font / enlarge window** → more cells → more resolution.
- **Use a graphics-capable terminal** (kitty/WezTerm/iTerm2/Sixel) → `textual-image`
  renders true pixels. Status line shows `🖼️ pixel-graphics` vs `half-block`.

### ⚠️ UNVERIFIED: the graphics path
The graphics render path (`_render_graphics` + `textual-image`) is **structurally
tested** (works as a Textual renderable, headless falls back fine) but the **actual
Sixel/Kitty output was NEVER tested** — the dev sandbox has no graphics-capable
terminal. When the user runs it in kitty etc., confirm: (a) status says
`🖼️ pixel-graphics`, (b) GIF animation is smooth (sixel re-encodes every frame —
may be CPU-heavy/laggy; TGP/kitty is lighter), (c) no compositor artifacts. If laggy
in graphics mode, consider capping animation FPS or caching. Everything is wrapped in
try/except → any failure falls back to half-block.

---

## 6. GOTCHAS / lessons (these bit us — don't repeat)

1. **`self._ready` collides with Textual's internal `App._ready()` method** →
   `'bool' object is not callable`. We use `self._ui_ready` instead. Don't name an
   App attribute `_ready`.
2. **`$accent` / `$secondary` etc. are Textual CSS variables, NOT Rich colours.**
   They work in the `CSS` block but **crash inside `Text.from_markup(...)`**
   (`MissingStyle`). Use concrete colours (`cyan`, `#e8c17a`) in markup strings.
3. **Reactive watchers fire during `compose()`** (first attribute access), before
   child widgets exist → `query_one` NoMatches. Guard widget updates with the
   `self._ui_ready` flag (set True at end of `on_mount`).
4. **PyInstaller + relative imports:** freezing `__main__.py` runs it as a top-level
   script → `from .app import main` fails (`no known parent package`). Fix = separate
   `launch.py` with ABSOLUTE import as the PyInstaller entry. Don't point the build
   at `__main__.py`.
5. **PyInstaller collect flags:** need `--collect-all pygame` (native SDL libs),
   `--collect-all textual`, `--collect-all textual_image`. Submodules-only is not
   enough for pygame.
6. **Audio device contention / orphaned processes:** running multiple app instances,
   or a test whose `python -m aarpo_metronome` child **outlives its `timeout`**
   (orphaned under `script`), leaves a process **holding the audio device**, so the
   NEXT `pygame.mixer.init()` **hangs** → looks like "the app won't quit / q doesn't
   work". This caused a false "regression" panic once. **Always**: for headless
   tests set `SDL_AUDIODRIVER=dummy`; before/after testing, kill strays:
   `ps -eo pid,cmd | grep -E "aarpo_metronome|run_test" | grep -v grep`. Do NOT
   `pkill -f aarpo_metronome` — it matches your own test process and kills it.
7. **`.desktop` `Icon=` with a path containing a space** falls back to a generic
   icon in GNOME's app grid. Fix = install the PNG into the icon **theme** via
   `xdg-icon-resource` and reference it by **name** (`Icon=aarpo-metronome`).
   `install-linux.sh` does this. After install the user must **log out/in** (Wayland
   can't restart gnome-shell live) for the icon to refresh.
8. **`.desktop` `Exec=` with a space** must be quoted (`Exec="/path with space/x"`)
   or it splits on the space.
9. **The image is invisible if used raw as an icon:** the original `img/aarpo.png`
   is a near-white wordmark on transparent (7.6% opaque). We composite it on a dark
   brown (`#26201705` → (38,30,23)) background for the icon (`img/aarpo-icon.png`,
   `aarpo.ico`, `aarpo.icns`, sized `aarpo-256/512.png`).

---

## 7. Testing (how to verify without a real terminal)

- **Headless TUI test:** Textual `app.run_test(size=(W,H))` → `pilot.press(...)`,
  `pilot.pause(seconds)`, assert on `app.bpm` etc. ALWAYS prefix with
  `SDL_AUDIODRIVER=dummy` to avoid audio-device hangs.
- **Screenshots:** `app.export_screenshot()` returns SVG → write to file →
  `cairosvg.svg2png(...)` → Read the PNG. **CAVEAT:** the SVG export font lacks many
  glyphs — the big `Digits`, box-drawing borders, emoji, and the `●`/`▀` visualiser
  glyphs render as **`□` boxes** in the export. They render FINE in a real terminal.
  Don't panic at boxes in screenshots; check colours/layout instead. (The `▀`
  half-block sometimes does export, sometimes not.)
- **Frozen binary test:** run under a pty and send `q` after startup:
  `{ sleep 9; printf 'q'; } | timeout 35 script -qec "./dist/aarpo-metronome" /tmp/x.log`
  → expect exit 0 and no traceback. Exit **124** = the `timeout` killed it (usually
  the binary cold-extract took longer than the sleep, OR an orphaned audio process —
  send `q` later / kill strays; it's almost never a real hang).
- **Render perf check:** `_render_image` ~3–5 ms/frame; fine.

Typical regression one-liner lives in the chat history; it presses up/b/v/i/comma/
period/space and asserts state + no overflow.

---

## 8. Run / build / distribute

- **Run from source:** `./run.sh` (mac/Linux) or `run.bat` (Windows). They create
  `./.venv` on first run, install `requirements.txt`, then `python -m aarpo_metronome`.
  `run.sh` is **self-healing**: it validates the venv imports (`textual, pygame, PIL,
  textual_image`) and rebuilds the venv if missing/foreign (e.g. a Linux venv copied
  to a Mac). Must run in a **real interactive terminal** (it's a TUI).
- **Double-click launchers:** `AARPO Metronome.command` (mac, opens Terminal),
  `AARPO Metronome.bat` (Windows), and on Linux `./install-linux.sh` adds an app-grid
  icon (or double-click `start-linux.sh`, which spawns a terminal emulator).
- **Standalone binary (no Python needed by end user):** `python build.py` →
  `dist/aarpo-metronome` (`.exe` on Windows). Per-OS double-click helpers:
  `build-mac.command`, `build-windows.bat`, `build-linux.sh`. **PyInstaller does NOT
  cross-compile** — must build on each target OS / CPU arch. Only the **Linux**
  binary has been built+tested here; mac/win must be built on those machines. The
  build attaches the right icon (`build.py:_resolve_icon`): `.ico` Windows, `.icns`
  mac (generated from master PNG via Pillow if absent), none on Linux.
- The user was shown how to send it to the bandmate (zip via `git archive`, or the
  GitHub zip link). Mac first-launch needs right-click→Open (Gatekeeper) and Python
  installed once.

---

## 9. What's gitignored (and why it matters)

`.gitignore` excludes: `.venv/`, `build/`, `dist/`, `*.spec`, `__pycache__/`,
`~/.aarpo_metronome` config, AND **`visualiser_img/*` except `README.txt`**. So:
- The user's personal **`visualiser_img/visualiser.gif`** (18MB, 24 frames) and
  `visualiser.png` are **on their machine only**, NOT in the repo. The next agent
  won't see them in a fresh clone. The repo ships only the AARPO-logo default
  (`aarpo_metronome/assets/visualiser_default.png`).
- The compiled binaries are not committed (platform-specific/large). Ship via
  GitHub Releases if ever needed.

---

## 10. Open items / ideas the user might ask for next

- **Verify the graphics path** on a real Kitty/WezTerm/Sixel terminal (see §5 ⚠️).
  This is the most important loose end — the user wants a sharp GIF and we don't yet
  know if pixel-graphics works for them. They were told to try `sudo apt install
  kitty` and check the status line.
- **BPM-synced GIF playback** — offered but not built: advance the animation in time
  with the tempo (e.g. one loop per beat/bar) instead of free-running native speed.
- **Bundle the user's GIF as the default** into the standalone build (they declined;
  would add ~18MB to the binary).
- **Demo GIF/screencast in the README** — best recorded on the user's real terminal.
- Possible perf tuning if graphics-mode animation is laggy (cap FPS / cache frames).

---

## 11. Commit history (most recent first)

```
0199eaf real pixel-graphics rendering on capable terminals (textual-image)
93c74bd slim one-line logo to give the visualiser more height
c63839e fit the whole GIF (no crop), composite transparency on black
5c2e22d play animated GIFs instead of the image wave
20ef90e maximise image visualiser resolution; fit UI to terminal
50927be 'fine' mode: render the real image (half-block), wave ripples over it
b95048c sharper dot-mosaic: adaptive res, vivid contrast on black
6d9b340 ship default visualiser image (AARPO logo) + brightness control
33e6a52 add image visualiser: dot-mosaic with beat wave
6b893c4 fix Linux app-grid icon (icon theme by name)
1fca7a4 AARPO branding: app icon + UI wordmark logo
db21123 initial commit: cross-platform terminal metronome
```

The visualiser arc: dot-mosaic+wave → fine half-block+wave → play GIF+flash →
fit whole GIF → +real pixel graphics. Current = §5.

---

## 12. Quick start for the next session

```bash
cd "/home/krissagar95/smart_metrnome app"
. .venv/bin/activate                       # venv already set up
SDL_AUDIODRIVER=dummy python -c "import asyncio; ..."   # headless tests
./run.sh                                    # run for real (needs a TTY)
python build.py                             # rebuild dist/aarpo-metronome
git push origin main                        # SSH auth already works
```

Be honest with the user about terminal limits (don't promise pixel-perfect on
GNOME Terminal). They iterate fast and prefer action + a clear explanation of
trade-offs over open-ended questions.
