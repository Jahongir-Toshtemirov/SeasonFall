# 🌨️ SeasonFall

**Falling seasons for your desktop** — snow ❄ in winter, cherry petals 🌸 in spring,
sun sparks ☀ in summer, tumbling leaves 🍂 in autumn… plus holiday surprises 🎄🎃💖.
A transparent, always-on-top, **click-through** overlay paints the current season
over your whole desktop while you keep working.

Works on **Windows, macOS and Linux** — one Python script, no build step.

```bash
git clone https://github.com/<you>/SeasonFall.git
cd SeasonFall
python3 SeasonFall.py          # Windows:  py SeasonFall.py
```

The first run bootstraps a private environment, installs its single dependency
(**PySide6 / Qt6**), **adds "SeasonFall" to your app list** (Linux app grid /
Windows Start Menu / macOS `~/Applications`), and opens the season picker.
From then on you launch it like any normal app — **no terminal needed**.
Pick a season, tune the feel, answer the *"start at login?"* question —
the window closes itself and the season begins to fall. 🍃

---

## ✨ Features

| | |
|---|---|
| ❄️ **4 seasons + Auto** | Auto follows the calendar (honours your hemisphere) |
| 🧪 **Mix mode** | Multi-select **any combination** — snow+petals+leaves at the same time; every card toggles, the last one can't be removed |
| 🎄 **Holiday surprises** | Christmas (gifts, candy canes, snow), Halloween (bats, pumpkins, leaves), Valentine (hearts, petals) — join *any* mix near the date |
| 🌸 **Per-season particles** | 6-arm dendrite snowflakes, soft slush, frost twinkles, cherry petals, spring drizzle, sun sparks, heat glitter, fireflies, tumbling leaves, glowing golden leaves, hearts, bats, pumpkins, gifts, candy canes |
| ♾️ **Infinite & constant** | Particle count **never** changes — not on heavy load, not over hours. Sub-stepped physics keeps motion exact even if FPS drops; a sprite-cache renderer blits pre-rendered shapes instead of redrawing vectors |
| 🎚️ **Full control** | Intensity, speed, wind, size/thickness, opacity, sway, golden-leaf share, FPS cap, quality presets, optional adaptive quality (off by default) |
| 🖱️ **Alive** | Wind gusts, depth parallax, 3D leaf tumbling, cursor pushes particles around |
| 🪟 **Desktop friendly** | Click-through overlay (clicks land on your apps), multi-monitor, primary-monitor mode, single-instance guaranteed (a second start *adopts* the running one instead of doubling) |
| 🔋 **Considerate** | Auto-pauses on battery (optional), claymorphism UI with live preview |
| 🚀 **Startup apps** | One-click login autostart: Windows registry (invisible VBS launcher), macOS LaunchAgent, XDG autostart |
| 🧰 **CLI** | `settings`, `overlay`, `pause`, `resume`, `quit`, `status`, `startup on/off`, `install`, `uninstall`, `smoke` |

---

## 🚀 Install & run

### 📦 Ready-made packages (recommended — no Python needed)

See the [`releases/`](releases/) folder and the GitHub **Releases** page:

| OS | File | Install |
|---|---|---|
| 🐧 Linux (Debian/Ubuntu) | `SeasonFall_1.1.0_amd64.deb` | `sudo apt install ./SeasonFall_1.1.0_amd64.deb` → launch **SeasonFall** from the app grid |
| 🪟 Windows | `SeasonFall-Windows.exe` | double-click (single file, fully offline) |
| 🍎 macOS | `SeasonFall.app` | double-click (or drag into Applications) |

### From source

### Linux
```bash
./install.sh          # or: bash install.sh
./run.sh              # season picker GUI
./run.sh menu         # add an entry to your app menu (optional)
./run.sh startup on   # launch at login (optional)
```
<details>
<summary>Wayland users (GNOME on Ubuntu etc.)</summary>

The overlay is drawn through **XWayland** so it can stay above everything and
remain click-through even in GNOME-Wayland sessions. Qt's xcb plugin needs a
few standard runtime libraries; the installer installs them for you, or run:

