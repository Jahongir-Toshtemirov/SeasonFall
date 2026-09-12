"""SeasonFall settings GUI — claymorphism edition: soft, chunky, tactile."""
from __future__ import annotations

import math
import subprocess
import sys

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout,
                               QGraphicsDropShadowEffect, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QPushButton, QSlider,
                               QVBoxLayout, QWidget)

from . import seasons as S
from . import startup
from .config import Config, config_dir
from .engine import ParticleField
from .ipc import IpcServer, probe_status, send_command
from .overlay import OverlayManager

MAX_SLIDER = 1000  # internal resolution for smooth float sliders

# --------------------------------------------------------------------------- #
#  Claymorphism palette — warm clay, no gradients, soft depth via shadows
# --------------------------------------------------------------------------- #
CLAY_BG = "#EFE7DA"
CLAY_PANEL = "#FBF4E8"
CLAY_CARD = "#F3E9D7"
CLAY_EDGE = "#E3D4B8"
CLAY_TEXT = "#4A4034"
CLAY_MUTED = "#988C7A"
PREVIEW_SKY = "#223047"

ACCENTS = {
    "auto": "#3FAE90", "winter": "#5FB4E5", "spring": "#F27BA8",
    "summer": "#FFAF3C", "autumn": "#EE8A1F", "halloween": "#9575DE",
    "christmas": "#E05A5A", "valentine": "#F56A94",
}


def app_icon() -> QIcon:
    """Procedurally painted snowflake icon — no binary assets needed."""
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setBrush(QColor("#5FB4E5"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 64, 64)
    pen = QPen(QColor("#FFFFFF"), 11)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    cx = cy = 128.0
    for i in range(6):
        a = math.radians(i * 60)
        ca, sa = math.cos(a), math.sin(a)
        p.drawLine(QPointF(cx, cy), QPointF(cx + ca * 82, cy + sa * 82))
        for bf in (0.45, 0.72):
            bx, by = cx + ca * 82 * bf, cy + sa * 82 * bf
            for da in (math.radians(52), -math.radians(52)):
                p.drawLine(QPointF(bx, by),
                           QPointF(bx + math.cos(a + da) * 26,
                                   by + math.sin(a + da) * 26))
    p.end()
    return QIcon(pm)


def _clay(widget: QWidget, blur: int = 20, dy: int = 6, alpha: int = 60) -> None:
    """Give a widget the soft 'clay' drop shadow."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    effect.setColor(QColor(96, 74, 48, alpha))
    widget.setGraphicsEffect(effect)


def build_qss(accent: str) -> str:
    return f"""
QWidget {{ background: {CLAY_BG}; color: {CLAY_TEXT}; font-size: 13px; }}
QLabel {{ background: transparent; }}
QMainWindow {{ background: {CLAY_BG}; }}
QLabel#h1 {{ font-size: 22px; font-weight: 800; }}
QLabel#h2 {{ font-size: 14px; font-weight: 700; color: #6B5F4E; }}
QLabel#muted {{ color: {CLAY_MUTED}; font-size: 12px; }}
QFrame#panel {{ background: {CLAY_PANEL};
    border: 1px solid {CLAY_EDGE}; border-radius: 20px; }}
QFrame#card {{ background: {CLAY_CARD};
    border: 1px solid {CLAY_EDGE}; border-radius: 16px; }}
QFrame#cardOn {{ background: #FFFFFF;
    border: 2px solid {accent}; border-radius: 16px; }}
QLabel#seasonEmoji {{ font-size: 24px; background: transparent; }}
QPushButton {{ background: {CLAY_CARD}; border: 1px solid {CLAY_EDGE};
    border-radius: 14px; padding: 10px 18px; font-weight: 600;
    color: {CLAY_TEXT}; }}
