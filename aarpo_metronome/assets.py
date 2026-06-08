"""Audio asset generation.

The metronome ships its own click sounds. Rather than committing binary blobs we
synthesize small, pleasant percussive "clicks" with nothing but the Python standard
library (``math`` + ``wave``). Files are written once and then reused, so the app is
fully self-contained and works out-of-the-box on any OS.

Three voices are produced:

* ``accent``      — the emphasized down-beat (bright, loud)
* ``beat``        — a normal main beat
* ``subdivision`` — the softer in-between clicks
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

SAMPLE_RATE = 44_100

# name -> (frequency Hz, duration s, peak volume 0..1, decay rate, 2nd-harmonic mix)
CLICK_PROFILES: dict[str, tuple[float, float, float, float, float]] = {
    "accent":      (1568.0, 0.075, 0.92, 30.0, 0.35),
    "beat":        (988.0,  0.065, 0.78, 34.0, 0.25),
    "subdivision": (1760.0, 0.040, 0.42, 50.0, 0.0),
}


def _render_click(freq: float, duration: float, volume: float,
                  decay: float, harmonic: float) -> bytes:
    """Render a single mono 16-bit PCM click as raw frame bytes."""
    n_samples = int(SAMPLE_RATE * duration)
    attack = max(1, int(SAMPLE_RATE * 0.0015))  # tiny fade-in kills the "pop"
    frames = bytearray()
    norm = 1.0 + harmonic
    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-decay * t)
        if i < attack:
            env *= i / attack
        sample = math.sin(2.0 * math.pi * freq * t)
        if harmonic:
            sample += harmonic * math.sin(2.0 * math.pi * (freq * 2.0) * t)
        value = (sample / norm) * env * volume
        value = max(-1.0, min(1.0, value))
        frames += struct.pack("<h", int(value * 32767))
    return bytes(frames)


def _write_wav(path: Path, data: bytes) -> None:
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(data)


def get_asset_dir() -> Path:
    """Return a writable directory that holds the click WAVs.

    Prefers the package's own ``assets`` folder. When that is read-only (e.g. a
    frozen / PyInstaller build) it falls back to a per-user directory.
    """
    if getattr(sys, "frozen", False):
        bundled = Path(getattr(sys, "_MEIPASS", "")) / "assets"
        if bundled.is_dir():
            return bundled

    pkg_assets = Path(__file__).resolve().parent / "assets"
    try:
        pkg_assets.mkdir(exist_ok=True)
        probe = pkg_assets / ".write_test"
        probe.write_text("ok")
        probe.unlink()
        return pkg_assets
    except OSError:
        user_dir = Path.home() / ".aarpo_metronome" / "assets"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir


def ensure_assets(asset_dir: Path | None = None) -> dict[str, Path]:
    """Make sure every click WAV exists; generate any that are missing.

    Returns a mapping of voice name -> file path.
    """
    asset_dir = asset_dir or get_asset_dir()
    asset_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, profile in CLICK_PROFILES.items():
        path = asset_dir / f"{name}.wav"
        if not path.exists() or path.stat().st_size == 0:
            _write_wav(path, _render_click(*profile))
        paths[name] = path
    return paths


if __name__ == "__main__":  # allow `python -m aarpo_metronome.assets` to (re)build
    generated = ensure_assets()
    for voice, file in generated.items():
        print(f"{voice:12s} -> {file}")
