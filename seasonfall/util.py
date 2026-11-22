"""Small shared helpers for SeasonFall."""
from __future__ import annotations

import os
import sys

# Verbose logging when SEASONFALL_DEBUG=1
DEBUG = os.environ.get("SEASONFALL_DEBUG") == "1"


def _safe_print(prefix: str, *args) -> None:
    """Print without crashing on Windows cp1252 / windowed (no-console) builds."""
    try:
        print(prefix, *args, flush=True)
    except UnicodeEncodeError:
        enc = getattr(sys.stdout, "encoding", None) or "ascii"
        text = " ".join(str(a) for a in args)
        try:
            print(prefix, text.encode(enc, "replace").decode(enc, "replace"),
                  flush=True)
        except Exception:
            pass
    except Exception:
        # runw.exe / piped stdio can raise OSError; never kill the app for a log line
        pass


def dbg(*args) -> None:
    if DEBUG:
        _safe_print("[SeasonFall:debug]", *args)


def log(*args) -> None:
    _safe_print("[SeasonFall]", *args)


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def is_frozen() -> bool:
    """True when running from a packaged bundle (.deb binary / .exe / .app)."""
    return bool(getattr(sys, "frozen", False))