```bash
sudo apt install -y libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
    libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-shape0
```
</details>

### macOS
```bash
./install.sh          # or double-click SeasonFall.command
./run.sh
```
The overlay appears above normal windows. (macOS keeps true full-screen apps on
their own space — the snow shows on your normal desktop.)

### Windows
```bat
install.bat
run.bat
```
Registering login autostart uses the per-user registry Run key — no admin needed.

> **No internet on the target machine?** Install once where you have network:
> `pip install PySide6`, then copy the repo + your user-site wheel cache, or
> simply run `pip install PySide6` in the target's Python.

---

## 🎛️ The settings window

- **Season cards** — Auto, Winter, Spring, Summer, Autumn (accent colour follows
  the season everywhere in the UI)
- **Live preview** — the mini-canvas runs the *real* engine; every slider move
  is visible instantly, and if the overlay is already running it updates live
- **Fall feel** — Intensity, Speed, Wind (left ↔ right), Size / thickness,
  Opacity, Sway, Golden-leaves share (autumn)
- **Behaviour** — tumbling/3D flip, cursor interaction, spring drizzle,
  click-through, pause-on-battery, quality, FPS, monitors
- **▶ Start & Enjoy** — saves, asks about login autostart (once), closes itself,
  and the season keeps falling

### Hotkeys (only when *click-through* is off)
| Key | Action |
|---|---|
| `Esc` | quit overlay |
| `Space` | pause / resume |

When click-through is on, use the CLI (`run.sh quit`, `run.sh pause`) — or
temporarily untick click-through.

---

## 🧰 CLI reference

```
python -m seasonfall                # smart: first run → settings, else overlay
python -m seasonfall settings       # open the settings window
python -m seasonfall overlay        # run the overlay
python -m seasonfall install        # (re)register the app-list/Start-Menu entry
python -m seasonfall --season autumn --density 60 --wind 30   # one-off override
python -m seasonfall pause | resume | quit | status
python -m seasonfall startup on | off | status
python -m seasonfall uninstall      # remove app entry + autostart + settings
python -m seasonfall smoke          # headless self-test (renders all seasons)
```

Settings live in:
- Linux: `~/.config/SeasonFall/config.json`
- macOS: `~/Library/Application Support/SeasonFall/config.json`
- Windows: `%APPDATA%\SeasonFall\config.json`

---

## 🏗️ How it works

```
SeasonFall.py ──▶ seasonfall/__main__.py ──▶ settings_gui.py (configurator)
                    │                              │
                    │                              ├─ OverlayManager (same process)
                    │                              └─ IPC reload → running overlay
                    └──▶ overlay.py  OverlayManager
                           ├─ one SeasonOverlay per screen
                           │    transparent · topmost · click-through · frameless
                           └─ engine.py  ParticleField
                                physics (depth, gusts, sway, tumble, mouse)
                                + QPainter renderers per particle kind
```

- **Depth parallax** — every particle has `z ∈ [0.15, 1]`: far ones are smaller,
  slower, dimmer, sway less — the falling feels 3-dimensional
- **Wind model** — steady wind + layered sine gusts; rain slants with it
- **Adaptive quality** — frame-time EMA vs. FPS budget silently scales particle count
- **Single instance** — a local socket (`seasonfall-<user>`) carries
  `reload / pause / resume / quit / status`

## 🖥️ How it works on each OS (full chain)

### 🐧 Linux
```
install.sh
  ├─ no python3?        → installs python3 + venv + pip (apt / dnf / pacman / zypper, sudo)
  ├─ creates .venv      → pip installs PySide6 into it (falls back to pip --user)
  ├─ installs xcb libs  → libxcb-cursor0, icccm4, image0, keysyms1, render-util0,
  │                       xinerama0, shape0  (needed by Qt's xcb plugin)
  └─ registers the app  → ~/.local/share/applications/seasonfall.desktop + icon.png
Overlay runtime
  ├─ Qt platform = xcb  → the overlay is an X11 window even on GNOME/KDE-Wayland,
  │                       drawn by **XWayland**: real positioning, keep-above
  │                       (_NET_WM_STATE_ABOVE) and click-through (empty input region)
  ├─ one frameless ARGB QWidget per monitor (WA_TranslucentBackground + Tool +
  │   WindowStaysOnTopHint + WindowTransparentForInput)
  ├─ QPainter paints cached sprite pixmaps with per-particle opacity/rotation
  └─ autostart: ~/.config/autostart/seasonfall.desktop → run.sh --overlay
```
Notes: works on X11 sessions natively; on Wayland it rides XWayland (GNOME/KDE
compose ARGB X11 windows with true per-pixel alpha).

