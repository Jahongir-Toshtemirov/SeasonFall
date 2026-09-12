#!/usr/bin/env python3
"""SeasonFall — universal launcher (works on Windows / macOS / Linux).

    python3 SeasonFall.py            # macOS / Linux
    py SeasonFall.py                 # Windows

First run bootstraps everything: creates a local virtual environment,
installs the single dependency (PySide6), then starts the app.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(ROOT, ".venv")


def _venv_python():
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def _import_ok(py):
    try:
        return subprocess.call([py, "-c", "import PySide6"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL) == 0
    except OSError:
        return False


def _pip_install(py, extra=()):
    req = os.path.join(ROOT, "requirements.txt")
    base = [py, "-m", "pip", "install"]
    for attempt in (
        base + list(extra) + ["-r", req],
        base + list(extra) + ["--user", "-r", req],
        base + ["--user", "--break-system-packages", "-r", req],
    ):
        try:
            if subprocess.call(attempt) == 0 and _import_ok(py):
                return True
        except OSError:
            continue
    return False


def resolve_python():
    """Return a python executable that can import PySide6."""
    py = _venv_python()
    if os.path.exists(py):
        if _import_ok(py):
            return py
        print("[SeasonFall] installing the GUI toolkit (PySide6) into .venv …")
        if _pip_install(py):
            return py
        shutil.rmtree(VENV, ignore_errors=True)   # broken venv → discard

    print("[SeasonFall] first run — creating a private environment (.venv) …")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", VENV])
        py = _venv_python()
        if _pip_install(py):
            return py
        shutil.rmtree(VENV, ignore_errors=True)
    except (subprocess.CalledProcessError, OSError):
        shutil.rmtree(VENV, ignore_errors=True)

    print("[SeasonFall] venv unavailable — installing into your user site …")
    if _pip_install(sys.executable, extra=("--user",)):
        return sys.executable

    print("[SeasonFall] ERROR: could not install PySide6 automatically.")
    print("             Install it manually, then rerun:")
    print("                 pip install PySide6")
    sys.exit(1)


def main():
    os.chdir(ROOT)
    py = resolve_python()
    return subprocess.call([py, "-m", "seasonfall"] + sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
