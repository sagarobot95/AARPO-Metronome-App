"""Cross-platform audio backend.

Primary backend uses ``pygame.mixer`` because it ships pre-built wheels for
Windows / macOS / Linux, pre-loads samples into memory for low latency, and mixes
overlapping clicks without blocking the timing thread.

If audio can't be initialised (no sound device, headless box, missing wheel) the app
degrades gracefully to a *silent* visual-only backend instead of corrupting the TUI.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path

from .assets import ensure_assets

# Hide pygame's stdout banner before it is ever imported.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


class AudioBackend:
    """Interface for click playback."""

    available: bool = False
    name: str = "none"

    def play(self, kind: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - interface
        pass


class SilentBackend(AudioBackend):
    """Fallback when no audio device is usable. Visual-only metronome."""

    name = "silent"

    def __init__(self, reason: str = "") -> None:
        self.available = False
        self.reason = reason

    def play(self, kind: str) -> None:
        return None


class PygameBackend(AudioBackend):
    """Low-latency playback via ``pygame.mixer``."""

    name = "pygame"

    def __init__(self, asset_paths: dict[str, Path]) -> None:
        import pygame  # imported lazily so the app still starts without it

        # Small buffer => low latency. Suppress any init chatter on stderr.
        with contextlib.redirect_stderr(io.StringIO()):
            pygame.mixer.pre_init(frequency=44_100, size=-16, channels=1, buffer=256)
            pygame.mixer.init()
        pygame.mixer.set_num_channels(16)

        self._pygame = pygame
        self._sounds = {
            kind: pygame.mixer.Sound(str(path)) for kind, path in asset_paths.items()
        }
        self.available = True

    def play(self, kind: str) -> None:
        sound = self._sounds.get(kind)
        if sound is None:
            return
        channel = self._pygame.mixer.find_channel(True)  # steal oldest if needed
        if channel is not None:
            channel.play(sound)

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._pygame.mixer.quit()


def create_audio_backend() -> AudioBackend:
    """Build the best available audio backend, never raising."""
    try:
        paths = ensure_assets()
    except Exception as exc:  # asset generation failed -> silent
        return SilentBackend(reason=f"asset error: {exc}")

    try:
        return PygameBackend(paths)
    except Exception as exc:  # pygame missing or no audio device
        return SilentBackend(reason=str(exc) or "audio device unavailable")
