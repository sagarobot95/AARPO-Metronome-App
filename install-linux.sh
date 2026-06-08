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
ICON_NAME="aarpo-metronome"

mkdir -p "$APPS_DIR"
chmod +x "$DIR/run.sh" "$DIR/start-linux.sh"

# Install the icon into the user's icon theme and refer to it by NAME. Referring
# to a themed name (not an absolute path) is what GNOME's app grid resolves
# reliably — an absolute path that contains a space often falls back to a generic
# icon. xdg-icon-resource also refreshes the icon cache for us.
ICON_REF="$ICON_NAME"
if command -v xdg-icon-resource >/dev/null 2>&1; then
  for size in 256 512; do
    src="$DIR/img/aarpo-${size}.png"
    [ -f "$src" ] && xdg-icon-resource install --novendor --size "$size" "$src" "$ICON_NAME" 2>/dev/null || true
  done
else
  # Fallback: drop the PNG straight into the hicolor theme.
  dest="$HOME/.local/share/icons/hicolor/512x512/apps"
  mkdir -p "$dest"
  cp -f "$DIR/img/aarpo-512.png" "$dest/$ICON_NAME.png" 2>/dev/null || ICON_REF="$DIR/img/aarpo-icon.png"
  command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

write_entry() {
  cat > "$1" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=AARPO Metronome
Comment=A terminal metronome with BPM, accents, subdivisions and tap tempo
Exec="$DIR/start-linux.sh"
Icon=$ICON_REF
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
