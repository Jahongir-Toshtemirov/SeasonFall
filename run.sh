#!/usr/bin/env bash
# Launch SeasonFall (Linux & macOS). Sets up the environment on first run.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] && [ "${SEASONFALL_SKIP_SETUP:-}" != "1" ]; then
    if python3 -c "import PySide6" >/dev/null 2>&1; then
        :   # dependency already available — skip the installer
    else
        bash install.sh
    fi
fi
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m seasonfall "$@"
fi
exec python3 -m seasonfall "$@"
