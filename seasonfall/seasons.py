"""Season + holiday definitions, palettes and the auto-season resolver.

Every season owns a set of particle "recipes" (kind, weight) and a palette.
The engine (engine.py) knows how to simulate & draw each kind.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import date


# --------------------------------------------------------------------------- #
#  Particle kinds understood by the engine
# --------------------------------------------------------------------------- #
K_SNOW = "snow"          # 6-arm dendrite snowflake
K_SLUSH = "slush"        # soft snowball
K_FROST = "frost"        # tiny twinkling frost star
K_PETAL = "petal"        # cherry blossom petal
K_RAIN = "rain"          # drizzle streak
K_LEAF = "leaf"          # tumbling autumn leaf
K_GOLDEN = "golden"      # glowing golden leaf
K_SPARK = "spark"        # rising sun sparkle (summer)
K_GLITTER = "glitter"    # heat glitter dust (summer)
K_FIREFLY = "firefly"    # pulsing firefly glow (summer)
K_HEART = "heart"        # valentine heart
K_BAT = "bat"            # halloween bat
K_PUMPKIN = "pumpkin"    # halloween pumpkin
K_GIFT = "gift"          # christmas gift
K_CANE = "cane"          # candy cane


@dataclass(frozen=True)
class SeasonSpec:
    key: str
    name: str
    emoji: str
    accent: str                       # hex color used by the GUI
    kinds: tuple = dc_field(default_factory=tuple)   # ((kind, weight), ...)
    palettes: dict = dc_field(default_factory=dict)  # kind -> [(r, g, b), ...]


WINTER = SeasonSpec(
    key="winter", name="Winter", emoji="❄️", accent="#7fd4ff",
    kinds=((K_SNOW, 62), (K_FROST, 20), (K_SLUSH, 18)),
    palettes={
        K_SNOW: [(255, 255, 255), (235, 244, 255), (214, 235, 255), (190, 215, 245)],
        K_SLUSH: [(255, 255, 255), (228, 240, 255)],
        K_FROST: [(205, 232, 255), (170, 214, 255), (255, 255, 255)],
    },
)

SPRING = SeasonSpec(
    key="spring", name="Spring", emoji="🌸", accent="#ff9ec7",
    kinds=((K_PETAL, 78), (K_RAIN, 22)),
    palettes={
        K_PETAL: [(255, 183, 197), (255, 158, 181), (255, 205, 214),
                  (247, 143, 167), (255, 240, 245)],
        K_RAIN: [(190, 220, 255)],
    },
)

SUMMER = SeasonSpec(
    key="summer", name="Summer", emoji="☀️", accent="#ffd166",
    kinds=((K_SPARK, 52), (K_GLITTER, 30), (K_FIREFLY, 18)),
    palettes={
        K_SPARK: [(255, 214, 120), (255, 236, 160), (255, 247, 214), (255, 190, 92)],
        K_GLITTER: [(255, 255, 255), (255, 228, 150), (255, 250, 220)],
        K_FIREFLY: [(206, 255, 120), (255, 244, 130)],
    },
)

AUTUMN = SeasonSpec(
    key="autumn", name="Autumn", emoji="🍂", accent="#ff9f43",
    kinds=((K_LEAF, 100),),
    palettes={
        K_LEAF: [(226, 88, 34), (240, 138, 44), (212, 60, 30),
                 (188, 122, 32), (166, 96, 28), (245, 160, 60)],
        K_GOLDEN: [(255, 196, 0), (255, 214, 60), (255, 170, 40), (255, 231, 118)],
    },
)

HALLOWEEN = SeasonSpec(
    key="halloween", name="Halloween", emoji="🎃", accent="#b07cff",
    kinds=((K_BAT, 38), (K_LEAF, 42), (K_PUMPKIN, 20)),
    palettes={
        K_BAT: [(38, 28, 58), (52, 38, 78), (25, 18, 40)],
        K_LEAF: [(226, 88, 34), (240, 138, 44), (188, 122, 32)],
        K_PUMPKIN: [(255, 122, 24), (235, 90, 10), (255, 148, 48)],
    },
)

CHRISTMAS = SeasonSpec(
    key="christmas", name="Christmas", emoji="🎄", accent="#ff5d5d",
    kinds=((K_SNOW, 68), (K_GIFT, 18), (K_CANE, 14)),
    palettes={
        K_SNOW: [(255, 255, 255), (224, 240, 255), (205, 228, 255)],
        K_GIFT: [(220, 40, 50), (60, 160, 90), (230, 60, 70), (70, 120, 220),
                 (250, 200, 60)],
        K_CANE: [(235, 235, 245), (230, 30, 40)],
    },
)

VALENTINE = SeasonSpec(
    key="valentine", name="Valentine", emoji="💖", accent="#ff6b9d",
    kinds=((K_HEART, 72), (K_PETAL, 28)),
    palettes={
        K_HEART: [(255, 80, 120), (255, 105, 140), (255, 140, 170), (232, 54, 104)],
        K_PETAL: [(255, 183, 197), (255, 205, 214), (255, 158, 181)],
    },
)

SPECS = {s.key: s for s in
         (WINTER, SPRING, SUMMER, AUTUMN, HALLOWEEN, CHRISTMAS, VALENTINE)}

GUI_SEASON_ORDER = ("auto", "winter", "spring", "summer", "autumn")


# --------------------------------------------------------------------------- #
#  Holiday windows (month, day) inclusive
# --------------------------------------------------------------------------- #
_HOLIDAYS = (
    ("christmas", ((12, 10), (1, 6))),
    ("halloween", ((10, 24), (10, 31))),
    ("valentine", ((2, 7), (2, 14))),
)


def _in_window(today: date, start: tuple, end: tuple) -> bool:
    sm, sd = start
    em, ed = end
    s = date(today.year, sm, sd)
    e = date(today.year, em, ed)
    if s <= e:
        return s <= today <= e
    # window wraps new year (christmas)
    return today >= s or today <= e


def _month_season(month: int, south: bool) -> str:
    if south:
        month = (month + 5) % 12 + 1
    if month in (12, 1, 2):
        return "winter"
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    return "autumn"


def guess_hemisphere() -> str:
    """Crude hemisphere guess from the timezone region name — default fallback."""
    try:
        import time
        zone = time.tzname[0] or ""
        region = zone.split("/")[0]
        south_regions = {"Australia", "Pacific", "Antarctica", "America/Argentina",
                         "Chile", "Brazil", "NZ"}
        if region in south_regions or "Sao_Paulo" in zone or "Santiago" in zone:
            return "south"
        return "north"
    except Exception:
        return "north"


def resolve_season(cfg, today: date | None = None) -> SeasonSpec:
    """Pick the active season honouring holidays + auto mode."""
    today = today or date.today()
    if getattr(cfg, "holiday_specials", True):
        for key, (start, end) in _HOLIDAYS:
            if _in_window(today, start, end):
                return SPECS[key]
    key = cfg.season
    if key == "auto":
        hemi = cfg.hemisphere
        if hemi == "auto":
            hemi = guess_hemisphere()
        key = _month_season(today.month, hemi == "south")
    return SPECS.get(key, WINTER)
