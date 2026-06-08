"""The Textual terminal UI for AARPO Metronome."""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

from rich.align import Align
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Digits, Footer, Header, Static

from .assets import get_asset_dir
from .audio import create_audio_backend
from .engine import MAX_BPM, MIN_BPM, MetronomeEngine
from .presets import Preset, add_preset, load_presets
from .tempo import MAX_SUBDIVISIONS, subdivision_label, tempo_marking

MIN_BEATS = 1
MAX_BEATS = 12

# ASCII-art "aarpo" wordmark shown at the top of the UI (terminals can't render
# the PNG logo reliably, so this is the on-brand text equivalent).
LOGO = r"""  __ _   __ _  _ __  _ __    ___
 / _` | / _` || '__|| '_ \  / _ \
| (_| || (_| || |   | |_) || (_) |
 \__,_| \__,_||_|   | .__/  \___/
                    |_|"""


def visualiser_dir() -> Path:
    """Folder where users drop background images for the visualiser.

    Lives next to the executable for a frozen build, or at the project root
    (sibling of the package) when run from source. Created if missing.
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent
    folder = base / "visualiser_img"
    try:
        folder.mkdir(exist_ok=True)
    except OSError:
        pass
    return folder


class BeatVisualizer(Static):
    """Animated row of beat indicators plus a subdivision strip."""

    beats = reactive(4)
    subdivisions = reactive(1)
    accent_beats: reactive[frozenset[int]] = reactive(frozenset({0}))
    current_beat = reactive(-1)
    current_sub = reactive(0)
    playing = reactive(False)
    flash = reactive(0)  # bumped on every tick to retrigger the pulse

    def render(self):
        text = Text(justify="center")

        # --- main beats -----------------------------------------------------
        for i in range(self.beats):
            is_accent = i in self.accent_beats
            is_current = self.playing and i == self.current_beat
            glyph = "◆" if is_accent else "●"
            if is_current:
                if self.current_sub == 0:
                    style = "bold white on red" if is_accent else "bold black on green"
                else:
                    # an off-beat subdivision is sounding within this beat
                    style = "bold yellow" if is_accent else "bold green"
            else:
                style = "yellow" if is_accent else "grey50"
            text.append("  ")
            text.append(f" {glyph} ", style=style)
        text.append("\n\n")

        # --- subdivision strip for the active beat --------------------------
        if self.subdivisions > 1:
            for s in range(self.subdivisions):
                lit = self.playing and s == self.current_sub
                pip = "▮" if s == 0 else "▯"
                style = "bold cyan" if lit else "grey37"
                text.append(f" {pip} ", style=style)
            text.append("\n")

        return Align.center(text)


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


class ClickVisualizer(Static):
    """The beat visualiser. Every click fires an expanding, fading ring.

    Two modes:

    * **rings** (default) — a sonar ping on a blank field; accents / beats /
      subdivisions get their own colour and reach.
    * **image** — if an image is found in the ``visualiser_img/`` folder it is
      rendered as a colour dot-mosaic, and each click sweeps a bright wave-crest
      outward across it (the dots brighten as the ring passes, then settle back).

    Press ``i`` in the app to cycle: rings → each image → rings.
    """

    COLS = 50
    ROWS = 14
    FPS = 24
    DECAY = 0.86  # per-frame intensity multiplier
    DIM = 0.5     # idle brightness of the background image (so the crest pops)

    _PALETTE = {"accent": "red", "beat": "green", "subdivision": "cyan"}
    _REACH = {"accent": 1.0, "beat": 0.8, "subdivision": 0.5}

    def __init__(self, *args, image_dir: str | None = None,
                 default_image: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._pings: list[dict] = []
        self._was_active = False
        self._image_dir = image_dir
        self._default_image = default_image
        self._images: list = []
        self._current = None            # None => plain rings, else a Path
        self._base_grid = None          # ROWS x COLS of (r, g, b), or None
        self.bg_name = "rings"
        self._brightness = self.DIM     # idle image brightness (adjustable)
        self._cx = (self.COLS - 1) / 2.0
        self._cy = (self.ROWS - 1) / 2.0
        self._maxd = math.hypot(self._cx * 0.5, self._cy)
        self._thick = 1.4

    def on_mount(self) -> None:
        sources = self._sources()
        # Start on the newest user image, else the bundled default, else rings.
        if self._images:
            self._select(self._images[0])
        elif len(sources) > 1:
            self._select(sources[1])
        else:
            self._select(None)
        self.set_interval(1.0 / self.FPS, self._frame)
        self.refresh()

    # ----------------------------------------------------------- background images
    def _discover_images(self) -> None:
        self._images = []
        if not self._image_dir:
            return
        folder = Path(self._image_dir)
        if not folder.is_dir():
            return
        files = [p for p in folder.iterdir()
                 if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)  # newest first
        self._images = files

    def _load_image(self, path) -> None:
        try:
            from PIL import Image, ImageOps
        except Exception:
            self._base_grid = None
            self.bg_name = "rings (pip install pillow for images)"
            return
        try:
            img = Image.open(path).convert("RGB")
            # Terminal cells are ~2x taller than wide: fit to COLS x (ROWS*2)
            # preserving aspect (centre-crop), then squash vertically to ROWS.
            fitted = ImageOps.fit(img, (self.COLS, self.ROWS * 2), Image.LANCZOS)
            small = fitted.resize((self.COLS, self.ROWS), Image.LANCZOS)
            px = small.load()
            self._base_grid = [[px[c, r] for c in range(self.COLS)]
                               for r in range(self.ROWS)]
            self.bg_name = path.name
        except Exception:
            self._base_grid = None
            self.bg_name = "rings (image could not be read)"

    def _sources(self) -> list:
        """Ordered cycle of backgrounds: rings, bundled default, user images."""
        self._discover_images()
        sources: list = [None]  # None = plain rings
        if self._default_image and Path(self._default_image).is_file():
            sources.append(Path(self._default_image))
        sources += self._images
        return sources

    def _select(self, source) -> None:
        if source is None:
            self._base_grid = None
            self.bg_name = "rings"
        else:
            self._load_image(source)
            if (self._base_grid is not None and self._default_image
                    and Path(source) == Path(self._default_image)):
                self.bg_name = "aarpo (default)"
        self._current = source

    def cycle_background(self) -> str:
        """Cycle through: rings -> bundled default -> each user image -> rings."""
        sources = self._sources()
        try:
            idx = sources.index(self._current)
        except ValueError:
            idx = 0
        self._select(sources[(idx + 1) % len(sources)])
        self.refresh()
        return self.bg_name

    def adjust_brightness(self, delta: float) -> int:
        """Tweak the idle image brightness; returns the new value as a percent."""
        self._brightness = max(0.2, min(0.95, self._brightness + delta))
        self.refresh()
        return round(self._brightness * 100)

    # ----------------------------------------------------------------- animation
    def ping(self, kind: str) -> None:
        """Register a new click to animate."""
        self._pings.append({"i": 1.0, "kind": kind})
        if len(self._pings) > 8:  # cap overlap at very high tempo
            self._pings = self._pings[-8:]

    def _frame(self) -> None:
        if self._pings:
            for ping in self._pings:
                ping["i"] *= self.DECAY
            self._pings = [p for p in self._pings if p["i"] > 0.05]
            self._was_active = True
            self.refresh()
        elif self._was_active:
            self._was_active = False
            self.refresh()  # one final paint to settle back to the static image

    def _rings(self):
        return [(p, (1.0 - p["i"]) * self._maxd * self._REACH[p["kind"]])
                for p in self._pings]

    def _glow(self, dist, rings, peak):
        g = 0.0
        for ping, radius in rings:
            d = abs(dist - radius)
            if d <= self._thick:
                gg = ping["i"] * (1.0 - d / self._thick)
                if gg > g:
                    g = gg
        if dist < 1.0 and peak > 0.82:  # bright core on a fresh click
            g = max(g, peak)
        return g

    def render(self):
        rings = self._rings()
        peak = max((p["i"] for p in self._pings), default=0.0)
        if self._base_grid is not None:
            return self._render_image(rings, peak)
        return self._render_rings(rings, peak)

    def _render_image(self, rings, peak):
        text = Text()
        grid = self._base_grid
        for r in range(self.ROWS):
            row = grid[r]
            for c in range(self.COLS):
                dist = math.hypot((c - self._cx) * 0.5, r - self._cy)
                glow = self._glow(dist, rings, peak)
                br, bg, bb = row[c]
                bf = self._brightness + glow         # brightness factor
                tw = min(1.0, glow) * 0.6            # whiten the wave-crest
                rr = min(255, int(br * bf * (1 - tw) + 255 * tw))
                gg = min(255, int(bg * bf * (1 - tw) + 255 * tw))
                bb2 = min(255, int(bb * bf * (1 - tw) + 255 * tw))
                text.append("●", style=f"#{rr:02x}{gg:02x}{bb2:02x}")
            if r != self.ROWS - 1:
                text.append("\n")
        return Align.center(text)

    def _render_rings(self, rings, peak):
        text = Text()
        for row in range(self.ROWS):
            for col in range(self.COLS):
                dist = math.hypot((col - self._cx) * 0.5, row - self._cy)
                best = None  # (intensity, kind) of the strongest ring touching here
                for ping, radius in rings:
                    if abs(dist - radius) <= self._thick and (
                        best is None or ping["i"] > best[0]
                    ):
                        best = (ping["i"], ping["kind"])

                if dist < 1.0 and peak > 0.82:
                    text.append("✦", style="bold white")
                elif best is not None:
                    inten, kind = best
                    color = self._PALETTE[kind]
                    if inten > 0.55:
                        glyph, style = "●", f"bold {color}"
                    elif inten > 0.30:
                        glyph, style = "•", color
                    else:
                        glyph, style = "·", f"dim {color}"
                    text.append(glyph, style=style)
                elif dist < 1.0:
                    text.append("·", style="grey30")  # faint idle centre
                else:
                    text.append(" ")
            if row != self.ROWS - 1:
                text.append("\n")
        return Align.center(text)


class MetronomeApp(App):
    TITLE = "AARPO Metronome"
    SUB_TITLE = "a terminal metronome"

    CSS = """
    Screen {
        align: center middle;
    }
    #main {
        width: 84;
        max-width: 96%;
        height: auto;
        border: round $accent;
        padding: 1 2;
    }
    #logo {
        width: auto;
        height: auto;
        color: #e8c17a;
        text-style: bold;
        margin-bottom: 1;
    }
    #top {
        height: auto;
        margin-bottom: 1;
    }
    #bpm-box {
        width: 2fr;
        height: auto;
        align: center middle;
        border-right: vkey $panel-lighten-2;
    }
    #bpm-digits {
        color: $accent;
        width: auto;
        content-align: center middle;
    }
    .label {
        color: $text-muted;
        text-align: center;
        text-style: bold;
    }
    #tempo-name {
        color: $secondary;
        text-align: center;
        text-style: italic bold;
    }
    #info-box {
        width: 3fr;
        height: auto;
        padding: 0 2;
        content-align: left middle;
    }
    #info-box Static {
        height: 1;
        margin-bottom: 1;
    }
    #tempo-bar {
        text-align: center;
        margin: 1 0;
        color: $accent;
    }
    ClickVisualizer {
        height: 14;
        content-align: center middle;
        margin: 0;
    }
    BeatVisualizer {
        height: auto;
        min-height: 5;
        content-align: center middle;
        margin: 1 0;
    }
    #status {
        text-align: center;
        text-style: bold;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("space", "toggle_play", "Start / Stop"),
        ("up", "bpm(1)", "+1 BPM"),
        ("down", "bpm(-1)", "-1 BPM"),
        ("right", "bpm(5)", "+5"),
        ("left", "bpm(-5)", "-5"),
        ("pageup", "bpm(10)", "+10"),
        ("pagedown", "bpm(-10)", "-10"),
        ("t", "tap", "Tap tempo"),
        ("b", "cycle_beats", "Beats/bar"),
        ("v", "cycle_subdiv", "Subdivision"),
        ("a", "toggle_accent", "Accent"),
        ("i", "cycle_background", "Visualiser bg"),
        ("comma", "vis_brightness(-1)", "Dimmer"),
        ("full_stop", "vis_brightness(1)", "Brighter"),
        ("s", "save_preset", "Save preset"),
        ("l", "load_preset", "Load preset"),
        ("r", "reset", "Reset"),
        ("q", "quit", "Quit"),
    ]

    # --- reactive state ----------------------------------------------------
    bpm = reactive(120)
    beats_per_measure = reactive(4)
    subdivisions = reactive(1)
    accent_enabled = reactive(True)
    accent_beats: reactive[frozenset[int]] = reactive(frozenset({0}))
    playing = reactive(False)

    def __init__(self) -> None:
        super().__init__()
        self.audio = create_audio_backend()
        self.engine = MetronomeEngine(self.audio, on_tick=self._on_tick)
        self._tap_times: list[float] = []
        self._presets: list[Preset] = load_presets()
        self._preset_index = -1
        self._status_msg = ""
        # Becomes True only once all widgets are composed and mounted, so that
        # reactive watchers don't try to query widgets that don't exist yet
        # (reactives initialise lazily during compose()).
        self._ui_ready = False

    # --- layout ------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main"):
            with Center():
                yield Static(LOGO, id="logo")
            with Horizontal(id="top"):
                with Vertical(id="bpm-box"):
                    yield Static("TEMPO (BPM)", classes="label")
                    yield Digits(str(self.bpm), id="bpm-digits")
                    yield Static(tempo_marking(self.bpm), id="tempo-name")
                with Vertical(id="info-box"):
                    yield Static(id="time-sig")
                    yield Static(id="subdiv")
                    yield Static(id="accent")
            yield Static(id="tempo-bar")
            yield ClickVisualizer(
                id="pulse",
                image_dir=str(visualiser_dir()),
                default_image=str(get_asset_dir() / "visualiser_default.png"),
            )
            yield BeatVisualizer(id="beats")
            yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.engine.start()
        self._ui_ready = True
        self._push_params()
        self._refresh_all()
        if not self.audio.available:
            reason = getattr(self.audio, "reason", "")
            self._set_status(f"🔇 Visual-only mode (no audio: {reason})")
        else:
            self._set_status("Ready — press [b]Space[/] to start")

    def on_unmount(self) -> None:
        self.engine.shutdown()

    # --- helpers -----------------------------------------------------------
    def _push_params(self) -> None:
        self.engine.set_params(
            bpm=self.bpm,
            beats_per_measure=self.beats_per_measure,
            subdivisions=self.subdivisions,
            accent_enabled=self.accent_enabled,
            accent_beats=set(self.accent_beats),
        )

    def _set_status(self, message: str) -> None:
        self._status_msg = message
        try:
            self.query_one("#status", Static).update(message)
        except Exception:
            pass

    def _refresh_all(self) -> None:
        self._update_bpm_widgets()
        self._update_info_widgets()
        self._sync_visualizer()

    def _update_bpm_widgets(self) -> None:
        self.query_one("#bpm-digits", Digits).update(str(self.bpm))
        self.query_one("#tempo-name", Static).update(tempo_marking(self.bpm))
        self.query_one("#tempo-bar", Static).update(self._render_tempo_bar())

    def _render_tempo_bar(self) -> Text:
        width = 44
        frac = (self.bpm - MIN_BPM) / (MAX_BPM - MIN_BPM)
        filled = max(0, min(width, round(frac * width)))
        bar = Text()
        bar.append(f"{MIN_BPM} ", style="grey50")
        bar.append("━" * filled, style="bold green")
        bar.append("●", style="bold white")
        bar.append("━" * (width - filled), style="grey37")
        bar.append(f" {MAX_BPM}", style="grey50")
        return bar

    def _update_info_widgets(self) -> None:
        self.query_one("#time-sig", Static).update(
            Text.from_markup(
                f"[b]Time signature[/]   [b cyan]{self.beats_per_measure}/4[/]"
                f"   [dim]({self.beats_per_measure} beats per bar)[/]"
            )
        )
        self.query_one("#subdiv", Static).update(
            Text.from_markup(
                f"[b]Subdivision[/]     [b cyan]{self.subdivisions}×[/]"
                f"   [dim]{subdivision_label(self.subdivisions)}[/]"
            )
        )
        accents = ", ".join(str(b + 1) for b in sorted(self.accent_beats)) or "none"
        state = "[b green]ON[/]" if self.accent_enabled else "[b red]OFF[/]"
        self.query_one("#accent", Static).update(
            Text.from_markup(f"[b]Accent[/]          {state}   [dim]beats: {accents}[/]")
        )

    def _sync_visualizer(self) -> None:
        vis = self.query_one(BeatVisualizer)
        vis.beats = self.beats_per_measure
        vis.subdivisions = self.subdivisions
        vis.accent_beats = frozenset(self.accent_beats)
        vis.playing = self.playing

    # --- engine callback (runs on the engine thread) -----------------------
    def _on_tick(self, kind: str, beat: int, sub: int, beats: int, subs: int) -> None:
        self.call_from_thread(self._show_tick, kind, beat, sub)

    def _show_tick(self, kind: str, beat: int, sub: int) -> None:
        vis = self.query_one(BeatVisualizer)
        vis.current_beat = beat
        vis.current_sub = sub
        vis.flash += 1
        self.query_one(ClickVisualizer).ping(kind)

    # --- reactive watchers -------------------------------------------------
    def watch_bpm(self, value: int) -> None:
        if self._ui_ready:
            self._update_bpm_widgets()
        self.engine.set_params(bpm=value)

    def watch_beats_per_measure(self, value: int) -> None:
        # keep accents within range
        self.accent_beats = frozenset(b for b in self.accent_beats if b < value) or frozenset({0})
        if self._ui_ready:
            self._update_info_widgets()
            self._sync_visualizer()
        self.engine.set_params(beats_per_measure=value, accent_beats=set(self.accent_beats))

    def watch_subdivisions(self, value: int) -> None:
        if self._ui_ready:
            self._update_info_widgets()
            self._sync_visualizer()
        self.engine.set_params(subdivisions=value)

    def watch_accent_enabled(self, value: bool) -> None:
        if self._ui_ready:
            self._update_info_widgets()
        self.engine.set_params(accent_enabled=value)

    def watch_accent_beats(self, value: frozenset[int]) -> None:
        if self._ui_ready:
            self._update_info_widgets()
            self._sync_visualizer()
        self.engine.set_params(accent_beats=set(value))

    def watch_playing(self, value: bool) -> None:
        if self._ui_ready:
            self._sync_visualizer()

    # --- actions -----------------------------------------------------------
    def action_toggle_play(self) -> None:
        self.playing = self.engine.toggle()
        if self.playing:
            self._set_status("▶ Playing")
        else:
            self.query_one(BeatVisualizer).current_beat = -1
            self._set_status("⏸ Stopped")

    def action_bpm(self, delta: int) -> None:
        self.bpm = max(MIN_BPM, min(MAX_BPM, self.bpm + delta))

    def action_cycle_beats(self) -> None:
        self.beats_per_measure = MIN_BEATS if self.beats_per_measure >= MAX_BEATS else self.beats_per_measure + 1
        self._set_status(f"Time signature → {self.beats_per_measure}/4")

    def action_cycle_subdiv(self) -> None:
        self.subdivisions = 1 if self.subdivisions >= MAX_SUBDIVISIONS else self.subdivisions + 1
        self._set_status(f"Subdivision → {subdivision_label(self.subdivisions)}")

    def action_toggle_accent(self) -> None:
        self.accent_enabled = not self.accent_enabled
        self._set_status(f"Accent {'enabled' if self.accent_enabled else 'disabled'}")

    def action_cycle_background(self) -> None:
        name = self.query_one(ClickVisualizer).cycle_background()
        self._set_status(f"Visualiser: {name}")

    def action_vis_brightness(self, direction: int) -> None:
        pct = self.query_one(ClickVisualizer).adjust_brightness(0.1 * direction)
        self._set_status(f"Visualiser brightness: {pct}%")

    def action_tap(self) -> None:
        now = time.perf_counter()
        # drop taps older than 2s — treat as a fresh sequence
        if self._tap_times and now - self._tap_times[-1] > 2.0:
            self._tap_times.clear()
        self._tap_times.append(now)
        self._tap_times = self._tap_times[-6:]
        if len(self._tap_times) >= 2:
            intervals = [b - a for a, b in zip(self._tap_times, self._tap_times[1:])]
            avg = sum(intervals) / len(intervals)
            if avg > 0:
                self.bpm = max(MIN_BPM, min(MAX_BPM, round(60.0 / avg)))
                self._set_status(f"Tap tempo → {self.bpm} BPM")
        else:
            self._set_status("Tap again…")

    def action_save_preset(self) -> None:
        name = f"{self.bpm}bpm {self.beats_per_measure}/4 x{self.subdivisions}"
        preset = Preset(
            name=name,
            bpm=self.bpm,
            beats_per_measure=self.beats_per_measure,
            subdivisions=self.subdivisions,
            accent_enabled=self.accent_enabled,
            accent_beats=sorted(self.accent_beats),
        )
        self._presets = add_preset(preset)
        self._set_status(f"💾 Saved preset: {name}")

    def action_load_preset(self) -> None:
        self._presets = load_presets()
        if not self._presets:
            self._set_status("No presets saved yet — press [b]s[/] to save one")
            return
        self._preset_index = (self._preset_index + 1) % len(self._presets)
        p = self._presets[self._preset_index]
        self.beats_per_measure = p.beats_per_measure
        self.subdivisions = p.subdivisions
        self.accent_enabled = p.accent_enabled
        self.accent_beats = frozenset(b for b in p.accent_beats if b < p.beats_per_measure) or frozenset({0})
        self.bpm = max(MIN_BPM, min(MAX_BPM, p.bpm))
        self._set_status(f"📂 Loaded: {p.name}")

    def action_reset(self) -> None:
        self.bpm = 120
        self.beats_per_measure = 4
        self.subdivisions = 1
        self.accent_enabled = True
        self.accent_beats = frozenset({0})
        self._set_status("Reset to defaults")

    # --- per-beat accent toggling via number keys --------------------------
    def on_key(self, event) -> None:
        if event.key.isdigit():
            n = int(event.key)
            if 1 <= n <= self.beats_per_measure:
                idx = n - 1
                beats = set(self.accent_beats)
                beats ^= {idx}
                self.accent_beats = frozenset(beats)
                self._set_status(f"Toggled accent on beat {n}")
                event.stop()


def main() -> None:
    MetronomeApp().run()


if __name__ == "__main__":
    main()
