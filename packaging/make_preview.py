"""Render the SeasonFall banner (docs/preview.png) using the real engine.

Runs fully offscreen — safe to re-run any time the engine changes.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

from PySide6.QtGui import QColor, QLinearGradient, QImage, QPainter
from PySide6.QtWidgets import QApplication

from seasonfall import seasons as S
from seasonfall.config import Config
from seasonfall.engine import ParticleField

W, H = 1280, 660
STRIP = H // 3

app = QApplication([])

img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
painter = QPainter(img)
grad = QLinearGradient(0, 0, 0, H)
grad.setColorAt(0.0, QColor("#0b1220"))
grad.setColorAt(0.6, QColor("#16233a"))
grad.setColorAt(1.0, QColor("#1e3050"))
painter.fillRect(img.rect(), grad)
painter.end()


def render_strip(key: str, y: int) -> None:
    layer = QImage(W, STRIP, QImage.Format.Format_ARGB32_Premultiplied)
    layer.fill(0)
    cfg = Config(season=key, holiday_specials=False, quality="high",
                 density=200, size=1.2, speed=1.0)
    spec = S.resolve_season(cfg, today=date(2026, 12, 20))
    field = ParticleField(cfg, [spec], W, STRIP, seed=11)
    for _ in range(150):
        field.tick(1 / 60.0, None)
    p = QPainter(layer)
    field.paint(p, transparent=True)
    p.end()
    painter = QPainter(img)
    painter.drawImage(0, y, layer)
    painter.end()


render_strip("winter", 0)
render_strip("spring", STRIP)
render_strip("autumn", STRIP * 2)

out = "docs/preview.png"
img.save(out, "PNG")

# sanity: make sure particles actually rendered
sampled = lit = 0
for yy in range(0, H, 9):
    for xx in range(0, W, 9):
        sampled += 1
        if (img.pixel(xx, yy) >> 24) & 0xFF:
            lit += 1
print(f"wrote {out}  lit={lit / sampled * 100:.1f}%")
