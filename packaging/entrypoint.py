"""PyInstaller entry point — frozen builds (Linux .deb binary / .exe / .app).

The source-repo launcher (SeasonFall.py) bootstraps a virtualenv, which makes
no sense inside a packaged bundle; frozen builds run the app directly.
"""
from __future__ import annotations

import sys
import traceback


def _crash_dialog(exc: BaseException) -> None:
    """Surface fatal errors when --windowed hides the console on Windows."""
    detail = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()}"
    log_path = None
    try:
        import os
        from pathlib import Path

        if sys.platform.startswith("win"):
            base = Path(os.environ.get("APPDATA", Path.home())) / "SeasonFall"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "SeasonFall"
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME",
                                       Path.home() / ".config")) / "SeasonFall"
        base.mkdir(parents=True, exist_ok=True)
        log_path = base / "crash.log"
        log_path.write_text(detail, encoding="utf-8")
    except Exception:
        pass

    if sys.platform.startswith("win"):
        try:
            import ctypes

            text = "SeasonFall failed to start.\n\n" f"{type(exc).__name__}: {exc}\n"
            if log_path is not None:
                text += f"\nDetails saved to:\n{log_path}"
            ctypes.windll.user32.MessageBoxW(0, text, "SeasonFall", 0x10)
        except Exception:
            pass
    else:
        sys.stderr.write(detail + "\n")


if __name__ == "__main__":
    try:
        from seasonfall.__main__ import main

        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 — last-chance frozen crash UI
        _crash_dialog(exc)
        raise SystemExit(1) from exc
