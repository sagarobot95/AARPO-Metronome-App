#!/usr/bin/env bash
# Cross-platform launcher for macOS / Linux.
# Creates an isolated virtual environment on first run, installs dependencies,
# then starts the metronome. Subsequent runs start instantly.
#
# It is self-healing: if the .venv is missing, broken, or was copied from a
# different OS (e.g. moved from Linux to macOS), it is rebuilt automatically.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

PY="python3"
command -v "$PY" >/dev/null 2>&1 || PY="python"

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Error: Python 3 is required but was not found."
  echo "On macOS, install it from https://www.python.org/downloads/ or with: brew install python"
  exit 1
fi

venv_ok() {
  [ -x "$VENV/bin/python" ] && \
    "$VENV/bin/python" -c "import textual, pygame" >/dev/null 2>&1
}

if ! venv_ok; then
  echo "Setting up AARPO Metronome (first run on this machine)…"
  rm -rf "$VENV"
  "$PY" -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r "$ROOT/requirements.txt"
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

exec python -m aarpo_metronome
