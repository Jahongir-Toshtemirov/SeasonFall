"""Login autostart integration: Windows registry, macOS LaunchAgent, XDG autostart."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .util import is_linux, is_macos, is_windows

WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_VALUE = "SeasonFall"
PLIST_LABEL = "com.seasonfall.app"


def launch_command() -> list[str]:
    python = os.path.abspath(sys.executable)
    if is_windows():
        pythonw = Path(python).with_name("pythonw.exe")
        if pythonw.exists():
            python = str(pythonw)
    return [python, "-m", "seasonfall", "--overlay"]


def _quoted(args: list[str]) -> str:
    return " ".join(f'"{a}"' if (" " in a or a.startswith("-") is False and " " in a) else a
                    for a in args)


def _macos_plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"


def _linux_autostart_dir() -> Path:
    override = os.environ.get("SEASONFALL_AUTOSTART_DIR")
    if override:
        return Path(override)
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart"


_DESKTOP_TEMPLATE = """[Desktop Entry]
Type=Application
Version=1.0
Name=SeasonFall
Comment=Falling seasons for your desktop (snow, petals, sparks, leaves)
Exec="{python}" -m seasonfall --overlay
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;Amusement;
"""

_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>-m</string>
        <string>seasonfall</string>
        <string>--overlay</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""


def is_enabled() -> bool:
    try:
        if is_windows():
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.QueryValueEx(key, WIN_VALUE)
            return True
        if is_macos():
            return _macos_plist().exists()
        return (_linux_autostart_dir() / "seasonfall.desktop").exists()
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> tuple[bool, str]:
    try:
        cmd = launch_command()
        if is_windows():
            import winreg

            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY) as key:
                winreg.SetValueEx(key, WIN_VALUE, 0, winreg.REG_SZ,
                                  " ".join(f'"{a}"' for a in cmd))
            return True, "Windows registry Run key"
        if is_macos():
            plist = _macos_plist()
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_text(_PLIST_TEMPLATE.format(label=PLIST_LABEL, python=cmd[0]),
                             encoding="utf-8")
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
            subprocess.run(["launchctl", "load", str(plist)], capture_output=True)
            return True, "macOS LaunchAgent"
        path = _linux_autostart_dir() / "seasonfall.desktop"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DESKTOP_TEMPLATE.format(python=cmd[0]), encoding="utf-8")
        return True, f"XDG autostart ({path})"
    except Exception as exc:
        return False, str(exc)


def disable() -> tuple[bool, str]:
    try:
        if is_windows():
            import winreg

            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY, 0,
                                    winreg.KEY_SET_VALUE) as key:
                    winreg.DeleteValue(key, WIN_VALUE)
            except FileNotFoundError:
                pass
            return True, "Windows registry Run key"
        if is_macos():
            plist = _macos_plist()
            if plist.exists():
                subprocess.run(["launchctl", "unload", str(plist)],
                               capture_output=True)
                plist.unlink()
            return True, "macOS LaunchAgent"
        path = _linux_autostart_dir() / "seasonfall.desktop"
        if path.exists():
            path.unlink()
            return True, f"removed {path}"
        return True, "autostart was not enabled"
    except Exception as exc:
        return False, str(exc)
