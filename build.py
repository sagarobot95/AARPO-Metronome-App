#!/usr/bin/env python3
"""Build a single self-contained executable for the current OS using PyInstaller.

Run this on each OS you want to target (Windows / macOS / Linux) — PyInstaller does
not cross-compile. The resulting binary in ``dist/`` has no Python or dependency
requirements and runs out of the box.

    pip install pyinstaller
    python build.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    # Make sure the click WAVs exist so they can be bundled into the binary.
    from aarpo_metronome.assets import ensure_assets, get_asset_dir

    ensure_assets()
    asset_dir = get_asset_dir()
    sep = ";" if sys.platform.startswith("win") else ":"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "aarpo-metronome",
        "--noconfirm", "--clean",
        "--add-data", f"{asset_dir}{sep}assets",
        # textual + pygame load data files and native libs dynamically; pull
        # everything in so the frozen binary is fully self-contained.
        "--collect-all", "textual",
        "--collect-all", "pygame",
        "--console",
        str(ROOT / "launch.py"),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
