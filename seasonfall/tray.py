"""System-tray control for a running overlay.

Non-technical users need a visible way to change seasons or quit after the
settings window closes. The snowflake icon lives near the clock; right-click
for Settings / Pause / Quit, double-click for Settings.
"""
from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .config import Config


class TrayController(QObject):
    """Owns the tray icon for one overlay process."""

    def __init__(self, manager, open_settings=None, parent=None):
        super().__init__(parent or manager)
        self.manager = manager
        self._open_settings = open_settings
        self._settings_window = None
        self.icon = QSystemTrayIcon(self)
        from . import settings_gui

        self.icon.setIcon(settings_gui.app_icon())
        self.icon.setToolTip("SeasonFall — right-click for Settings / Quit")
        self.icon.setContextMenu(self._build_menu())
        self.icon.activated.connect(self._on_activated)
        self.icon.show()

    @staticmethod
    def available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _build_menu(self) -> QMenu:
        menu = QMenu()
        act_settings = QAction("Settings…", menu)
        act_settings.triggered.connect(self.open_settings)
        self._act_pause = QAction("Pause", menu)
        self._act_pause.triggered.connect(self._toggle_pause)
        act_quit = QAction("Quit SeasonFall", menu)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_settings)
        menu.addAction(self._act_pause)
        menu.addSeparator()
        menu.addAction(act_quit)
        menu.aboutToShow.connect(self._refresh_pause_label)
        return menu

    def _refresh_pause_label(self) -> None:
        self._act_pause.setText("Resume" if self.manager.paused else "Pause")

    def _on_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings()

    def open_settings(self) -> None:
        if callable(self._open_settings):
            self._open_settings()
            return
        # Default: open (or raise) an in-process settings window bound to
        # this overlay manager so Stop / Apply work without a second process.
        from . import settings_gui

        win = self._settings_window
        if win is not None and win.isVisible():
            win.raise_()
            win.activateWindow()
            return
        win = settings_gui.SettingsWindow(manager=self.manager)
        self._settings_window = win
        win.destroyed.connect(lambda *_: setattr(self, "_settings_window", None))
        win.show()
        win.raise_()
        win.activateWindow()

    def _toggle_pause(self) -> None:
        self.manager.toggle_pause()
        self._refresh_pause_label()

    def _quit(self) -> None:
        self.manager.stop()
        self.hide()
        app = QApplication.instance()
        if app:
            app.quit()

    def show_welcome_tip(self) -> None:
        """One-time balloon so first-time users know where the controls went."""
        cfg = Config.load()
        if getattr(cfg, "tray_tip_shown", False):
            return
        if self.icon.supportsMessages():
            self.icon.showMessage(
                "SeasonFall is running",
                "Find the snowflake icon near the clock.\n"
                "Right-click it to change seasons, pause, or quit.",
                QSystemTrayIcon.MessageIcon.Information,
                8000,
            )
        cfg.tray_tip_shown = True
        cfg.save()

    def hide(self) -> None:
        self.icon.hide()


def attach_tray(manager, open_settings=None) -> TrayController | None:
    """Create a tray if the desktop supports it; otherwise return None."""
    if not TrayController.available():
        return None
    app = QApplication.instance()
    if app is not None:
        app.setQuitOnLastWindowClosed(False)
    tray = TrayController(manager, open_settings=open_settings)
    # Keep a strong ref on the manager so GC never eats the tray.
    manager._seasonfall_tray = tray  # type: ignore[attr-defined]
    return tray
