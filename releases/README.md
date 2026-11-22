# 📦 Releases

Ready-to-run SeasonFall packages — no Python, no terminal needed.

| OS | File | How to use |
|---|---|---|
| 🐧 **Linux** (Debian/Ubuntu) | `SeasonFall_*.deb` | `sudo apt install ./SeasonFall_*.deb` → launch **SeasonFall** from the app grid |
| 🪟 **Windows** | `SeasonFall-Windows.exe` | double-click — single file, nothing to install, fully offline (needs Windows 10/11 64-bit) |
| 🍎 **macOS** | `SeasonFall.app` / `SeasonFall-macOS.zip` | double-click (right-click → *Open* the first time for Gatekeeper) |
| 🤖 **Android** | `SeasonFall-Android.apk` | install → open app → **Set as live wallpaper** (battery-friendly; pauses when you leave the home screen) |

## Rebuilding

- **Linux `.deb`**: `packaging/build_deb.sh` (see its header for usage)
- **Windows `.exe`**: PyInstaller under Wine + Windows Python — see
  `.github/workflows/release.yml` for the exact recipe (also runs on every
  `v*` tag push and attaches fresh builds to GitHub Releases)
- **macOS icon**: `packaging/make_icns.py`

