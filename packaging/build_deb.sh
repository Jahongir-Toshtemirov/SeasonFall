#!/usr/bin/env bash
# Build the SeasonFall Linux .deb from a PyInstaller onefile binary.
#
# Usage:  packaging/build_deb.sh <SeasonFall-binary> [output-dir]
#
# Run on the target architecture (e.g. ubuntu-latest in CI for amd64).
set -euo pipefail

BIN="${1:?usage: build_deb.sh <SeasonFall-binary> [output-dir]}"
OUT="${2:-.}"
BIN="$(readlink -f "$BIN")"
cd "$(dirname "$0")/.."

VER="$(grep -oP '(?<=__version__ = ")[^"]+' seasonfall/__init__.py)"
ROOT="packaging/_debroot/seasonfall_${VER}_amd64"

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" \
         "$ROOT/usr/local/bin" \
         "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/icons/hicolor/512x512/apps" \
         "$ROOT/usr/share/doc/seasonfall"

# --- payload -------------------------------------------------------------- #
install -m 0755 "$BIN" "$ROOT/usr/local/bin/seasonfall"
install -m 0644 packaging/seasonfall.png \
    "$ROOT/usr/share/icons/hicolor/512x512/apps/seasonfall.png"
install -m 0644 LICENSE "$ROOT/usr/share/doc/seasonfall/copyright"

cat > "$ROOT/usr/share/applications/seasonfall.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=SeasonFall
GenericName=Falling Seasons
Comment=Snow, petals, sparks and leaves over your desktop
Keywords=snow;season;overlay;winter;autumn;desktop;
Exec=/usr/local/bin/seasonfall
Icon=seasonfall
Terminal=false
StartupWMClass=SeasonFall
Categories=Utility;Amusement;
Actions=Settings;

[Desktop Action Settings]
Name=Season Settings
Exec=/usr/local/bin/seasonfall settings
Icon=seasonfall
EOF

cat > "$ROOT/DEBIAN/control" <<EOF
Package: seasonfall
Version: ${VER}
Section: utils
Priority: optional
Architecture: $(dpkg --print-architecture)
Depends: libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-xinerama0, libxcb-shape0
Maintainer: SeasonFall <seasonfall@local>
Installed-Size: $(du -sk "$ROOT/usr" | cut -f1)
Description: Falling seasons for your desktop
 SeasonFall rains snow, petals, sparks, leaves and holiday specials over
 your desktop, with a mix-any-seasons mode, a settings GUI, click-through
 always-on-top overlays and optional login autostart.
 .
 This package bundles everything (PySide6 included) — no Python needed.
Homepage: https://github.com/seasonfall/seasonfall
EOF

cat > "$ROOT/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
exit 0
EOF
chmod 0755 "$ROOT/DEBIAN/postinst"

mkdir -p "$OUT"
dpkg-deb --build --root-owner-group "$ROOT" \
    "$OUT/SeasonFall_${VER}_$(dpkg --print-architecture).deb"
echo "built: $OUT/SeasonFall_${VER}_$(dpkg --print-architecture).deb"
