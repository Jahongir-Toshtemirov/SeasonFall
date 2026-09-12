#!/usr/bin/env bash
# SeasonFall installer for Linux & macOS.
#   ./install.sh            # install + verify
#   ./install.sh --startup  # also register login autostart
set -uo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || { echo "Python 3 not found — install Python 3.9+ first."; exit 1; }
echo "==> Using $($PY --version 2>&1) at $(command -v "$PY")"

# 1) virtual environment (fall back to --user install if venv is unavailable)
if [ ! -x .venv/bin/python ]; then
    if "$PY" -m venv .venv >/dev/null 2>&1; then
        echo "==> Created virtual environment (.venv)"
    else
        rm -rf .venv
        echo "==> venv module unavailable (Debian/Ubuntu: sudo apt install python3-venv)"
        echo "    → falling back to a --user install"
    fi
fi
if [ -x .venv/bin/python ]; then PYBIN=.venv/bin/python; else PYBIN="$PY"; fi

# 2) dependency (PySide6)
echo "==> Installing PySide6 (this can take a minute)…"
if ! "$PYBIN" -m pip install -q -r requirements.txt >/dev/null 2>&1 \
   || ! "$PYBIN" -c "import PySide6" >/dev/null 2>&1; then
    rm -rf .venv
    PYBIN="$PY"
    "$PYBIN" -m pip install --user -q -r requirements.txt >/dev/null 2>&1 \
        || "$PYBIN" -m pip install --user -q --break-system-packages -r requirements.txt
fi

if ! "$PYBIN" -c "import PySide6" 2>/dev/null; then
    echo "ERROR: PySide6 is not importable — see README troubleshooting."
    exit 1
fi
echo "==> PySide6 OK"

# 3) Linux: xcb runtime libraries (required for the desktop overlay window)
if [ "$(uname -s)" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then
    QXCB="$("$PYBIN" -c 'import PySide6, os; print(os.path.join(os.path.dirname(PySide6.__file__), "Qt", "plugins", "platforms", "libqxcb.so"))' 2>/dev/null || true)"
    if [ -n "$QXCB" ] && ldd "$QXCB" 2>/dev/null | grep -q "not found"; then
        echo "==> Installing xcb runtime libraries (needed for the overlay)…"
        if command -v sudo >/dev/null 2>&1; then
            sudo apt-get install -y libxcb-cursor0 libxcb-icccm4 libxcb-image0 \
                libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-shape0 \
                || echo "!! Automatic install failed — run this manually:
   sudo apt install -y libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-shape0"
        fi
    else
        echo "==> xcb runtime libraries OK"
    fi
fi

# 4) register in the OS application list (launch like a normal app, no terminal)
echo "==> Adding SeasonFall to your app list…"
"$PYBIN" -m seasonfall install || true

# 5) optional autostart
if [ "${1:-}" = "--startup" ] || [ "${1:-}" = "startup" ]; then
    "$PYBIN" -m seasonfall startup on
fi

chmod +x run.sh SeasonFall.py 2>/dev/null || true

cat <<'EOF'

SeasonFall is installed! ❄🌸☀🍂

  • Open "SeasonFall" from your app list / Start Menu (no terminal needed)
  • ./run.sh settings      # same thing from a terminal
  • ./run.sh overlay       # start the desktop overlay directly
  • ./run.sh startup on    # fall automatically at login
  • ./run.sh quit          # stop a running overlay
EOF
