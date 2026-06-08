"""Save / load metronome presets to a per-user JSON file."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Preset:
    name: str
    bpm: int
    beats_per_measure: int
    subdivisions: int
    accent_enabled: bool
    accent_beats: list[int] = field(default_factory=lambda: [0])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        return cls(
            name=str(data.get("name", "Preset")),
            bpm=int(data.get("bpm", 120)),
            beats_per_measure=int(data.get("beats_per_measure", 4)),
            subdivisions=int(data.get("subdivisions", 1)),
            accent_enabled=bool(data.get("accent_enabled", True)),
            accent_beats=[int(b) for b in data.get("accent_beats", [0])],
        )


def _presets_path() -> Path:
    base = Path.home() / ".aarpo_metronome"
    base.mkdir(parents=True, exist_ok=True)
    return base / "presets.json"


def load_presets() -> list[Preset]:
    path = _presets_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [Preset.from_dict(item) for item in raw]
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return []


def save_presets(presets: list[Preset]) -> None:
    path = _presets_path()
    path.write_text(
        json.dumps([p.to_dict() for p in presets], indent=2),
        encoding="utf-8",
    )


def add_preset(preset: Preset) -> list[Preset]:
    """Append a preset (replacing any with the same name) and persist."""
    presets = [p for p in load_presets() if p.name != preset.name]
    presets.append(preset)
    save_presets(presets)
    return presets
