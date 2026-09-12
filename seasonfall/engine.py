"""Particle engine: simulation + QPainter rendering for every particle kind.

ParticleField is UI-agnostic — it renders into any QPainter, so the same code
drives the transparent desktop overlay and the settings live-preview.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional, Tuple

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF, QRadialGradient)

from . import seasons as S

# --------------------------------------------------------------------------- #
#  Tuning tables
# --------------------------------------------------------------------------- #
# vy: px/sec at depth z=1 and speed=1 (negative = rising)
# sway: horizontal sinusoid px/sec, rot: deg/sec, tw: twinkle pulses/sec
KINDS = {
    S.K_SNOW:    dict(vy=(26, 60), sway=(14, 34), rot=(28, 80), flip=0, tw=0.0),
    S.K_SLUSH:   dict(vy=(18, 44), sway=(10, 26), rot=(0, 0),   flip=0, tw=0.0),
    S.K_FROST:   dict(vy=(10, 26), sway=(16, 40), rot=(8, 40),  flip=0, tw=2.6),
    S.K_PETAL:   dict(vy=(20, 42), sway=(22, 46), rot=(16, 60), flip=1, tw=0.0),
    S.K_RAIN:    dict(vy=(430, 650), sway=(0, 0), rot=(0, 0),   flip=0, tw=0.0),
    S.K_LEAF:    dict(vy=(28, 58), sway=(18, 40), rot=(40, 110), flip=1, tw=0.0),
    S.K_GOLDEN:  dict(vy=(24, 52), sway=(20, 42), rot=(35, 95), flip=1, tw=0.8),
    S.K_SPARK:   dict(vy=(-26, -10), sway=(8, 20), rot=(5, 25), flip=0, tw=3.0),
    S.K_GLITTER: dict(vy=(-14, -4), sway=(4, 12),  rot=(0, 0),  flip=0, tw=4.0),
    S.K_FIREFLY: dict(vy=(-8, 8),   sway=(10, 26), rot=(0, 0),  flip=0, tw=1.3),
    S.K_HEART:   dict(vy=(16, 34), sway=(18, 36), rot=(6, 18),  flip=0, tw=0.0),
    S.K_BAT:     dict(vy=(46, 80), sway=(30, 70), rot=(0, 0),   flip=0, tw=0.0),
    S.K_PUMPKIN: dict(vy=(34, 60), sway=(10, 24), rot=(8, 30),  flip=0, tw=0.0),
    S.K_GIFT:    dict(vy=(44, 72), sway=(10, 26), rot=(10, 36), flip=0, tw=0.0),
    S.K_CANE:    dict(vy=(48, 78), sway=(12, 30), rot=(12, 40), flip=0, tw=0.0),
}

BASE_SIZE = {
    S.K_SNOW: 7.0, S.K_SLUSH: 5.0, S.K_FROST: 3.6, S.K_PETAL: 6.5,
    S.K_RAIN: 1.0, S.K_LEAF: 10.0, S.K_GOLDEN: 10.0, S.K_SPARK: 5.0,
    S.K_GLITTER: 1.8, S.K_FIREFLY: 5.0, S.K_HEART: 9.0, S.K_BAT: 11.0,
    S.K_PUMPKIN: 13.0, S.K_GIFT: 11.0, S.K_CANE: 10.0,
}

QUALITY_MULT = {"low": 0.35, "medium": 0.6, "high": 1.0, "ultra": 1.5}
MAX_PARTICLES = 900
MOUSE_R = 150.0
MOUSE_R2 = MOUSE_R * MOUSE_R


# --------------------------------------------------------------------------- #
#  Unit geometry (radius-1 shapes, scaled at draw time)
# --------------------------------------------------------------------------- #
def _build_snow_lines():
    lines = []
    for i in range(6):
        a = math.radians(i * 60)
        ca, sa = math.cos(a), math.sin(a)
        lines.append(QLineF(0.0, 0.0, ca, sa))
        for bf in (0.45, 0.72):
            bx, by = ca * bf, sa * bf
            bl = 0.34 * (1.0 - bf * 0.35)
            for da in (math.radians(52), -math.radians(52)):
                lines.append(QLineF(bx, by,
                                    bx + math.cos(a + da) * bl,
                                    by + math.sin(a + da) * bl))
    return tuple(lines)


def _build_heart_pts(n=22):
    pts = []
    for i in range(n):
        t = math.tau * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(QPointF(x / 17.0, -y / 17.0))
    return QPolygonF(pts)


SNOW_LINES = _build_snow_lines()
LEAF_PTS = QPolygonF([
    QPointF(0.0, -0.55), QPointF(0.26, -0.40), QPointF(0.36, -0.08),
    QPointF(0.26, 0.26), QPointF(0.08, 0.50), QPointF(0.0, 0.56),
    QPointF(-0.08, 0.50), QPointF(-0.26, 0.26), QPointF(-0.36, -0.08),
    QPointF(-0.26, -0.40),
])
HEART_PTS = _build_heart_pts()
STAR4_PTS = QPolygonF([
    QPointF(0.0, -1.0), QPointF(0.16, -0.16), QPointF(1.0, 0.0),
    QPointF(0.16, 0.16), QPointF(0.0, 1.0), QPointF(-0.16, 0.16),
    QPointF(-1.0, 0.0), QPointF(-0.16, -0.16),
])
BAT_PTS = QPolygonF([
    QPointF(0.0, -0.28), QPointF(-0.08, -0.34), QPointF(-0.50, -0.62),
    QPointF(-0.38, -0.30), QPointF(-0.66, -0.18), QPointF(-0.42, 0.18),
    QPointF(-0.16, 0.10), QPointF(0.0, 0.34), QPointF(0.16, 0.10),
    QPointF(0.42, 0.18), QPointF(0.66, -0.18), QPointF(0.38, -0.30),
    QPointF(0.50, -0.62), QPointF(0.08, -0.34),
])


class Particle:
    __slots__ = ("kind", "x", "y", "z", "vx", "vy", "size", "rot", "rot_spd",
                 "phase", "phase_spd", "sway", "flip", "flip_spd", "tw",
                 "seed", "kx", "ky", "color", "glow", "rising")

    def __init__(self):
        self.kind = S.K_SNOW
        self.x = 0.0
        self.y = 0.0
        self.z = 1.0
        self.vx = 0.0
        self.vy = 30.0
        self.size = 6.0
        self.rot = 0.0
        self.rot_spd = 0.0
        self.phase = 0.0
        self.phase_spd = 1.0
        self.sway = 0.0
        self.flip = 0.0
        self.flip_spd = 0.0
        self.tw = 0.0
        self.seed = 0.0
        self.kx = 0.0
        self.ky = 0.0
        self.color = (255, 255, 255)
        self.glow = False
        self.rising = False


def _zkey(p):
    return p.z


class ParticleField:
    """Owns every particle, advances physics and paints them."""

    def __init__(self, cfg: Config, spec: S.SeasonSpec,
                 width: float = 800, height: float = 600, seed: int | None = None):
        self.cfg = cfg
        self.spec = spec
        self.w = float(width)
        self.h = float(height)
        self.t = 0.0
        self.gust = 0.0
        self._wind_px = 0.0
        self.load = 1.0            # adaptive-quality multiplier (0.3 .. 1.0)
        self.rnd = random.Random(seed)
        self.particles: List[Particle] = []
        self.kind_names: list[str] = []
        self.kind_weights: list[float] = []
        self.palettes: dict = {}
        self._apply_spec(spec)
        self._populate()

    # ------------------------------------------------------------------ #
    #  Configuration
    # ------------------------------------------------------------------ #
    def _effective_kinds(self, spec: S.SeasonSpec):
        kinds = list(spec.kinds)
        if spec.key == "autumn":
            g = max(0, min(100, int(self.cfg.golden_share)))
            kinds = [(S.K_LEAF, 100 - g), (S.K_GOLDEN, g)]
        elif spec.key == "spring" and not self.cfg.rain:
            kinds = [(S.K_PETAL, 100)]
        names = [k for k, w in kinds if w > 0]
        weights = [float(w) for k, w in kinds if w > 0]
        return names, weights

    def _apply_spec(self, spec: S.SeasonSpec) -> None:
        self.spec = spec
        self.kind_names, self.kind_weights = self._effective_kinds(spec)
        self.palettes = dict(spec.palettes)
        for p in self.particles:      # convert existing, keep positions
            self._assign(p, keep_position=True)

    def set_season(self, spec: S.SeasonSpec) -> None:
        self._apply_spec(spec)

    def set_config(self, cfg: Config) -> None:
        self.cfg = cfg
        names, weights = self._effective_kinds(self.spec)
        if names != self.kind_names:
            self.kind_names, self.kind_weights = names, weights
            for p in self.particles:
                self._assign(p, keep_position=True)

    def resize(self, w: float, h: float) -> None:
        self.w, self.h = float(w), float(h)

    # ------------------------------------------------------------------ #
    #  Population control
    # ------------------------------------------------------------------ #
    def target_count(self) -> int:
        area = (self.w * self.h) / 1_000_000.0
        base = 240.0 * (self.cfg.density / 100.0) * area
        q = QUALITY_MULT.get(self.cfg.quality, 1.0)
        return int(max(8, min(MAX_PARTICLES, base * q * self.load)))

    def _populate(self) -> None:
        for _ in range(self.target_count()):
            p = Particle()
            p.x = self.rnd.uniform(0, self.w)
            p.y = self.rnd.uniform(-60, self.h)
            self.particles.append(p)
            self._assign(p, keep_position=True)

    def prefill(self) -> None:
        """Instantly top-up to the target count (used by the live preview)."""
        while len(self.particles) < self.target_count():
            p = Particle()
            p.x = self.rnd.uniform(0, self.w)
            p.y = self.rnd.uniform(-60, self.h)
            self.particles.append(p)
            self._assign(p, keep_position=True)

    def _adjust_population(self) -> None:
        target = self.target_count()
        cur = len(self.particles)
        if cur < target:
            for _ in range(min(target - cur, 12)):
                p = Particle()
                self.particles.append(p)
                self._spawn(p)
        elif cur > target + 8:
            del self.particles[max(target, cur - 20):]

    # ------------------------------------------------------------------ #
    #  Spawning
    # ------------------------------------------------------------------ #
    def _pick_kind(self) -> str:
        return self.rnd.choices(self.kind_names, weights=self.kind_weights, k=1)[0]

    def _spawn(self, p: Particle) -> None:
        self._assign(p, keep_position=False)

    def _assign(self, p: Particle, keep_position: bool) -> None:
        rnd = self.rnd
        kind = self._pick_kind()
        kt = KINDS[kind]
        p.kind = kind
        p.z = rnd.uniform(0.15, 1.0)
        vy = rnd.uniform(*kt["vy"])
        p.vy = vy
        p.rising = vy < 0
        p.size = (BASE_SIZE[kind] * self.cfg.size
                  * rnd.uniform(0.75, 1.35) * (0.55 + 0.45 * p.z))
        if not keep_position:
            if p.rising:
                p.y = self.h + rnd.uniform(10, 90)
            else:
                p.y = -rnd.uniform(10, 90)
            p.x = rnd.uniform(-20, self.w + 20)
        p.rot = rnd.uniform(0, 360)
        rs = kt["rot"]
        p.rot_spd = rnd.uniform(*rs) * rnd.choice((-1, 1)) if rs and rs[1] > 0 else 0.0
        p.phase = rnd.uniform(0, math.tau)
        p.phase_spd = rnd.uniform(0.9, 2.2) * rnd.choice((-1, 1))
        p.sway = rnd.uniform(*kt["sway"]) if kt["sway"] else 0.0
        p.flip = rnd.uniform(0, math.tau)
        p.flip_spd = rnd.uniform(1.2, 2.6) * rnd.choice((-1, 1)) if kt["flip"] else 0.0
        p.tw = kt["tw"]
        p.seed = rnd.uniform(0, math.tau)
        p.kx = 0.0
        p.ky = 0.0
        pal = self.palettes.get(kind) or [(255, 255, 255)]
        p.color = pal[rnd.randrange(len(pal))]
        p.glow = kind in (S.K_GOLDEN, S.K_FIREFLY)

    # ------------------------------------------------------------------ #
    #  Simulation
    # ------------------------------------------------------------------ #
    def tick(self, dt: float, cursor: Optional[Tuple[float, float]]) -> None:
        dt = max(0.001, min(dt, 0.05))
        self.t += dt
        gp = self.t
        self.gust = (0.55 * math.sin(gp * 0.45 + 1.1)
                     + 0.35 * math.sin(gp * 0.13)
                     + 0.25 * math.sin(gp * 1.31 + 2.2))
        wind_px = (self.cfg.wind / 100.0) * 80.0 + self.gust * 42.0
        self._wind_px = wind_px
        sp = self.cfg.speed
        kdec = math.exp(-4.5 * dt)
        mx = my = None
        if cursor is not None and self.cfg.mouse_interact:
            mx, my = cursor
        rnd = self.rnd
        particles = self.particles

        for p in particles:
            if mx is not None and p.kind != S.K_RAIN:
                dx = p.x - mx
                dy = p.y - my
                d2 = dx * dx + dy * dy
                if d2 < MOUSE_R2 and d2 > 0.01:
                    d = math.sqrt(d2)
                    f = (1.0 - d / MOUSE_R) * 1500.0 * dt * (0.4 + 0.6 * p.z)
                    p.kx += dx / d * f
                    p.ky += dy / d * f
            p.kx *= kdec
            p.ky *= kdec
            p.x += (wind_px * (0.35 + 0.65 * p.z)
                    + math.sin(p.phase) * p.sway * p.z * self.cfg.sway
                    + p.kx) * dt
            p.y += (p.vy * p.z * sp + p.ky) * dt
            p.phase += p.phase_spd * dt
            if p.rot_spd and self.cfg.tumble:
                p.rot += p.rot_spd * dt
            if p.flip_spd:
                p.flip += p.flip_spd * dt
            if p.kind == S.K_FIREFLY:
                p.vy += rnd.uniform(-70, 70) * dt
                p.vy = max(-32.0, min(32.0, p.vy))
            # recycle off-screen particles
            if p.rising:
                if p.y < -80:
                    self._spawn(p)
            elif p.y > self.h + 90:
                self._spawn(p)
            if p.x < -110:
                p.x = self.w + 90
            elif p.x > self.w + 110:
                p.x = -90

        particles.sort(key=_zkey)
        self._adjust_population()

    # ------------------------------------------------------------------ #
    #  Rendering
    # ------------------------------------------------------------------ #
    def _alpha(self, p: Particle, extra: float = 1.0) -> int:
        a = 255.0 * self.cfg.opacity * (0.35 + 0.65 * p.z) * extra
        if p.tw:
            s = 0.5 + 0.5 * math.sin(self.t * p.tw * 2.0 + p.seed)
            a *= 0.35 + 0.65 * s
        return int(max(0, min(255, a)))

    def paint(self, painter: QPainter, transparent: bool = True) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(0, 0, self.w, self.h)
        if transparent:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(rect, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        else:
            bg = QLinearGradient(0, 0, 0, self.h)
            bg.setColorAt(0.0, QColor("#101426"))
            bg.setColorAt(1.0, QColor("#1b2340"))
            painter.fillRect(rect, bg)
        for p in self.particles:
            self._drawers[p.kind](painter, p)
        painter.restore()

    @property
    def _drawers(self):
        try:
            return self.__drawers
        except AttributeError:
            self.__drawers = {
                S.K_SNOW: self._d_snow, S.K_SLUSH: self._d_slush,
                S.K_FROST: self._d_frost, S.K_PETAL: self._d_petal,
                S.K_RAIN: self._d_rain, S.K_LEAF: self._d_leaf,
                S.K_GOLDEN: self._d_golden, S.K_SPARK: self._d_spark,
                S.K_GLITTER: self._d_glitter, S.K_FIREFLY: self._d_firefly,
                S.K_HEART: self._d_heart, S.K_BAT: self._d_bat,
                S.K_PUMPKIN: self._d_pumpkin, S.K_GIFT: self._d_gift,
                S.K_CANE: self._d_cane,
            }
            return self.__drawers

    # ---- individual particle renderers ----
    def _d_snow(self, painter: QPainter, p: Particle) -> None:
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size, p.size)
        painter.setPen(QPen(QColor(p.color[0], p.color[1], p.color[2],
                                   self._alpha(p)), 0.16))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLines(list(SNOW_LINES))
        painter.restore()

    def _d_slush(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        r = p.size * 1.25
        painter.save()
        painter.translate(p.x, p.y)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], int(a * 0.45)))
        painter.drawEllipse(QPointF(0, 0), r, r)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], a))
        painter.drawEllipse(QPointF(0, 0), r * 0.6, r * 0.6)
        painter.restore()

    def _d_frost(self, painter: QPainter, p: Particle) -> None:
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size * 1.4, p.size * 1.4)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], self._alpha(p)))
        painter.drawPolygon(STAR4_PTS)
        painter.restore()

    def _d_petal(self, painter: QPainter, p: Particle) -> None:
        sx = 0.35 + 0.65 * abs(math.sin(p.flip)) if p.flip_spd else 1.0
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size * sx, p.size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], self._alpha(p)))
        painter.drawEllipse(QRectF(-0.45, -0.7, 0.9, 1.4))
        painter.restore()

    def _d_rain(self, painter: QPainter, p: Particle) -> None:
        pen = QPen(QColor(p.color[0], p.color[1], p.color[2],
                          int(self._alpha(p) * 0.8)),
                   max(0.9, 1.4 * p.z * self.cfg.size))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        length = (12.0 + 18.0 * p.z) * max(1.0, self.cfg.size)
        painter.drawLine(QLineF(p.x - self._wind_px * 0.05 * p.z, p.y - length,
                                p.x, p.y))

    def _draw_leaf_shape(self, painter: QPainter, p: Particle,
                         a: int, halo: bool) -> None:
        sx = 0.3 + 0.7 * abs(math.cos(p.flip)) if p.flip_spd else 1.0
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size * sx, p.size)
        if halo:
            g = QRadialGradient(0.0, 0.05, 2.1)
            g.setColorAt(0.0, QColor(255, 210, 70, int(a * 0.33)))
            g.setColorAt(1.0, QColor(255, 210, 70, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(g)
            painter.drawEllipse(QPointF(0.0, 0.05), 2.1, 2.1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], a))
        painter.drawPolygon(LEAF_PTS)
        painter.setPen(QPen(QColor(0, 0, 0, 70), 0.06))
        painter.drawLine(QLineF(0.0, 0.4, 0.0, 0.85))    # stem
        painter.setPen(QPen(QColor(255, 255, 255, 40), 0.05))
        painter.drawLine(QLineF(0.0, -0.42, 0.0, 0.42))  # vein
        painter.restore()

    def _d_leaf(self, painter: QPainter, p: Particle) -> None:
        self._draw_leaf_shape(painter, p, self._alpha(p), halo=False)

    def _d_golden(self, painter: QPainter, p: Particle) -> None:
        self._draw_leaf_shape(painter, p, self._alpha(p), halo=True)

    def _d_spark(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size * 1.6, p.size * 1.6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], a))
        painter.drawPolygon(STAR4_PTS)
        painter.rotate(45)
        painter.scale(0.45, 0.45)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], int(a * 0.55)))
        painter.drawPolygon(STAR4_PTS)
        painter.restore()

    def _d_glitter(self, painter: QPainter, p: Particle) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2],
                                self._alpha(p)))
        r = max(0.8, p.size)
        painter.drawEllipse(QPointF(p.x, p.y), r, r)
        painter.restore()

    def _d_firefly(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        pulse = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(self.t * p.tw * 2.0 + p.seed)) ** 2
        r = p.size * 2.4 * (0.7 + 0.3 * pulse)
        g = QRadialGradient(p.x, p.y, r)
        g.setColorAt(0.0, QColor(255, 255, 235, int(a * pulse)))
        g.setColorAt(0.3, QColor(p.color[0], p.color[1], p.color[2],
                                 int(a * 0.6 * pulse)))
        g.setColorAt(1.0, QColor(p.color[0], p.color[1], p.color[2], 0))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(g)
        painter.drawEllipse(QPointF(p.x, p.y), r, r)
        painter.restore()

    def _d_heart(self, painter: QPainter, p: Particle) -> None:
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(8.0 * math.sin(self.t * 1.5 + p.seed))
        painter.scale(p.size, p.size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2],
                                int(self._alpha(p) * 0.95)))
        painter.drawPolygon(HEART_PTS)
        painter.restore()

    def _d_bat(self, painter: QPainter, p: Particle) -> None:
        flap = 0.55 + 0.45 * abs(math.sin(self.t * 9.0 + p.seed))
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(10.0 * math.sin(self.t * 2.2 + p.seed))
        painter.scale(p.size, p.size * flap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2],
                                int(self._alpha(p) * 0.92)))
        painter.drawPolygon(BAT_PTS)
        painter.restore()

    def _d_pumpkin(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size, p.size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], a))
        painter.drawEllipse(QRectF(-0.55, -0.45, 1.1, 0.9))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 70), 0.05))
        painter.drawEllipse(QRectF(-0.30, -0.45, 0.60, 0.9))
        painter.drawEllipse(QRectF(-0.11, -0.45, 0.22, 0.9))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(84, 120, 46, a))
        painter.drawRect(QRectF(-0.06, -0.62, 0.12, 0.2))
        painter.restore()

    def _d_gift(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size, p.size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], a))
        painter.drawRoundedRect(QRectF(-0.55, -0.42, 1.1, 0.84), 0.08, 0.08)
        painter.setBrush(QColor(250, 250, 255, int(a * 0.9)))
        painter.drawRect(QRectF(-0.09, -0.42, 0.18, 0.84))
        painter.drawRect(QRectF(-0.55, -0.06, 1.1, 0.16))
        painter.drawEllipse(QRectF(-0.30, -0.56, 0.26, 0.17))
        painter.drawEllipse(QRectF(0.04, -0.56, 0.26, 0.17))
        painter.restore()

    def _d_cane(self, painter: QPainter, p: Particle) -> None:
        a = self._alpha(p)
        painter.save()
        painter.translate(p.x, p.y)
        painter.rotate(p.rot)
        painter.scale(p.size, p.size)
        path = QPainterPath()
        path.moveTo(0.0, 0.55)
        path.lineTo(0.0, -0.25)
        path.arcTo(QRectF(0.0, -0.45, 0.4, 0.4), 180.0, -180.0)
        pen = QPen(QColor(245, 245, 250, a), 0.18)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        pen = QPen(QColor(230, 30, 40, a), 0.10)
        pen.setDashPattern((1.6, 1.6))
        painter.setPen(pen)
        painter.drawPath(path)
        painter.restore()

