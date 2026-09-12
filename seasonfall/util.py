"""Small shared helpers for SeasonFall."""
from __future__ import annotations

import os
import sys

# Verbose logging when SEASONFALL_DEBUG=1
DEBUG = os.environ.get("SEASONFALL_DEBUG") == "1"


def dbg(*args) -> None:
    if DEBUG:
        print("[SeasonFall:debug]", *args, flush=True)


def log(*args) -> None:
    print("[SeasonFall]", *args, flush=True)


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_frozen() -> bool:
    """True when running from a packaged bundle (.deb binary / .exe / .app)."""
    return bool(getattr(sys, "frozen", False))
