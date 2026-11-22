# 📦 Releases

Ready-to-run SeasonFall packages — no Python, no terminal needed.

| OS | File | How to use |
|---|---|---|
| 🐧 **Linux** (Debian/Ubuntu) | `SeasonFall_1.2.0_amd64.deb` | `sudo apt install ./SeasonFall_1.2.0_amd64.deb` → launch **SeasonFall** from the app grid |
| 🪟 **Windows** | `SeasonFall-Windows.exe` | double-click — single file, nothing to install, fully offline (needs Windows 10/11 64-bit) |
| 🍎 **macOS** | `SeasonFall.app` | double-click it (right-click → *Open* the first time for Gatekeeper), or drag into `Applications`. Auto-installs its toolkit into your user Python on first run (~70 MB, needs internet once; if macOS asks to install *Command Line Tools*, accept — that provides `python3`) |

## Rebuilding

- **Linux `.deb`**: `packaging/build_deb.sh` (see its header for usage)
- **Windows `.exe`**: PyInstaller under Wine + Windows Python — see
  `.github/workflows/release.yml` for the exact recipe (also runs on every
  `v*` tag push and attaches fresh builds to GitHub Releases)
- **macOS icon**: `packaging/make_icns.py`

