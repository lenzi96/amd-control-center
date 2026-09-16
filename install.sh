#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
SHARE_DIR="$HOME/.local/share/amd-control-center"
HICOLOR_DIR="$HOME/.local/share/icons/hicolor"
PIXMAPS_DIR="$HOME/.local/share/pixmaps"
AUTOSTART_DIR="$HOME/.config/autostart"

DESKTOP_DIR="$HOME/Desktop"
if [ -d "$HOME/Schreibtisch" ]; then
    DESKTOP_DIR="$HOME/Schreibtisch"
fi

echo "======================================================="
echo "   Installing AMD Software: Adrenalin Edition (Linux)  "
echo "======================================================="

mkdir -p "$BIN_DIR" "$APP_DIR" "$SHARE_DIR" "$PIXMAPS_DIR" "$AUTOSTART_DIR"

# 1. Install application files to ~/.local/share/amd-control-center
echo "→ Copying application files to $SHARE_DIR..."
cp -r "$DIR/amd_control_center" "$SHARE_DIR/"
cp "$DIR/main.py" "$SHARE_DIR/"
echo "[✓] Installed application core files"

# 2. Install standalone launcher to ~/.local/bin/amd-control-center
rm -f "$BIN_DIR/amd-control-center"
cat << 'LAUNCHER_EOF' > "$BIN_DIR/amd-control-center"
#!/usr/bin/env bash
# Standalone launcher for AMD Software: Adrenalin Edition

INSTALL_DIR="$HOME/.local/share/amd-control-center"
DEV_DIR="/run/media/julian/HDD/Linux/amd-control-center"

if [ -n "$AMD_DEV_DIR" ] && [ -d "$AMD_DEV_DIR" ]; then
    APP_DIR="$AMD_DEV_DIR"
elif [ -d "$INSTALL_DIR" ]; then
    APP_DIR="$INSTALL_DIR"
elif [ -d "$DEV_DIR" ]; then
    APP_DIR="$DEV_DIR"
else
    echo "Error: amd-control-center installation not found." >&2
    exit 1
fi

export PYTHONPATH="$APP_DIR:$PYTHONPATH"
exec python3 "$APP_DIR/main.py" "$@"
LAUNCHER_EOF
chmod 755 "$BIN_DIR/amd-control-center"
echo "[✓] Installed standalone binary to $BIN_DIR/amd-control-center"

# 3. Install Icons (Multi-Resolution PNGs + Scalable SVG + Pixmaps)
mkdir -p "$HICOLOR_DIR/scalable/apps"
cp "$DIR/amd_control_center/resources/app_icon.svg" "$HICOLOR_DIR/scalable/apps/amd-control-center.svg"
cp "$DIR/amd_control_center/resources/app_icon.svg" "$PIXMAPS_DIR/amd-control-center.svg"

for sz in 16 24 32 48 64 128 256 512; do
    if [ -f "$DIR/amd_control_center/resources/app_icon_${sz}.png" ]; then
        mkdir -p "$HICOLOR_DIR/${sz}x${sz}/apps"
        cp "$DIR/amd_control_center/resources/app_icon_${sz}.png" "$HICOLOR_DIR/${sz}x${sz}/apps/amd-control-center.png"
    fi
done

if [ -f "$DIR/amd_control_center/resources/app_icon_256.png" ]; then
    cp "$DIR/amd_control_center/resources/app_icon_256.png" "$PIXMAPS_DIR/amd-control-center.png"
elif [ -f "$DIR/amd_control_center/resources/app_icon.png" ]; then
    cp "$DIR/amd_control_center/resources/app_icon.png" "$PIXMAPS_DIR/amd-control-center.png"
fi
echo "[✓] Installed application icons (multi-resolution PNGs and SVG)"

# 4. Install Desktop file to Application Menu
sed -e "s|^Icon=.*|Icon=amd-control-center|g" \
    -e "s|^Exec=.*|Exec=$BIN_DIR/amd-control-center|g" \
    "$DIR/amd-control-center.desktop" > "$APP_DIR/amd-control-center.desktop"
chmod +x "$APP_DIR/amd-control-center.desktop"
echo "[✓] Installed desktop file to $APP_DIR"

# 5. Install Desktop Shortcut on Desktop/Schreibtisch
if [ -d "$DESKTOP_DIR" ]; then
    cp "$APP_DIR/amd-control-center.desktop" "$DESKTOP_DIR/amd-control-center.desktop"
    chmod +x "$DESKTOP_DIR/amd-control-center.desktop"
    gio set "$DESKTOP_DIR/amd-control-center.desktop" metadata::trusted true 2>/dev/null || true
    echo "[✓] Installed desktop shortcut to $DESKTOP_DIR"
fi

# 6. Configure Autostart (System Tray)
cat << AUTO_EOF > "$AUTOSTART_DIR/amd-control-center.desktop"
[Desktop Entry]
Name=AMD Software: Adrenalin Edition
Comment=AMD Radeon GPU Control Center (System Tray)
GenericName=AMD GPU Control Center
Exec=$BIN_DIR/amd-control-center --tray
Icon=amd-control-center
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;System;
X-GNOME-Autostart-enabled=true
Hidden=false
StartupNotify=false
X-KDE-autostart-after=panel
AUTO_EOF
chmod 644 "$AUTOSTART_DIR/amd-control-center.desktop"
echo "[✓] Configured autostart in $AUTOSTART_DIR"

# 7. Update desktop & icon caches
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HICOLOR_DIR" 2>/dev/null || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 --noincremental 2>/dev/null || true
fi

echo ""
echo "Installation complete!"
echo "• Launch via terminal: 'amd-control-center'"
echo "• Launch via application menu: 'AMD Software: Adrenalin Edition'"
echo "• Autostart enabled on user login (--tray)"
