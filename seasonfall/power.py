"""Battery / power-source detection (best effort, cross platform).

Returns True when running on battery, False on AC power, None when unknown.
"""
from __future__ import annotations

import glob
import os
import subprocess

from .util import is_macos, is_windows


def on_battery() -> bool | None:
    try:
        if is_windows():
            return _on_battery_windows()
        if is_macos():
            return _on_battery_macos()
        return _on_battery_linux()
    except Exception:
        return None


def _on_battery_windows() -> bool | None:
    import ctypes

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("Reserved1", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    sps = SYSTEM_POWER_STATUS()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
        return None
    if sps.BatteryFlag & 128:  # no system battery
        return None
    return sps.ACLineStatus == 0


def _on_battery_macos() -> bool | None:
    out = subprocess.run(
        ["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5
    ).stdout.lower()
    if "no batteries" in out or "battery" not in out:
        return None
    if "discharging" in out:
        return True
    if "charging" in out or "ac power" in out or "finishing charge" in out:
        return False
    return None


def _on_battery_linux() -> bool | None:
    statuses = []
    for path in glob.glob("/sys/class/power_supply/*/status"):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                statuses.append(fh.read().strip().lower())
        except OSError:
            continue
    if not statuses:
        return None
    if "discharging" in statuses:
        return True
    # Desktops / no battery report "Unknown" only.
    known = [s for s in statuses if s in ("charging", "full", "not charging", "discharging")]
    if known:
        return False
    return None


def battery_hint() -> str:
    state = on_battery()
    if state is None:
        return "power source unknown"
    return "on battery" if state else "on AC power"
