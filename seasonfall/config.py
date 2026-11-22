"""SeasonFall configuration: dataclass + JSON persistence with platform paths."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field as dc_field, fields
from pathlib import Path

from .util import dbg, is_linux, is_macos, is_windows

CONFIG_VERSION = 1

SEASON_KEYS = ("auto", "winter", "spring", "summer", "autumn",
               "halloween", "christmas", "valentine")
QUALITY_KEYS = ("low", "medium", "high", "ultra")
MONITOR_KEYS = ("all", "primary")
HEMISPHERE_KEYS = ("auto", "north", "south")


def config_dir() -> Path:
    override = os.environ.get("SEASONFALL_CONFIG_DIR")
    if override:
        return Path(override)
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "SeasonFall"
    if is_macos():
        return Path.home() / "Library" / "Application Support" / "SeasonFall"
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "SeasonFall"


def config_path() -> Path:
    return config_dir() / "config.json"


def _clamp(v, lo, hi):
    try:
        v = type(lo)(v)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, v))


@dataclass
class Config:
    # look & feel
    season: str = "auto"            # SEASON_KEYS (single; used when mix is empty)
    mix: list = dc_field(default_factory=list)   # e.g. ["winter","spring","autumn"]
    density: int = 40               # 1..100  — "how much falls"
    speed: float = 1.0              # 0.25..3.0
    wind: int = 0                   # -100..100 (left ↔ right)
    size: float = 1.0               # 0.5..2.5 — particle size / thickness
    opacity: float = 0.9            # 0.15..1.0
    sway: float = 1.0               # 0..2.5
    tumble: bool = True             # rotation / 3D flip
    golden_share: int = 18          # % golden leaves in autumn
    rain: bool = True               # spring drizzle
    # behaviour
    mouse_interact: bool = True     # cursor pushes particles
    click_through: bool = True      # clicks pass to desktop/apps
    monitors: str = "all"           # MONITOR_KEYS
    quality: str = "high"           # QUALITY_KEYS
    fps: int = 60                   # 24 | 30 | 60
    adaptive_quality: bool = False  # auto-reduce count under load (off = constant snowfall)
    auto_pause_battery: bool = True # pause when laptop unplugged
    hemisphere: str = "auto"        # HEMISPHERE_KEYS (for season = auto)
    holiday_specials: bool = True   # 🎄 🎃 💖 join the fall near the date
    # bookkeeping
    first_run_done: bool = False
    startup_prompted: bool = False
    tray_tip_shown: bool = False    # one-time "look near the clock" tip
    version: int = CONFIG_VERSION

    # ---------- persistence ----------
    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or config_path()
        cfg = cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            dbg("no config file yet:", path)
            return cfg
        except Exception as exc:  # corrupted file → defaults
            dbg("config unreadable, using defaults:", exc)
            return cfg
        known = {f.name for f in fields(cls)}
        for key, val in raw.items():
            if key in known:
                setattr(cfg, key, val)
        cfg.sanitize()
        return cfg

    def save(self, path: Path | None = None) -> Path:
        path = path or config_path()
        self.version = CONFIG_VERSION
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(asdict(self), indent=2, sort_keys=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".config-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
        return path

    @staticmethod
    def exists() -> bool:
        return config_path().exists()

    # ---------- validation ----------
    def sanitize(self) -> None:
        if self.season not in SEASON_KEYS:
            self.season = "auto"
        if self.quality not in QUALITY_KEYS:
            self.quality = "high"
        if self.monitors not in MONITOR_KEYS:
            self.monitors = "all"
        if self.hemisphere not in HEMISPHERE_KEYS:
            self.hemisphere = "auto"
        # mix: keep valid, unique season keys, max 6 layers
        clean_mix = []
        for key in self.mix:
            if key in SEASON_KEYS and key not in clean_mix:
                clean_mix.append(key)
        self.mix = clean_mix[:6]
        self.density = int(_clamp(self.density, 1, 100))
        self.speed = _clamp(self.speed, 0.25, 3.0)
        self.wind = int(_clamp(self.wind, -100, 100))
        self.size = _clamp(self.size, 0.5, 2.5)
        self.opacity = _clamp(self.opacity, 0.15, 1.0)
        self.sway = _clamp(self.sway, 0.0, 2.5)
        self.golden_share = int(_clamp(self.golden_share, 0, 100))
        self.fps = int(_clamp(self.fps, 24, 60))

    def clone(self) -> "Config":
        return Config(**asdict(self))
