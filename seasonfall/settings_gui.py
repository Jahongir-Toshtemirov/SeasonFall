"""SeasonFall settings GUI: season cards, sliders, live preview, startup prompt."""
from __future__ import annotations

import math
import subprocess
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QIcon, QLinearGradient, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                               QPushButton, QScrollArea, QSlider, QVBoxLayout,
                               QWidget)

from . import seasons as S
from . import startup
from .config import Config, config_dir, config_path
from .engine import ParticleField
from .ipc import probe_status, send_command
from .overlay import OverlayManager
from .util import is_linux

MAX_SLIDER = 1000  # internal resolution for smooth float sliders


def app_icon() -> QIcon:
    """Procedurally painted snowflake icon — no binary assets needed."""
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    grad = QLinearGradient(0, 0, 256, 256)
    grad.setColorAt(0.0, QColor("#1c2748"))
    grad.setColorAt(1.0, QColor("#0d1220"))
    p.setBrush(grad)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 56, 56)
    pen = QPen(QColor("#9fdcff"), 10)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    cx = cy = 128.0
    for i in range(6):
        a = math.radians(i * 60)
        ca, sa = math.cos(a), math.sin(a)
        p.drawLine(QPointF(cx, cy), QPointF(cx + ca * 84, cy + sa * 84))
        for bf in (0.45, 0.72):
            bx, by = cx + ca * 84 * bf, cy + sa * 84 * bf
            for da in (math.radians(52), -math.radians(52)):
                p.drawLine(QPointF(bx, by),
                           QPointF(bx + math.cos(a + da) * 26,
                                   by + math.sin(a + da) * 26))
    p.end()
    return QIcon(pm)


def build_qss(accent: str) -> str:
    return f"""
QWidget {{ background: #12141d; color: #e7eaf3; font-size: 13px; }}
QLabel {{ background: transparent; }}
QMainWindow, QDialog {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 #0e1119, stop:1 #141a2b); }}
QLabel#h1 {{ font-size: 22px; font-weight: 700; }}
QLabel#h2 {{ font-size: 14px; font-weight: 600; color: #aab3cc; }}
QLabel#muted {{ color: #8a92ab; font-size: 12px; }}
QFrame#card {{ background: #191e2e; border: 1px solid #272e45; border-radius: 12px; }}
QFrame#cardOn {{ background: #1f2540; border: 2px solid {accent}; border-radius: 12px; }}
QFrame#panel {{ background: #171b29; border: 1px solid #262c42; border-radius: 12px; }}
QLabel#seasonEmoji {{ font-size: 26px; background: transparent; }}
QPushButton {{ background: #232a44; border: 1px solid #313a5c; border-radius: 9px;
    padding: 9px 16px; font-weight: 500; }}
QPushButton:hover {{ background: #2b3354; }}
QPushButton:disabled {{ color: #666e88; background: #1a1f31; }}
QPushButton#primary {{ background: {accent}; color: #0a0d16; font-weight: 700;
    border: none; }}
QPushButton#danger {{ background: #3a2030; border-color: #5c2f42; }}
QSlider::groove:horizontal {{ height: 6px; background: #2a3050; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -6px 0;
    border-radius: 8px; background: #e8ecf7; }}
QComboBox {{ background: #1d2338; border: 1px solid #2e3654; border-radius: 8px;
    padding: 6px 10px; min-width: 110px; }}
QComboBox QAbstractItemView {{ background: #1d2338; border: 1px solid #2e3654;
    selection-background-color: {accent}; selection-color: #0a0d16; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid #3a4468; background: #1d2338; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QScrollArea {{ border: none; background: transparent; }}
QMessageBox {{ background: #171b29; }}
QLabel#chip {{ background: #1d2338; border-radius: 10px; padding: 4px 10px;
    color: #9aa3bd; }}
"""


