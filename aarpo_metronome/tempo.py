"""Tempo metadata: Italian tempo markings and subdivision names."""

from __future__ import annotations

# (upper-bound-exclusive BPM, name). Ordered slow -> fast.
_TEMPO_MARKINGS: list[tuple[int, str]] = [
    (40,  "Grave"),
    (60,  "Largo"),
    (66,  "Larghetto"),
    (76,  "Adagio"),
    (108, "Andante"),
    (120, "Moderato"),
    (156, "Allegro"),
    (176, "Vivace"),
    (200, "Presto"),
    (10_000, "Prestissimo"),
]


def tempo_marking(bpm: int) -> str:
    """Return the Italian tempo marking for a given BPM."""
    for upper, name in _TEMPO_MARKINGS:
        if bpm < upper:
            return name
    return "Prestissimo"


# subdivision count -> human label
SUBDIVISION_LABELS: dict[int, str] = {
    1: "Quarter notes",
    2: "Eighth notes",
    3: "Triplets",
    4: "Sixteenth notes",
}

MAX_SUBDIVISIONS = 4


def subdivision_label(subdivisions: int) -> str:
    return SUBDIVISION_LABELS.get(subdivisions, f"{subdivisions} per beat")
