"""Self-installation: put SeasonFall into the OS application list.

After this runs, the user launches SeasonFall like any normal GUI app:
  - Linux:   app grid entry (~/.local/share/applications/seasonfall.desktop)
  - Windows: Start Menu shortcut (pythonw → no console window)
  - macOS:   ~/Applications/SeasonFall.app bundle

Terminal is only needed for the very first bootstrap.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import config_dir
from .util import is_frozen, is_linux, is_macos, is_windows


def repo_root() -> str:
    return str(Path(__file__).resolve().parent.parent)


def _ensure_qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication(sys.argv[:1])
    return app


def _save_icons() -> dict:
    """Render the procedural snowflake icon to the formats each OS wants."""
    from . import settings_gui

    _ensure_qt_app()
    base = config_dir()
    base.mkdir(parents=True, exist_ok=True)
    out: dict = {}
    png = base / "icon.png"
    if settings_gui.app_icon().pixmap(512, 512).save(str(png), "PNG"):
        out["png"] = png
    if is_windows():
        ico = base / "icon.ico"
        try:
            if settings_gui.app_icon().pixmap(256, 256).save(str(ico), "ICO"):
                out["ico"] = ico
        except Exception:
            pass
    if is_macos():
        icns = base / "icon.icns"
        try:
            if settings_gui.app_icon().pixmap(512, 512).save(str(icns), "ICNS"):
                out["icns"] = icns
        except Exception:
            pass
    return out


# --------------------------------------------------------------------------- #
#  Linux — freedesktop app grid entry
# --------------------------------------------------------------------------- #
def _install_linux(icons: dict) -> list[str]:
    apps_dir = Path.home() / ".local" / "share" / "applications"
    apps_dir.mkdir(parents=True, exist_ok=True)
    desktop = apps_dir / "seasonfall.desktop"
    icon = icons.get("png", "")
    if is_frozen():
        exec_line = f'Exec="{os.path.abspath(sys.executable)}"\n'
        path_line = ""
    else:
        runsh = Path(repo_root()) / "run.sh"
        try:
            runsh.chmod(runsh.stat().st_mode | 0o755)
        except OSError:
            pass
        exec_line = f'Exec="{runsh}" settings\n'
        path_line = f"Path={repo_root()}\n"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        "Name=SeasonFall\n"
        "GenericName=Falling Seasons\n"
        "Comment=Snow, petals, sparks and leaves over your desktop\n"
        "Keywords=snow;season;overlay;winter;autumn;desktop;\n"
        f"{exec_line}"
        f"{path_line}"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "StartupWMClass=SeasonFall\n"
        "Categories=Utility;Amusement;\n",
        encoding="utf-8")
    subprocess.run(["update-desktop-database", str(apps_dir)],
                   capture_output=True)
    return [f"app grid entry → {desktop}"]


# --------------------------------------------------------------------------- #
#  Windows — Start Menu shortcut (pythonw = GUI only, no console)
# --------------------------------------------------------------------------- #
def _install_windows(icons: dict) -> list[str]:
    base_menu = Path(os.environ.get("APPDATA", str(Path.home() / "AppData")))
    programs = base_menu / "Microsoft" / "Start Menu" / "Programs"
    programs.mkdir(parents=True, exist_ok=True)
    lnk = programs / "SeasonFall.lnk"

    python = os.path.abspath(sys.executable)
    pythonw = Path(python).with_name("pythonw.exe")
    if pythonw.exists():
        python = str(pythonw)
    ico = icons.get("ico", "")

    if is_frozen():
        # Packaged .exe: launch directly, no console, no repo working dir.
        target = os.path.abspath(sys.executable)
        arguments = "settings"
        workdir = str(Path.home())
    else:
        target = python
        arguments = "-m seasonfall settings"
        workdir = repo_root()

    icon_part = f"$s.IconLocation = '{ico}, 0'; " if ico else ""
    ps_script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{lnk}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.Arguments = '{arguments}'; "
        f"$s.WorkingDirectory = '{workdir}'; "
        f"{icon_part}"
        "$s.Description = 'SeasonFall - falling seasons for your desktop'; "
        "$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-ExecutionPolicy", "Bypass", "-Command", ps_script],
        capture_output=True, timeout=60)
    return [f"Start Menu shortcut → {lnk}"]


# --------------------------------------------------------------------------- #
#  macOS — .app bundle in ~/Applications
# --------------------------------------------------------------------------- #
_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>            <string>SeasonFall</string>
    <key>CFBundleDisplayName</key>     <string>SeasonFall</string>
    <key>CFBundleIdentifier</key>      <string>com.seasonfall.app</string>
    <key>CFBundleExecutable</key>      <string>SeasonFall</string>
    <key>CFBundleIconFile</key>        <string>{iconfile}</string>
    <key>CFBundlePackageType</key>     <string>APPL</string>
    <key>CFBundleShortVersionString</key> <string>{version}</string>
    <key>CFBundleInfoDictionaryVersion</key> <string>6.0</string>
    <key>NSHighResolutionCapable</key> <true/>
</dict>
</plist>
"""


def _install_macos(icons: dict) -> list[str]:
    if is_frozen():
        # PyInstaller --windowed already produced a real .app bundle.
        bundle = Path(sys.executable).resolve().parents[2]
        return [f"app bundle → {bundle}"]
    app_root = Path.home() / "Applications" / "SeasonFall.app"
    contents = app_root / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(parents=True, exist_ok=True)

    launcher = contents / "MacOS" / "SeasonFall"
    python = os.path.abspath(sys.executable)
    launcher.write_text(
        "#!/bin/bash\n"
        f'cd "{repo_root()}" && exec "{python}" -m seasonfall settings "$@"\n',
        encoding="utf-8")
    launcher.chmod(0o755)

    iconfile = "SeasonFall"
    if "icns" in icons:
        icons["icns"].rename(contents / "Resources" / "SeasonFall.icns")
    elif "png" in icons:
        png = contents / "Resources" / "SeasonFall.png"
        icons["png"].rename(png)
        iconfile = "SeasonFall.png"

    (contents / "Info.plist").write_text(
        _PLIST.format(iconfile=iconfile, version=__version__), encoding="utf-8")
    return [f"macOS app → {app_root}"]


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #
def install() -> list[str]:
    icons = _save_icons()
    if is_windows():
        return _install_windows(icons)
    if is_macos():
        return _install_macos(icons)
    return _install_linux(icons)


def remove() -> list[str]:
    removed = []
    if is_windows():
        base_menu = Path(os.environ.get("APPDATA", str(Path.home() / "AppData")))
        lnk = base_menu / "Microsoft" / "Start Menu" / "Programs" / "SeasonFall.lnk"
        if lnk.exists():
            lnk.unlink()
            removed.append(str(lnk))
    elif is_macos():
        app_root = Path.home() / "Applications" / "SeasonFall.app"
        if app_root.exists():
            import shutil
            shutil.rmtree(app_root, ignore_errors=True)
            removed.append(str(app_root))
    else:
        desktop = (Path.home() / ".local" / "share" / "applications"
                   / "seasonfall.desktop")
        if desktop.exists():
            desktop.unlink()
            removed.append(str(desktop))
    return removed