class SliderRow(QWidget):
    """label — slider — value, mapped to 0..MAX_SLIDER internally."""

    def __init__(self, label, lo, hi, value, fmt, on_change, parent=None):
        super().__init__(parent)
        self.lo, self.hi, self.fmt = float(lo), float(hi), fmt
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lab = QLabel(label)
        lab.setMinimumWidth(110)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, MAX_SLIDER)
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(54)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight |
                                      Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(lab)
        lay.addWidget(self.slider, 1)
        lay.addWidget(self.value_label)
        self.slider.valueChanged.connect(self._refresh_label)
        self.slider.valueChanged.connect(on_change)
        self.set_value(value)

    def _refresh_label(self):
        self.value_label.setText(self.fmt(self.real_value()))

    def set_value(self, real):
        frac = (float(real) - self.lo) / (self.hi - self.lo)
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(frac * MAX_SLIDER)))
        self.slider.blockSignals(False)
        self.value_label.setText(self.fmt(real))

    def real_value(self):
        frac = self.slider.value() / MAX_SLIDER
        return self.lo + frac * (self.hi - self.lo)


class PreviewWidget(QWidget):
    """Miniature live rendering of the current configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        cfg = Config()
        self.field = ParticleField(cfg, S.resolve_season(cfg), 400, 200, seed=7)
        self.field.load = 3.0          # preview canvas is small → keep it lively
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._step)

    def start(self):
        if not self.timer.isActive():
            self.timer.start()

    def set_scene(self, cfg: Config, spec: S.SeasonSpec):
        self.field.set_config(cfg)
        self.field.set_season(spec)
        self.field.resize(max(200.0, float(self.width())),
                          max(120.0, float(self.height())))
        self.field.prefill()

    def resizeEvent(self, ev):
        self.field.resize(max(200.0, float(self.width())),
                          max(120.0, float(self.height())))
        super().resizeEvent(ev)

    def _step(self):
        self.field.tick(1 / 30.0, None)
        self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)
        self.field.paint(painter, transparent=False)
        painter.end()


class SettingsWindow(QMainWindow):
    """The main configuration window."""

    def __init__(self, first_run: bool = False):
        super().__init__()
        self.first_run = first_run
        self.cfg = Config.load()
        self.spec = S.resolve_season(self.cfg)
        self.manager: OverlayManager | None = None   # internal overlay (same proc)
        self.external_overlay = probe_status() is not None
        self._cards: dict[str, tuple[QFrame, QLabel]] = {}
        self._apply_timer = QTimer(self)             # debounce live push
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(350)
        self._apply_timer.timeout.connect(self._push_live)
        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._poll_status)

        self.setWindowTitle("SeasonFall — Season Overlay Studio")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(960, 640)
        self._loading = True          # guard: don't echo init into cfg
        self._build_ui()
        self.restyle(self.spec.accent)
        self._cfg_to_controls()
        self._loading = False
        self.preview.start()
        self._status_timer.start()
        self._update_start_labels()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(14)
        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_right_panel(), 1)

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(250)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        logo_row = QHBoxLayout()
        emoji = QLabel("🌨️")
        emoji.setStyleSheet("font-size: 30px; background: transparent;")
        title = QLabel("SeasonFall")
        title.setObjectName("h1")
        import seasonfall as _sf
        ver = QLabel(f"v{_sf.__version__}")
        ver.setObjectName("muted")
        logo_row.addWidget(emoji)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(title)
        col.addWidget(ver)
        logo_row.addLayout(col)
        logo_row.addStretch(1)
        lay.addLayout(logo_row)

        tip = QLabel("Pick your season")
        tip.setObjectName("h2")
        lay.addWidget(tip)

        for key in S.GUI_SEASON_ORDER:
            lay.addWidget(self._make_season_card(key))
        lay.addStretch(1)

        self.holiday_check = QCheckBox("Holiday surprises  🎄 🎃 💖")
        self.holiday_check.setChecked(self.cfg.holiday_specials)
        self.holiday_check.toggled.connect(self._on_any_change)
        lay.addWidget(self.holiday_check)

        lay.addWidget(QLabel("Hemisphere (for Auto)"))
        self.hemisphere_combo = QComboBox()
        self.hemisphere_combo.addItems(["auto", "north", "south"])
        self.hemisphere_combo.currentTextChanged.connect(self._on_any_change)
        lay.addWidget(self.hemisphere_combo)

        self.startup_label = QLabel()
        self.startup_label.setObjectName("muted")
        self.startup_label.setWordWrap(True)
        self._refresh_startup_label()
        lay.addWidget(self.startup_label)
        return panel

    def _make_season_card(self, key: str) -> QFrame:
        if key == "auto":
            name, emoji = "Auto (by date)", "🗓️"
        else:
            spec = S.SPECS[key]
            name, emoji = spec.name, spec.emoji
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(12, 9, 12, 9)
        em = QLabel(emoji)
        em.setObjectName("seasonEmoji")
        label = QLabel(name)
        lay.addWidget(em)
        lay.addWidget(label)
        lay.addStretch(1)
        card.mousePressEvent = lambda _ev, k=key: self._select_season(k)
        self._cards[key] = (card, label)
        return card

    def _build_right_panel(self) -> QWidget:
        right = QWidget()
        lay = QVBoxLayout(right)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        self.preview = PreviewWidget()
        self.preview.set_scene(self.cfg, self.spec)
        lay.addWidget(self.preview, 2)

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_feel_panel(), 2)
        body.addWidget(self._build_system_panel(), 1)
        lay.addLayout(body, 3)

        footer = QHBoxLayout()
        self.status_chip = QLabel("…")
        self.status_chip.setObjectName("chip")
        footer.addWidget(self.status_chip)
        footer.addStretch(1)
        btn_folder = QPushButton("Config folder")
        btn_folder.clicked.connect(self._open_config_folder)
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.clicked.connect(self._stop_overlay)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._save_only)
        self.btn_start = QPushButton("▶  Start & Enjoy")
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self._start_clicked)
        for b in (btn_folder, self.btn_stop, btn_save, self.btn_start):
            footer.addWidget(b)
        lay.addLayout(footer)
        return right

    def _build_feel_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 10, 14, 10)
        title = QLabel("Fall feel")
        title.setObjectName("h2")
        lay.addWidget(title)
        grid = QGridLayout()
        grid.setVerticalSpacing(4)
        c = self.cfg
        self.s_density = SliderRow("Intensity", 1, 100, c.density,
                                   lambda v: f"{v:.0f}%", self._on_any_change)
        self.s_speed = SliderRow("Speed", 0.25, 3.0, c.speed,
                                 lambda v: f"{v:.2f}×", self._on_any_change)
        self.s_wind = SliderRow("Wind", -100, 100, c.wind,
                                lambda v: f"{v:+.0f}", self._on_any_change)
        self.s_size = SliderRow("Size / Thickness", 0.5, 2.5, c.size,
                                lambda v: f"{v:.2f}×", self._on_any_change)
        self.s_opacity = SliderRow("Opacity", 0.15, 1.0, c.opacity,
                                   lambda v: f"{v * 100:.0f}%", self._on_any_change)
        self.s_sway = SliderRow("Sway", 0.0, 2.5, c.sway,
                                lambda v: f"{v:.2f}×", self._on_any_change)
        self.s_golden = SliderRow("Golden leaves", 0, 100, c.golden_share,
                                  lambda v: f"{v:.0f}%", self._on_any_change)
        for i, row in enumerate((self.s_density, self.s_speed, self.s_wind,
                                 self.s_size, self.s_opacity, self.s_sway,
                                 self.s_golden)):
            grid.addWidget(row, i, 0, 1, 2)
        lay.addLayout(grid)
        lay.addStretch(1)
        return panel

    def _build_system_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)
        title = QLabel("Behaviour")
        title.setObjectName("h2")
        lay.addWidget(title)

        self.tumble_check = QCheckBox("Tumble & 3D flip")
        self.tumble_check.toggled.connect(self._on_any_change)
        self.mouse_check = QCheckBox("Cursor pushes particles")
        self.mouse_check.toggled.connect(self._on_any_change)
        self.rain_check = QCheckBox("Spring drizzle")
        self.rain_check.toggled.connect(self._on_any_change)
        self.click_through_check = QCheckBox("Click-through desktop")
        self.click_through_check.toggled.connect(self._on_any_change)
        self.battery_check = QCheckBox("Pause on battery")
        self.battery_check.toggled.connect(self._on_any_change)
        for w in (self.tumble_check, self.mouse_check, self.rain_check,
                  self.click_through_check, self.battery_check):
            lay.addWidget(w)

        lay.addWidget(QLabel("Quality"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["low", "medium", "high", "ultra"])
        self.quality_combo.currentTextChanged.connect(self._on_any_change)
        lay.addWidget(self.quality_combo)

        row = QHBoxLayout()
        row.addWidget(QLabel("FPS"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "30", "60"])
        self.fps_combo.currentTextChanged.connect(self._on_any_change)
        row.addWidget(self.fps_combo)
        row.addWidget(QLabel("Monitors"))
        self.monitor_combo = QComboBox()
        self.monitor_combo.addItems(["all", "primary"])
        self.monitor_combo.currentTextChanged.connect(self._on_any_change)
        row.addWidget(self.monitor_combo)
        lay.addLayout(row)
        lay.addStretch(1)
        return panel

    # ------------------------------------------------------------------ #
    #  Behaviour / handlers
    # ------------------------------------------------------------------ #
    def restyle(self, accent: str) -> None:
        self.setStyleSheet(build_qss(accent))
        for key, (card, _label) in self._cards.items():
            selected = (key == self.cfg.season)
            card.setObjectName("cardOn" if selected else "card")
            card.style().unpolish(card)
            card.style().polish(card)

    def _cfg_to_controls(self) -> None:
        c = self.cfg
        self.s_density.set_value(c.density)
        self.s_speed.set_value(c.speed)
        self.s_wind.set_value(c.wind)
        self.s_size.set_value(c.size)
        self.s_opacity.set_value(c.opacity)
        self.s_sway.set_value(c.sway)
        self.s_golden.set_value(c.golden_share)
        self.tumble_check.setChecked(c.tumble)
        self.mouse_check.setChecked(c.mouse_interact)
        self.rain_check.setChecked(c.rain)
        self.click_through_check.setChecked(c.click_through)
        self.battery_check.setChecked(c.auto_pause_battery)
        self.holiday_check.setChecked(c.holiday_specials)
        self.quality_combo.setCurrentText(c.quality)
        self.fps_combo.setCurrentText(str(int(c.fps)))
        self.monitor_combo.setCurrentText(c.monitors)
        self.hemisphere_combo.setCurrentText(c.hemisphere)
        self.restyle(self.spec.accent)

    def _collect(self) -> Config:
        c = self.cfg
        c.density = int(round(self.s_density.real_value()))
        c.speed = round(self.s_speed.real_value(), 2)
        c.wind = int(round(self.s_wind.real_value()))
        c.size = round(self.s_size.real_value(), 2)
        c.opacity = round(self.s_opacity.real_value(), 2)
        c.sway = round(self.s_sway.real_value(), 2)
        c.golden_share = int(round(self.s_golden.real_value()))
        c.tumble = self.tumble_check.isChecked()
        c.mouse_interact = self.mouse_check.isChecked()
        c.rain = self.rain_check.isChecked()
        c.click_through = self.click_through_check.isChecked()
        c.auto_pause_battery = self.battery_check.isChecked()
        c.holiday_specials = self.holiday_check.isChecked()
        c.quality = self.quality_combo.currentText()
        c.fps = int(self.fps_combo.currentText())
        c.monitors = self.monitor_combo.currentText()
        c.hemisphere = self.hemisphere_combo.currentText()
        c.sanitize()
        return c

    def _select_season(self, key: str) -> None:
        self.cfg.season = key
        self.spec = S.resolve_season(self.cfg)
        self.restyle(self.spec.accent)
        self.preview.set_scene(self.cfg, self.spec)
        self._on_any_change()

    def _on_any_change(self, *_):
        if getattr(self, "_loading", False):
            return                    # ignore echoes while (re)initialising
        self._collect()
        self.spec = S.resolve_season(self.cfg)
        self.preview.set_scene(self.cfg, self.spec)
        self.restyle(self.spec.accent)
        self._apply_timer.start()

    def _push_live(self) -> None:
        """Push current settings to a running overlay (without saving)."""
        if self.manager is not None:
            self.manager.apply_config(self.cfg.clone())
        elif self.external_overlay:
            send_command("reload")

    def _save_only(self) -> None:
        self._collect()
        self.cfg.first_run_done = True
        self.cfg.save()
        self._push_live()
        self.status_chip.setText("saved ✓")

    def _start_clicked(self) -> None:
        self._collect()
        self.cfg.first_run_done = True
        self.cfg.save()
        if self.manager is None and self.external_overlay:
            send_command("reload")         # live-update the running overlay
        else:
            if self.manager is None:
                self.manager = OverlayManager(self.cfg, parent=self)
            # settings will close itself → keep the process alive for the overlay
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                app.setQuitOnLastWindowClosed(False)
            self.manager.apply_config(self.cfg.clone())
            self.manager.start()
            self.external_overlay = True
        if not self.cfg.startup_prompted:
            self._ask_startup()
        self._update_start_labels()
        self.close()                       # the app closes itself → snow remains

    def _ask_startup(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("SeasonFall")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("❄️  Start SeasonFall automatically when you log in?")
        box.setInformativeText("You can change this later from the settings window.")
        yes = box.addButton("Yes, start at login", QMessageBox.ButtonRole.YesRole)
        box.addButton("No thanks", QMessageBox.ButtonRole.NoRole)
        box.exec()
        if box.clickedButton() is yes:
            startup.enable()
        self.cfg.startup_prompted = True
        self.cfg.save()
        self._refresh_startup_label()

    def _stop_overlay(self) -> None:
        if self.manager is not None:
            self.manager.stop()
            self.manager = None
        elif self.external_overlay:
            send_command("quit")
            self.external_overlay = False
        self._update_start_labels()

    def _poll_status(self) -> None:
        if self.manager is not None:
            self.status_chip.setText(self.manager.stats_text())
            return
        st = probe_status()
        if st:
            self.external_overlay = True
            self.status_chip.setText(
                f"running · {st.get('particles', 0)} particles · "
                f"{st.get('fps', 0):.0f} fps · {st.get('season_name', '')}")
        else:
            self.external_overlay = False
            self.status_chip.setText("overlay stopped")

    def _update_start_labels(self) -> None:
        if self.external_overlay or self.manager is not None:
            self.btn_start.setText("⟳  Apply & Close")
            self.btn_stop.setEnabled(True)
        else:
            self.btn_start.setText("▶  Start & Enjoy")
            self.btn_stop.setEnabled(False)

    def _refresh_startup_label(self) -> None:
        if startup.is_enabled():
            self.startup_label.setText("✓ Starts at login")
        else:
            self.startup_label.setText("· Not in startup apps")

    def _open_config_folder(self) -> None:
        import os
        import subprocess
        import sys as _sys
        from .config import config_dir
        path = config_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            if _sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    def closeEvent(self, ev) -> None:
        ev.accept()
