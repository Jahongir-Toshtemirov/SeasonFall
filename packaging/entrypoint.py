"""PyInstaller entry point — frozen builds (Linux .deb binary / .exe / .app).

The source-repo launcher (SeasonFall.py) bootstraps a virtualenv, which makes
no sense inside a packaged bundle; frozen builds run the app directly.
"""
import sys

from seasonfall.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
