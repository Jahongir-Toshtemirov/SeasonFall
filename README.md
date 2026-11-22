# SeasonFall

SeasonFall makes it snow on your desktop. Petals in spring, sparks in summer,
leaves in autumn — and gifts, bats or hearts around the holidays.

It runs as a transparent layer over everything: the particles float above your
windows, but clicks go straight through, so you keep working while it snows.
Pick "auto" and it follows the calendar for you.

![SeasonFall — winter snow, spring petals and autumn leaves, rendered by the app](docs/preview.png)

Works on Windows, macOS, Linux and Android (live wallpaper).

## Install

Grab one file from the [`releases/`](releases/) folder. No Python needed.

| You have | Get | Do |
|---|---|---|
| Windows | `SeasonFall-Windows.exe` | Double-click it (Windows 10/11 64-bit). |
| macOS | `SeasonFall.app` | Double-click (first time: right-click → Open). |
| Ubuntu / Debian | `SeasonFall_*.deb` | `sudo apt install ./SeasonFall_*.deb`, then open **SeasonFall** from your app list. |
| Android | `SeasonFall-Android.apk` | Install → open SeasonFall → **Set as live wallpaper** (low-power; pauses in apps). |

On first launch a window opens where you pick a season, drag a few sliders and
press **Start & Enjoy**. Snow keeps falling after you close that window.

**How to stop or change it (no tech skills needed):**
- Look for the **snowflake icon near the clock** (system tray / menu bar).
  Right-click → **Settings…**, **Pause**, or **Quit SeasonFall**.
- Or just **open SeasonFall again** (double-click the `.exe`, or the Desktop /
  Start Menu shortcut) — the settings window comes back, with **Stop snowing**.

### Run from source instead

Works on any OS with Python 3.10 or newer:

```bash
git clone https://github.com/Jahongir-Toshtemirov/SeasonFall.git
cd SeasonFall
python3 SeasonFall.py        # Windows: py SeasonFall.py
```

The first run creates a private `.venv`, installs the single dependency
(PySide6 / Qt 6), adds SeasonFall to your app list and opens the picker.
After that you never need the terminal again.

## Controlling it

The settings window has:

- **Seasons** — winter, spring, summer, autumn, or *auto* (follows the date).
  Mix mode: tick several and they fall *at the same time* — snow, petals and
  leaves together is a look.
- **Holiday extras** — around December, Halloween and Valentine's Day, themed
  particles (gifts, candy canes, bats, pumpkins, hearts) join any season.
- **Feel** — how much falls, how fast, wind strength with natural gusts,
  particle size, opacity, sway, frame-rate cap, quality preset.
- **Behaviour** — cursor gently pushes particles around (can be turned off),
  click-through (can be turned off), auto-pause on battery, start at login.

The overlay is click-through by default: you can't click the snow, and the
snow can't get in your way. Turn click-through **off** if you want the
keyboard shortcuts — `Space` pauses, `Esc` quits.

### From the terminal

```bash
SeasonFall status        # what is falling, how many particles, fps
SeasonFall pause         # and: resume
SeasonFall quit
SeasonFall settings      # open the settings window
SeasonFall startup on    # launch at login (also a toggle in settings)
SeasonFall uninstall     # remove autostart and settings
```

Windows: use `SeasonFall.exe` instead of `SeasonFall`. From source:
`python3 -m seasonfall status`. Starting a second copy is harmless — it
notices the running one and leaves it alone.

### Where your settings live

Windows: `%APPDATA%\SeasonFall` · macOS: `~/Library/Application Support/SeasonFall`
· Linux: `~/.config/SeasonFall`.

Delete that folder for a factory reset, or just run `SeasonFall uninstall`.

## Good to know

- **Wayland (Ubuntu, GNOME…)** — the overlay runs through XWayland so it can
  stay above every window and stay click-through. The `.deb` pulls in the few
  libraries this needs; when running from source, `install.sh` sets them up.
- **Multi-monitor** — one overlay per screen, or primary screen only.
- **Laptops** — can pause themselves while on battery and resume on AC.
- **Privacy** — everything runs locally. No account, no telemetry, no network
  use at all — except the one-time toolkit download on the first run of the
  Windows/macOS packages.

## Building the packages yourself

See [`releases/README.md`](releases/README.md): one command each for the
`.deb`, the `.exe` (PyInstaller under Wine) and the macOS `.app` bundle.
Pushing a `v*` tag to GitHub also triggers Actions that build all three
natively and attach them to the release.

## License

MIT — see [LICENSE](LICENSE).