QPushButton:hover {{ background: #FBF3E4; }}
QPushButton:disabled {{ color: #B7AB97; background: #EFE5D2; }}
QPushButton#primary {{ background: {accent}; color: #FFFFFF;
    border: none; font-weight: 800; }}
QPushButton#primary:hover {{ background: {accent}; }}
QPushButton#danger {{ background: #F6DADA; border-color: #E8BFBF;
    color: #8C3B3B; }}
QSlider::groove:horizontal {{ height: 10px; background: #E9DCC5;
    border-radius: 5px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 5px; }}
QSlider::handle:horizontal {{ width: 22px; height: 22px; margin: -7px 0;
    border-radius: 11px; background: #FFF9EF; border: 2px solid {accent}; }}
QComboBox {{ background: #F6EDDD; border: 1px solid {CLAY_EDGE};
    border-radius: 12px; padding: 7px 12px; min-width: 110px;
    font-weight: 600; }}
QComboBox:hover {{ background: #FBF3E4; }}
QComboBox QAbstractItemView {{ background: {CLAY_PANEL};
    border: 1px solid {CLAY_EDGE}; color: {CLAY_TEXT};
    selection-background-color: {accent}; selection-color: #FFFFFF; }}
QCheckBox {{ spacing: 9px; font-weight: 500; }}
QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 7px;
    border: 2px solid #DCCCAE; background: #F6EDDD; }}
QCheckBox::indicator:checked {{ background: {accent};
    border-color: {accent}; }}
QLabel#chip {{ background: {CLAY_CARD}; border-radius: 12px;
    padding: 6px 12px; color: #6B5F4E; font-weight: 600; }}
QMessageBox {{ background: {CLAY_PANEL}; }}
QMessageBox QLabel {{ color: {CLAY_TEXT}; background: transparent; }}
"""


class SliderRow(QWidget):
    """label — slider — value, mapped to 0..MAX_SLIDER internally."""

    def __init__(self, label, lo, hi, value, fmt, on_change, parent=None):
        super().__init__(parent)
        self.lo, self.hi, self.fmt = float(lo), float(hi), fmt
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lab = QLabel(label)
        lab.setMinimumWidth(118)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, MAX_SLIDER)
        self.value_label = QLabel()
        self.value_label.setMinimumWidth(56)
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
    """Miniature live rendering of the current season mix."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        cfg = Config()
        self.field = ParticleField(cfg, S.active_mix(cfg), 400, 200, seed=7)
        self.field.load = 3.0          # preview canvas is small → keep it lively
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._step)

    def start(self):
        if not self.timer.isActive():
            self.timer.start()

    def set_scene(self, cfg: Config, specs: list):
        self.field.set_config(cfg)
        self.field.set_mix(specs)
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
        # current multi-season selection ("snow+spring+autumn" etc.)
        self.mix_keys = list(self.cfg.mix) or (
            [self.cfg.season] if self.cfg.season != "auto" else ["auto"])
        self.manager: OverlayManager | None = None   # internal overlay (same proc)
        self.external_overlay = False
        st = probe_status()
        if st and st.get("running"):
            self.external_overlay = True
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
        self.setMinimumSize(960, 660)
        self._loading = True          # guard: don't echo init into cfg
        self._build_ui()
        self.restyle(self._accent())
        self._cfg_to_controls()
        self._loading = False
        self.preview.start()
        self._status_timer.start()
        self._update_start_labels()

    def _accent(self) -> str:
        return ACCENTS.get(self.mix_keys[-1] if self.mix_keys else "auto",
                           ACCENTS["auto"])

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

        tip = QLabel("Pick your seasons — mix any of them!")
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
            name, emoji = "Auto (today)", "🗓️"
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
        check = QLabel("✓")
        check.setStyleSheet("font-weight: 800; background: transparent;")
        check.setVisible(key in self.mix_keys)
        lay.addWidget(check)
        card.mousePressEvent = lambda _ev, k=key: self._toggle_season(k)
        self._cards[key] = (card, check)
        _clay(card, blur=16, dy=4, alpha=45)
        return card

    def _toggle_season(self, key: str) -> None:
        """Multi-select: any combination of seasons can fall at once."""
        if key in self.mix_keys:
            if len(self.mix_keys) <= 1:
                return                     # always keep at least one season
            self.mix_keys.remove(key)
        else:
            self.mix_keys.append(key)
        self._on_any_change()

    def _build_right_panel(self) -> QWidget:
        right = QWidget()
        lay = QVBoxLayout(right)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        preview_wrap = QFrame()
        preview_wrap.setObjectName("panel")
        preview_lay = QVBoxLayout(preview_wrap)
        preview_lay.setContentsMargins(10, 10, 10, 10)
        self.preview = PreviewWidget()
        self.preview.set_scene(self.cfg, S.active_mix(self.cfg))
        preview_lay.addWidget(self.preview)
        _clay(preview_wrap, blur=24, dy=8)
        lay.addWidget(preview_wrap, 2)

        body = QHBoxLayout()
        body.setSpacing(12)
        feel = self._build_feel_panel()
        system = self._build_system_panel()
        _clay(feel, blur=24, dy=8)
        _clay(system, blur=24, dy=8)
        body.addWidget(feel, 2)
        body.addWidget(system, 1)
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
        self.adaptive_check = QCheckBox("Adaptive quality (fewer flakes on weak PCs)")
        self.adaptive_check.toggled.connect(self._on_any_change)
        for w in (self.tumble_check, self.mouse_check, self.rain_check,
                  self.click_through_check, self.battery_check,
                  self.adaptive_check):
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
        for key, (card, check) in self._cards.items():
            selected = key in self.mix_keys
            card.setObjectName("cardOn" if selected else "card")
            check.setVisible(selected)
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
        self.adaptive_check.setChecked(c.adaptive_quality)
        self.holiday_check.setChecked(c.holiday_specials)
        self.quality_combo.setCurrentText(c.quality)
        self.fps_combo.setCurrentText(str(int(c.fps)))
        self.monitor_combo.setCurrentText(c.monitors)
        self.hemisphere_combo.setCurrentText(c.hemisphere)
        self.restyle(self._accent())

    def _collect(self) -> Config:
        c = self.cfg
        c.mix = list(self.mix_keys)
        c.season = self.mix_keys[0] if len(self.mix_keys) == 1 else "auto"
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
        c.adaptive_quality = self.adaptive_check.isChecked()
        c.quality = self.quality_combo.currentText()
        c.fps = int(self.fps_combo.currentText())
        c.monitors = self.monitor_combo.currentText()
        c.hemisphere = self.hemisphere_combo.currentText()
        c.sanitize()
        return c

    def _active_specs(self) -> list:
        self._collect()
        return S.active_mix(self.cfg)

    def _on_any_change(self, *_):
        if getattr(self, "_loading", False):
            return                    # ignore echoes while (re)initialising
        specs = self._active_specs()
        self.preview.set_scene(self.cfg, specs)
        self.restyle(self._accent())
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
        # anti-doubling: if an overlay is already running, just update it
        st = probe_status()
        if st and st.get("running") and self.manager is None:
            send_command("reload")         # live-update the running overlay
            self.external_overlay = True
        else:
            if self.manager is None:
                self.manager = OverlayManager(self.cfg, parent=self)
                IpcServer(self.manager)    # other processes now detect us
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
        if st and st.get("running"):
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
