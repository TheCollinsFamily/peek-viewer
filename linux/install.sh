#!/bin/sh
# Installs RFab Viewer for the current user, no root needed:
#   the program      ~/.local/opt/rfab-viewer/RFab Viewer
#   a command        ~/.local/bin/rfab-viewer
#   a menu entry and "Open With" for images and videos (~/.local/share/applications)
# Remove it again with ~/.local/opt/rfab-viewer/uninstall.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
OPT="$HOME/.local/opt/rfab-viewer"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"

mkdir -p "$OPT" "$BIN" "$APPS" "$ICONS"
cp "$HERE/RFab Viewer" "$OPT/RFab Viewer"
chmod +x "$OPT/RFab Viewer"
cp "$HERE/rfab-viewer.png" "$ICONS/rfab-viewer.png"
ln -sf "$OPT/RFab Viewer" "$BIN/rfab-viewer"
# The menu entry names the installed binary by its full path, so it works whether or not
# ~/.local/bin is on the PATH of the desktop session.
sed "s|^Exec=.*|Exec=\"$OPT/RFab Viewer\" %F|" "$HERE/rfab-viewer.desktop" > "$APPS/rfab-viewer.desktop"

cat > "$OPT/uninstall.sh" <<EOF
#!/bin/sh
rm -f "$APPS/rfab-viewer.desktop" "$BIN/rfab-viewer" "$ICONS/rfab-viewer.png"
rm -rf "$OPT"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" 2>/dev/null || true
echo "RFab Viewer removed."
EOF
chmod +x "$OPT/uninstall.sh"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed."
echo "  Run:      rfab-viewer picture.jpg    (or a folder), or open RFab Viewer from your app menu"
echo "  Default:  right-click an image > Open With > RFab Viewer"
echo "  Remove:   $OPT/uninstall.sh"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "  Note: $BIN is not on your PATH yet; the menu entry works regardless." ;;
esac
