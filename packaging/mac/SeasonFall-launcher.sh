#!/bin/bash
# SeasonFall.app launcher — bootstraps PySide6 into the user's Python on
# first run, then starts the app. Works with macOS's bundled python3
# (Xcode Command Line Tools) or any python3 on PATH.
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
    osascript -e 'display dialog "SeasonFall needs Python 3 (free, one-time).\n\nClick OK to open the download page — install it, then open SeasonFall again." with title "SeasonFall"' >/dev/null 2>&1
    open "https://www.python.org/downloads/macos/" 2>/dev/null
    exit 1
fi

if ! "$PY" -c "import PySide6" >/dev/null 2>&1; then
    osascript -e 'display notification "Downloading the graphics toolkit (~70 MB), one moment…" with title "SeasonFall"' >/dev/null 2>&1
    if ! "$PY" -m pip install --user --quiet PySide6 >/dev/null 2>&1; then
        # newer pips refuse system dirs without this flag
        "$PY" -m pip install --user --quiet --break-system-packages PySide6 >/dev/null 2>&1 \
        || { osascript -e 'display dialog "Could not install the graphics toolkit.\n\nCheck your internet connection and open SeasonFall again." with title "SeasonFall"' >/dev/null 2>&1; exit 1; }
    fi
fi

export PYTHONPATH="$DIR"
exec "$PY" -m seasonfall "$@"