### 🍎 macOS
```
install.sh (or double-click SeasonFall.command)
  ├─ no python3?        → triggers xcode-select --install (system popup) and waits
  ├─ creates .venv      → pip installs PySide6 (macOS arm64/x86_64 wheels)
  └─ registers the app  → ~/Applications/SeasonFall.app
                          Contents/MacOS/SeasonFall (bash launcher → venv python)
                          Contents/Info.plist + .icns/.png icon
Overlay runtime
  ├─ frameless translucent NSWindow via Qt: WindowStaysOnTopHint → floating level,
  │   WindowTransparentForInput → NSWindow.ignoresMouseEvents = true (click-through)
  ├─ the app list entry opens the settings GUI (normal window, Dock icon)
  └─ autostart: ~/Library/LaunchAgents/com.seasonfall.app.plist (RunAtLoad) →
      bash -c 'cd <repo> && exec <venv-python> -m seasonfall --overlay'
```
Notes: the overlay shows above normal windows; macOS keeps true full-screen
spaces on top of it (that's an OS rule).

### 🪟 Windows
```
install.bat (right-click → Run)
  ├─ no Python?         → winget install Python.Python.3.12
  │                       fallback: downloads python.org installer silently
  │                       (/quiet InstallAllUsers=0 PrependPath=1)
  ├─ creates .venv      → pip installs PySide6 (Windows wheels)
  └─ registers the app  → Start Menu shortcut "SeasonFall.lnk"
                          TargetPath = pythonw.exe (GUI only — NO console window)
                          Icon = generated .ico, WorkingDirectory = repo
Overlay runtime
  ├─ frameless layered window: WS_EX_LAYERED | WS_EX_TRANSPARENT |
  │   WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE → always-on-top, click-through,
  │   never steals focus, no taskbar entry
  ├─ Qt raster engine paints the sprites; DWM composites the per-pixel alpha
  └─ autostart: HKCU\Software\Microsoft\Windows\CurrentVersion\Run →
      wscript.exe seasonfall_overlay.vbs (invisible: sets working dir, runs
      pythonw -m seasonfall --overlay with zero console flash)
```
Notes: everything is per-user (HKCU + %APPDATA%) — no admin rights needed.

### The shared core
```
config.json (per-user) → OverlayManager → one SeasonOverlay per screen
ParticleField: fixed population → sub-stepped physics (gusts, sway, tumble,
mouse repel) → sprite-cache QPainter rendering → update() at the FPS cap
IPC (named local socket): reload / pause / resume / quit / status
```

## 🧪 Self-test

```bash
python -m seasonfall smoke
```
Simulates + renders all 7 seasons offscreen, saves PNGs to `/tmp/seasonfall_smoke/`,
and verifies config persistence + autostart registration. `SMOKE: PASS` = healthy.

---

## ❓ Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not load the Qt platform plugin "xcb"` (Linux) | Install the libs listed in the Wayland box above |
| Overlay is a rectangle / no transparency | You're without a compositor or on Wayland-native QPA — SeasonFall auto-selects xcb/XWayland; check `echo $QT_QPA_PLATFORM` |
| App missing from the app list / moved the repo folder | `run.sh install` (or `python -m seasonfall install`) re-registers it |
| Snow doesn't start at login | `run.sh startup on`; if you *moved the repo folder*, re-run it |
| Too heavy on CPU | lower **Quality** to medium/low, FPS to 30, disable mouse interaction |
| Two overlays running | impossible — single-instance IPC; `run.sh status` shows the live one |

## 📄 License

MIT — see [LICENSE](LICENSE). Built with ❤️, Python and Qt.
