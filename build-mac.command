#!/bin/bash
# Double-click on macOS to build a standalone AARPO Metronome binary.
# Produces dist/aarpo-metronome — a self-contained executable that runs without
# Python installed. Build on the Mac you want to target (Apple Silicon or Intel);
# the binary matches that machine's CPU.
set -e
cd "$(dirname "$0")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3 is required to build. Install it from https://www.python.org/downloads/"
  read -n 1 -s -r -p "Press any key to close…"; exit 1
fi

venv_ok() { [ -x .venv/bin/python ] && \
  .venv/bin/python -c "import textual, pygame, PyInstaller" >/dev/null 2>&1; }

if ! venv_ok; then
  echo "Setting up build environment…"
  rm -rf .venv
  "$PY" -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt pyinstaller
else
  source .venv/bin/activate
fi

python build.py

echo
echo "✅ Build complete:  dist/aarpo-metronome"
echo "   Double-click it (or run ./dist/aarpo-metronome) to start — no Python needed."
read -n 1 -s -r -p "Press any key to close…"
