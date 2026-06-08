#!/usr/bin/env bash
# Installs a double-clickable "AARPO Metronome" application icon on Linux.
#
# It writes a .desktop entry (with absolute paths filled in for THIS machine) to
# your applications menu and your Desktop, so you can launch the metronome like a
# normal app. Run this once:  ./install-linux.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
ENTRY_NAME="aarpo-metronome.desktop"

mkdir -p "$APPS_DIR"
chmod +x "$DIR/run.sh" "$DIR/start-linux.sh"

write_entry() {
  cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=AARPO Metronome
Comment=A terminal metronome with BPM, accents, subdivisions and tap tempo
Exec="$DIR/start-linux.sh"
Icon=$DIR/img/aarpo-icon.png
Path=$DIR
Terminal=false
Categories=AudioVideo;Audio;Music;
Keywords=metronome;tempo;bpm;music;practice;
EOF
  chmod +x "$1"
}

write_entry "$APPS_DIR/$ENTRY_NAME"
echo "Installed to applications menu: $APPS_DIR/$ENTRY_NAME"

if [ -d "$DESKTOP_DIR" ]; then
  write_entry "$DESKTOP_DIR/$ENTRY_NAME"
  # GNOME requires the desktop launcher to be marked trusted.
  command -v gio >/dev/null 2>&1 && \
    gio set "$DESKTOP_DIR/$ENTRY_NAME" metadata::trusted true 2>/dev/null || true
  echo "Placed launcher on Desktop: $DESKTOP_DIR/$ENTRY_NAME"
  echo "  (If it shows a warning, right-click it and choose 'Allow Launching'.)"
fi

command -v update-desktop-database >/dev/null 2>&1 && \
  update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Done. Look for 'AARPO Metronome' in your apps or on your Desktop."
