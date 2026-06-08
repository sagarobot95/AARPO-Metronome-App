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


def _resolve_icon() -> str | None:
    """Return a path to the right icon for this OS, or None.

    Windows wants .ico, macOS wants .icns (generated on demand from the master
    PNG if a prebuilt one isn't present). Linux binaries have no embedded icon.
    """
    img = ROOT / "img"
    if sys.platform.startswith("win"):
        ico = img / "aarpo.ico"
        return str(ico) if ico.exists() else None
    if sys.platform == "darwin":
        icns = img / "aarpo.icns"
        if icns.exists():
            return str(icns)
        master = img / "aarpo-icon.png"
        if master.exists():
            try:  # convert master PNG -> .icns at build time
                from PIL import Image

                Image.open(master).convert("RGBA").resize((1024, 1024)).save(icns)
                return str(icns)
            except Exception as exc:
                print(f"(icon) could not create .icns, building without icon: {exc}")
        return None
    return None  # Linux: no embedded binary icon


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
        "--collect-all", "textual_image",
        "--collect-all", "pygame",
        "--console",
    ]

    icon = _resolve_icon()
    if icon:
        cmd += ["--icon", icon]
        print(f"(icon) using {icon}")

    cmd.append(str(ROOT / "launch.py"))
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
