#!/bin/bash
set -e

echo "Uninstalling AMD Software: Adrenalin Edition..."
rm -f "$HOME/.local/bin/amd-control-center"
rm -rf "$HOME/.local/share/amd-control-center"
rm -f "$HOME/.local/share/applications/amd-control-center.desktop"
rm -f "$HOME/.config/autostart/amd-control-center.desktop"
rm -f "$HOME/Desktop/amd-control-center.desktop"
rm -f "$HOME/Schreibtisch/amd-control-center.desktop"

HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
rm -f "$HICOLOR_DIR/scalable/apps/amd-control-center.svg"
for sz in 16 24 32 48 64 128 256 512; do
    rm -f "$HICOLOR_DIR/${sz}x${sz}/apps/amd-control-center.png"
done
rm -f "$HOME/.local/share/pixmaps/amd-control-center.png"
rm -f "$HOME/.local/share/pixmaps/amd-control-center.svg"
rm -f "$HOME/.local/share/kio/servicemenus/amd-control-center.desktop"

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HICOLOR_DIR" 2>/dev/null || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental 2>/dev/null || true
fi

echo "Uninstallation complete."
