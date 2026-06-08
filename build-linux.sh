#!/usr/bin/env bash
# Build a standalone AARPO Metronome binary on Linux.
# Produces dist/aarpo-metronome — a self-contained executable that runs without
# Python installed.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python

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
echo "   Run ./dist/aarpo-metronome to start — no Python needed."
