"""Transparent, click-through, always-on-top overlay windows + manager."""
from __future__ import annotations

import time

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QWidget

from . import seasons as S
from .config import Config
from .engine import ParticleField
from .power import on_battery
from .util import dbg


class SeasonOverlay(QWidget):
    """One fullscreen transparent window pinned to one screen."""

    def __init__(self, manager: "OverlayManager", screen):
        super().__init__(None)
        self.manager = manager
        cfg = manager.cfg
        flags = (Qt.WindowType.FramelessWindowHint
                 | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.Tool
                 | Qt.WindowType.NoDropShadowWindowHint)
        if cfg.click_through:
            flags |= Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        if cfg.click_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setWindowTitle("SeasonFall")
        self.field = ParticleField(cfg, manager.specs, seed=manager.next_seed())
        g = screen.geometry()
        self.setGeometry(g)
        self.field.resize(g.width(), g.height())
        self.show()

    def keyPressEvent(self, ev) -> None:
        # Only reachable when click-through is disabled.
        key = ev.key()
        if key == Qt.Key.Key_Escape:
            self.manager.request_quit()
        elif key == Qt.Key.Key_Space:
            self.manager.toggle_pause()
        else:
            super().keyPressEvent(ev)

    def paintEvent(self, ev) -> None:
        painter = QPainter(self)
        self.field.paint(painter, transparent=True)


class OverlayManager(QObject):
    """Drives one overlay per target screen with a fixed-rate timer."""

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.specs = S.active_mix(cfg)
        self.windows: list[SeasonOverlay] = []
        self.paused = False
        self.running = False
        self.fps = 0.0
        self.frame_ms = 0.0
        self._battery_paused = False
        self._seed = 20260912
        self._last_screen_key = ""
        self._last = time.perf_counter()
        self._frames = 0
        self._fps_t0 = self._last
        self._ema_ms = 0.0

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._tick)

        self.battery_timer = QTimer(self)
        self.battery_timer.setInterval(30_000)
        self.battery_timer.timeout.connect(self._check_battery)

        app = QGuiApplication.instance()
        if app:
            app.screenAdded.connect(self._screens_changed)
            app.screenRemoved.connect(self._screens_changed)
            app.primaryScreenChanged.connect(self._screens_changed)

    def next_seed(self) -> int:
        self._seed = (self._seed * 1103515245 + 12345) & 0x7FFFFFFF
        return self._seed

    # ---------------- lifecycle ---------------- #
    def start(self) -> None:
        self._rebuild_windows(force=True)
        self.timer.setInterval(self._interval())
        self._last = time.perf_counter()
        self.timer.start()
        self.battery_timer.start()
        self._check_battery()
        self.running = True

    def stop(self) -> None:
        self.running = False
        self.timer.stop()
        self.battery_timer.stop()
        for w in self.windows:
            w.close()
        self.windows.clear()

    def toggle_pause(self) -> None:
        self.resume() if self.paused else self.pause()

    def pause(self, battery: bool = False) -> None:
        if battery:
            self._battery_paused = True
        self.paused = True
        self.timer.stop()

    def resume(self) -> None:
        self._battery_paused = False
        self.paused = False
        self._last = time.perf_counter()
        self.timer.start()

    def request_quit(self) -> None:
        app = QApplication.instance()
        if app:
            app.quit()

    # ---------------- configuration ---------------- #
    def _interval(self) -> int:
        return max(15, int(1000 / max(24, min(60, int(self.cfg.fps)))))

    def apply_config(self, cfg: Config) -> None:
        self.cfg = cfg
        self.specs = S.active_mix(cfg)
        self.timer.setInterval(self._interval())
        for w in self.windows:
            w.field.set_config(cfg)
            w.field.set_mix(self.specs)
        self._rebuild_windows()

    # ---------------- screens / windows ---------------- #
    def _target_screens(self):
        if self.cfg.monitors == "primary":
            prim = QGuiApplication.primaryScreen()
            return [prim] if prim else []
        return list(QGuiApplication.screens())

    def _screen_key(self) -> str:
        return self.cfg.monitors + "|" + "|".join(
            f"{s.geometry().x()},{s.geometry().y()},"
            f"{s.geometry().width()},{s.geometry().height()}"
            for s in self._target_screens())

    def _rebuild_windows(self, force: bool = False) -> None:
        key = self._screen_key()
        if not force and key == self._last_screen_key:
            return
        self._last_screen_key = key
        for w in self.windows:
            w.close()
        self.windows.clear()
        for screen in self._target_screens():
            try:
                self.windows.append(SeasonOverlay(self, screen))
            except Exception as exc:  # pragma: no cover
                dbg("overlay window failed:", exc)
        dbg(f"{len(self.windows)} overlay window(s)")

    def _screens_changed(self, *_):
        QTimer.singleShot(800, self._rebuild_windows)

    # ---------------- main loop ---------------- #
    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last
        self._last = now
        if dt <= 0 or not self.windows:
            return
        self.frame_ms = dt * 1000.0
        self._ema_ms = self._ema_ms * 0.9 + dt * 1000.0 * 0.1
        if self.cfg.adaptive_quality:
            # optional: shrink the flock under sustained load
            budget = 1000.0 / max(24, min(60, int(self.cfg.fps)))
            if self._ema_ms > budget * 1.4:
                for w in self.windows:
                    w.field.load = max(0.35, w.field.load - 0.04)
            elif self._ema_ms < budget * 0.6:
                for w in self.windows:
                    w.field.load = min(1.0, w.field.load + 0.02)
        cursor = QCursor.pos()
        for w in self.windows:
            g = w.geometry()
            lx, ly = cursor.x() - g.x(), cursor.y() - g.y()
            inside = 0 <= lx <= g.width() and 0 <= ly <= g.height()
            w.field.tick(dt, (lx, ly) if inside else None)
            w.update()
        self._frames += 1
        if now - self._fps_t0 >= 1.0:
            self.fps = self._frames / (now - self._fps_t0)
            self._frames = 0
            self._fps_t0 = now

    def _check_battery(self) -> None:
        if not self.cfg.auto_pause_battery:
            return
        state = on_battery()
        if state is True and not self.paused:
            dbg("on battery → pausing")
            self.pause(battery=True)
        elif state is False and self.paused and self._battery_paused:
            dbg("back on AC → resuming")
            self.resume()

    # ---------------- status ---------------- #
    def season_label(self) -> str:
        return S.season_label(self.specs)

    def stats_text(self) -> str:
        state = "paused" if self.paused else "running"
        n = sum(len(w.field.particles) for w in self.windows)
        return f"{state} · {n} particles · {self.fps:.0f} fps · {self.season_label()}"
