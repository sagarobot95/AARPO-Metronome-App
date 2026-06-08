"""The metronome timing engine.

Timing lives in its own daemon thread driven by an absolute-time scheduler. Each
tick's target time is computed as ``next_time += interval`` (never ``sleep(interval)``)
so scheduling errors never accumulate — the clock self-corrects and stays rock steady
even while the Textual UI is busy repainting.

The engine is audio-first: it plays the click *before* notifying the UI, so UI work can
never delay a beat.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

# Sensible tempo limits (BPM).
MIN_BPM = 20
MAX_BPM = 300

# kind, beat_index, sub_index, beats_per_measure, subdivisions
TickCallback = Callable[[str, int, int, int, int], None]


class MetronomeEngine:
    def __init__(self, audio, on_tick: TickCallback | None = None) -> None:
        self.audio = audio
        self.on_tick = on_tick

        self._lock = threading.Lock()
        self._playing = threading.Event()
        self._shutdown = threading.Event()
        self._wake = threading.Event()

        # Musical parameters (guarded by _lock).
        self.bpm = 120
        self.beats_per_measure = 4
        self.subdivisions = 1
        self.accent_enabled = True
        self.accent_beats: set[int] = {0}

        self._thread = threading.Thread(target=self._run, name="metronome", daemon=True)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def shutdown(self) -> None:
        self._shutdown.set()
        self._playing.clear()
        self._wake.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.audio.close()

    # -------------------------------------------------------------------- control
    def play(self) -> None:
        self._wake.set()
        self._playing.set()

    def stop(self) -> None:
        self._playing.clear()

    def toggle(self) -> bool:
        if self._playing.is_set():
            self.stop()
        else:
            self.play()
        return self._playing.is_set()

    @property
    def is_playing(self) -> bool:
        return self._playing.is_set()

    # ----------------------------------------------------------------- parameters
    def set_params(self, **kwargs) -> None:
        with self._lock:
            for key, value in kwargs.items():
                if key == "accent_beats":
                    self.accent_beats = set(value)
                elif hasattr(self, key):
                    setattr(self, key, value)

    def _snapshot(self) -> tuple[int, int, int, bool, set[int]]:
        with self._lock:
            bpm = max(MIN_BPM, min(MAX_BPM, self.bpm))
            return (bpm, max(1, self.beats_per_measure),
                    max(1, self.subdivisions), self.accent_enabled,
                    set(self.accent_beats))

    # --------------------------------------------------------------------- thread
    def _run(self) -> None:
        next_time: float | None = None
        beat = 0
        sub = 0

        while not self._shutdown.is_set():
            if not self._playing.is_set():
                # Reset position so playback always starts on the down-beat.
                next_time = None
                beat = 0
                sub = 0
                self._wake.wait(timeout=0.2)
                self._wake.clear()
                continue

            now = time.perf_counter()
            if next_time is None:
                next_time = now

            delay = next_time - now
            if delay > 0:
                # Short, interruptible sleeps keep stop/param changes responsive
                # while still hitting the absolute target time precisely.
                time.sleep(min(delay, 0.010))
                continue

            bpm, beats, subs, accent_on, accent_beats = self._snapshot()
            if beat >= beats:
                beat = 0
                sub = 0

            is_main_beat = sub == 0
            if is_main_beat and accent_on and beat in accent_beats:
                kind = "accent"
            elif is_main_beat:
                kind = "beat"
            else:
                kind = "subdivision"

            # Audio first (timing critical), then UI notification.
            self.audio.play(kind)
            if self.on_tick is not None:
                try:
                    self.on_tick(kind, beat, sub, beats, subs)
                except Exception:
                    pass

            interval = 60.0 / bpm / subs
            next_time += interval

            sub += 1
            if sub >= subs:
                sub = 0
                beat = (beat + 1) % beats

            # Drift guard: if we ever fall badly behind (machine hiccup, tempo jump),
            # resynchronise instead of frantically firing catch-up ticks.
            if time.perf_counter() - next_time > 0.25:
                next_time = time.perf_counter()
