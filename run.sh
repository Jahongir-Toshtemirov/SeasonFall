#!/usr/bin/env bash
# Launch SeasonFall (Linux & macOS). Sets up the environment on first run.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] && [ "${SEASONFALL_SKIP_SETUP:-}" != "1" ]; then
    bash install.sh
fi
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python -m seasonfall "$@"
fi
exec python3 -m seasonfall "$@"
