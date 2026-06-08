#!/usr/bin/env bash
# Linux double-click launcher.
#
# When launched from a file manager there is usually no terminal attached, so
# this script opens one of the common terminal emulators and runs the app inside
# it. If it is already running in a terminal, it just runs the app directly.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_here() {
  cd "$DIR"
  exec ./run.sh
}

# Already attached to a terminal? Just run.
if [ -t 1 ]; then
  run_here
fi

# Otherwise find a terminal emulator and relaunch inside it.
INNER="cd \"$DIR\" && ./run.sh; echo; read -n 1 -s -r -p 'Press any key to close…'"

for term in x-terminal-emulator gnome-terminal konsole xfce4-terminal \
            mate-terminal tilix kitty alacritty xterm; do
  if command -v "$term" >/dev/null 2>&1; then
    case "$term" in
      gnome-terminal|tilix) exec "$term" -- bash -c "$INNER" ;;
      *)                    exec "$term" -e bash -c "$INNER" ;;
    esac
  fi
done

# No terminal emulator found — last resort, run in place.
run_here
