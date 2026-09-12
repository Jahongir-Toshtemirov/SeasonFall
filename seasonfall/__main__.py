"""SeasonFall command line interface.

    python -m seasonfall              # smart start (first run → settings)
    python -m seasonfall settings     # open the settings window
    python -m seasonfall overlay      # run the desktop overlay
    python -m seasonfall quit         # stop a running overlay
    python -m seasonfall pause|resume
    python -m seasonfall status
    python -m seasonfall startup on|off|status
    python -m seasonfall menu         # (Linux) add app-menu entry
    python -m seasonfall smoke        # headless self-test
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .config import SEASON_KEYS, Config, config_dir
from .util import is_linux, log


def _linux_prefer_xcb() -> None:
    """On Linux run under XWayland (xcb) so positioning/topmost/click-through
    work even inside GNOME-Wayland sessions. Probe first, fall back silently."""
    if not is_linux() or not os.environ.get("DISPLAY"):
        return
    if os.environ.get("SEASONFALL_QPA"):
        os.environ["QT_QPA_PLATFORM"] = os.environ["SEASONFALL_QPA"]
        return
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    probe = ("import sys; from PySide6.QtWidgets import QApplication; "
             "app = QApplication(sys.argv[:1]); print(app.platformName())")
    env = dict(os.environ, QT_QPA_PLATFORM="xcb")
    try:
        r = subprocess.run([sys.executable, "-c", probe], env=env,
                           capture_output=True, timeout=25)
        if r.returncode == 0 and b"xcb" in r.stdout:
            os.environ["QT_QPA_PLATFORM"] = "xcb"
        else:
            print("[SeasonFall] hint: the desktop overlay runs best through XWayland, "
                  "but the Qt 'xcb' plugin could not load.\n"
                  "  Ubuntu/Debian fix:\n"
                  "    sudo apt install -y libxcb-cursor0 libxcb-icccm4 libxcb-image0 "
                  "libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-shape0")
    except Exception:
        pass


def _collect_overrides(args) -> dict:
    ov: dict = {}
    for key in ("season", "density", "speed", "wind", "size", "opacity"):
        val = getattr(args, key, None)
        if val is not None:
            ov[key] = val
    if args.no_mouse:
        ov["mouse_interact"] = False
    if args.no_click_through:
        ov["click_through"] = False
    return ov


# --------------------------------------------------------------------------- #
#  Runners
# --------------------------------------------------------------------------- #
def run_overlay(overrides: dict, duration: float | None = None) -> int:
    _linux_prefer_xcb()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    app.setApplicationName("SeasonFall")
    app.setApplicationDisplayName("SeasonFall")

    from .ipc import IpcServer, probe_status
    from .overlay import OverlayManager
    from . import settings_gui

    app.setWindowIcon(settings_gui.app_icon())

    status = probe_status()
    if status:
        log(f"overlay already running ({status.get('season_name', '?')}) — use "
            f"'python -m seasonfall settings' to change, '... quit' to stop")
        return 0

    cfg = Config.load()
    for key, val in overrides.items():
        setattr(cfg, key, val)
    cfg.sanitize()
    if overrides:
        cfg.save()          # explicit CLI choice persists
    log(f"starting overlay · {cfg.season} · quality {cfg.quality} · {cfg.fps} fps")

    manager = OverlayManager(cfg)
    IpcServer(manager)
    manager.start()
    if duration:
        QTimer.singleShot(int(duration * 1000), app.quit)
    return app.exec()


def run_settings() -> int:
    _linux_prefer_xcb()
    from PySide6.QtWidgets import QApplication

    from . import settings_gui

    app = QApplication(sys.argv[:1])
    app.setApplicationName("SeasonFall")
    app.setWindowIcon(settings_gui.app_icon())
    first_run = not Config.exists() or not Config.load().first_run_done
    if first_run:
        # first bootstrap → also put SeasonFall into the OS app list
        try:
            from . import appinstall
            for line in appinstall.install():
                log(line)
            log("open 'SeasonFall' from your app list any time — no terminal needed")
        except Exception as exc:  # never block the GUI on registration
            from .util import dbg
            dbg("app-list registration failed:", exc)
    win = settings_gui.SettingsWindow(first_run=first_run)
    win.show()
    return app.exec()


def _ipc_app():
    from PySide6.QtCore import QCoreApplication
    return QCoreApplication(sys.argv[:1])


def cmd_status() -> int:
    _ipc_app()
    from .ipc import probe_status
    st = probe_status()
    if not st:
        print("stopped")
        return 1
    print(f"running · season={st.get('season')} · particles={st.get('particles')} "
          f"· fps={st.get('fps')} · paused={st.get('paused')}")
    return 0


def cmd_startup(action: str) -> int:
    from . import startup
    if action == "on":
        ok, where = startup.enable()
        print(f"startup: {'enabled' if ok else 'FAILED'} ({where})")
        return 0 if ok else 1
    if action == "off":
        ok, where = startup.disable()
        print(f"startup: {'disabled' if ok else 'FAILED'} ({where})")
        return 0 if ok else 1
    state = "enabled" if startup.is_enabled() else "disabled"
    print(f"startup: {state}")
    return 0


def cmd_uninstall(assume_yes: bool) -> int:
    from . import startup
    if not assume_yes:
        try:
            answer = input("Remove SeasonFall startup entry and settings? [y/N] ")
        except EOFError:
            answer = "n"
        if answer.strip().lower() not in ("y", "yes"):
            print("cancelled")
            return 0
    _ipc_app()
    from .ipc import send_command
    send_command("quit")
    ok, where = startup.disable()
    print(f"startup: disabled ({where})" if ok else f"startup: {where}")
    from . import appinstall
    for path in appinstall.remove():
        print("removed:", path)
    import shutil
    shutil.rmtree(config_dir(), ignore_errors=True)
    print("settings removed:", config_dir())
    print("SeasonFall uninstalled. (The repo folder itself was kept.)")
    return 0


def cmd_install_app() -> int:
    """Register SeasonFall in the OS application list (GUI launcher)."""
    from . import appinstall
    try:
        for line in appinstall.install():
            print("✓", line)
        print("Launch 'SeasonFall' from your app list — no terminal needed.")
        return 0
    except Exception as exc:
        print("app-list registration failed:", exc)
        return 1


def cmd_smoke() -> int:
    """Headless self-test: simulate + render every season offscreen."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QApplication

    from . import seasons as S
    from . import startup
    from .engine import ParticleField

    app = QApplication([])
    out_dir = Path("/tmp/seasonfall_smoke")
    out_dir.mkdir(exist_ok=True)
    ok = True

    for key in ("winter", "spring", "summer", "autumn",
                "halloween", "christmas", "valentine"):
        cfg = Config(season=key, holiday_specials=False, density=95)
        spec = S.resolve_season(cfg, today=date(2026, 9, 12))
        field = ParticleField(cfg, spec, 640, 400, seed=42)
        for _ in range(120):
            field.tick(1 / 60.0, None)
        img = QImage(640, 400, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        field.paint(painter, transparent=True)
        painter.end()
        path = out_dir / f"{key}.png"
        img.save(str(path), "PNG")
        sampled = 0
        lit = 0
        for y in range(0, 400, 7):
            for x in range(0, 640, 7):
                sampled += 1
                if (img.pixel(x, y) >> 24) & 0xFF:
                    lit += 1
        frac = lit / max(1, sampled)
        flag = "OK" if frac >= 0.003 else "FAIL"
        if flag == "FAIL":
            ok = False
        print(f"{key:10s} particles={len(field.particles):4d} "
              f"lit={frac * 100:5.1f}%  {flag}  {path}")

    os.environ["SEASONFALL_CONFIG_DIR"] = str(out_dir / "cfg")
    c1 = Config(season="autumn", density=77)
    c1.save()
    c2 = Config.load()
    assert c2.season == "autumn" and c2.density == 77, "config roundtrip failed"
    print("config save/load roundtrip        OK")

    os.environ["SEASONFALL_AUTOSTART_DIR"] = str(out_dir / "autostart")
    startup.enable()
    assert startup.is_enabled(), "startup enable failed"
    startup.disable()
    assert not startup.is_enabled(), "startup disable failed"
    print("startup enable/disable (isolated) OK")

    print("SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
#  Argument parsing
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="SeasonFall",
        description="❄ SeasonFall — falling seasons for your desktop "
                    "(snow ❄, petals 🌸, sparks ☀, leaves 🍂, holiday specials 🎄🎃💖)")
    p.add_argument("command", nargs="?", default=None,
                   choices=["settings", "overlay", "start", "quit", "pause",
                            "resume", "status", "startup", "install", "menu",
                            "smoke", "uninstall"],
                   help="settings / overlay / quit / pause / resume / status / "
                        "startup / install (app list) / smoke / uninstall")
    p.add_argument("arg", nargs="?", default=None,
                   help="argument for 'startup' (on | off | status)")
    p.add_argument("--season", choices=list(SEASON_KEYS), default=None)
    p.add_argument("--density", type=int, default=None,
                   help="1..100 — how much falls")
    p.add_argument("--speed", type=float, default=None, help="0.25..3.0")
    p.add_argument("--wind", type=int, default=None, help="-100..100")
    p.add_argument("--size", type=float, default=None,
                   help="particle size / thickness 0.5..2.5")
    p.add_argument("--opacity", type=float, default=None, help="0.15..1.0")
    p.add_argument("--no-mouse", action="store_true",
                   help="disable cursor interaction")
    p.add_argument("--no-click-through", action="store_true",
                   help="overlay captures mouse (lets you use ESC/Space keys)")
    p.add_argument("--duration", type=float, default=None,
                   help=argparse.SUPPRESS)  # used by tests
    p.add_argument("--yes", action="store_true", help="assume yes (uninstall)")
    p.add_argument("--version", action="store_true", help="print version")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.version:
        print(f"SeasonFall {__version__}")
        return 0

    cmd = args.command
    if cmd == "smoke":
        return cmd_smoke()
    if cmd == "startup":
        return cmd_startup(args.arg or "status")
    if cmd == "uninstall":
        return cmd_uninstall(assume_yes=args.yes)
    if cmd in ("install", "menu"):   # 'menu' kept as a friendly alias
        return cmd_install_app()
    if cmd == "settings":
        return run_settings()
    if cmd in ("overlay", "start"):
        return run_overlay(_collect_overrides(args), duration=args.duration)
    if cmd == "quit":
        _ipc_app()
        from .ipc import send_command
        if send_command("quit") is None:
            print("overlay is not running")
            return 1
        print("overlay stopped")
        return 0
    if cmd == "pause":
        _ipc_app()
        from .ipc import send_command
        if send_command("pause") is None:
            print("overlay is not running")
            return 1
        print("paused")
        return 0
    if cmd == "resume":
        _ipc_app()
        from .ipc import send_command
        if send_command("resume") is None:
            print("overlay is not running")
            return 1
        print("resumed")
        return 0
    if cmd == "status":
        return cmd_status()

    # default smart start -------------------------------------------------- #
    if not Config.exists() or not Config.load().first_run_done:
        log("welcome! opening the season picker…")
        return run_settings()
    _ipc_app()
    from .ipc import probe_status
    if probe_status():
        log("overlay already running — open settings with: "
            "python -m seasonfall settings")
        return 0
    return run_overlay(_collect_overrides(args), duration=args.duration)


if __name__ == "__main__":
    raise SystemExit(main())
