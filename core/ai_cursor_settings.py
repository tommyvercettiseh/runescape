#===========================================================================
# ai_cursor_settings.py ✅ (Single Source of Truth)
#===========================================================================
# Doel:
# 1) Oude defaults blijven werken (oude manier)
# 2) 1 switch om over te stappen op persoonlijk profiel
# 3) Tweedeling:
#    behavior -> ai_cursor.py (settle, click, overshoot, tremor, etc)
#    motion   -> ai_cursor_movement.py (pad, timing, jitter, steps, etc)
#
# Gebruik:
#   PERSONAL_PROFILE = False  -> altijd defaults
#   PERSONAL_PROFILE = True   -> profile.json (waar aanwezig) override defaults
#
# Profile file:
#   PROFILE_PATH = "mouse_profile/profile_all_time.json"
#===========================================================================

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional, Dict, Any


#===========================================================================
# Settings profile (TOP SWITCH) 🎛️
#===========================================================================
PERSONAL_PROFILE = False
PROFILE_PATH = Path("mouse_profile/profile_all_time.json")

# Optioneel: per scenario overrides (zonder profile file)
# Bijvoorbeeld: SCENARIO_OVERRIDES["PRECISION_SMALL"]["behavior"]["overshoot_max_px"]=38
SCENARIO_OVERRIDES: Dict[str, Dict[str, Dict[str, Any]]] = {}


#===========================================================================
# Data models 🧩
#===========================================================================
@dataclass(frozen=True)
class BehaviorConfig:
    # click / settle / micro
    settle_chance: float = 0.86
    settle_min_s: float = 0.05
    settle_max_s: float = 0.22
    settle_long_chance: float = 0.11
    settle_long_min_s: float = 0.28
    settle_long_max_s: float = 1.10

    # overshoot / undershoot / pre-click nudge
    overshoot_chance: float = 0.22
    overshoot_min_px: int = 6
    overshoot_max_px: int = 22

    undershoot_chance: float = 0.18

    pre_click_chance: float = 0.42
    pre_click_px_min: int = 1
    pre_click_px_max: int = 4

    # tail feel
    micro_pause_chance: float = 0.35
    tremor_chance: float = 0.35
    tremor_px_min: int = 1
    tremor_px_max: int = 4

    # persona / speed
    persona: Optional[str] = None         # "precise" | "fast" | "careful" | "distracted"
    speed_mult: float = 1.0              # multiplies speed_pct in ai_cursor


@dataclass(frozen=True)
class MotionConfig:
    # Movement-only tuning (ai_cursor_movement)
    # Houd dit bewust compact: alleen dingen die écht het pad/timing bepalen.
    # Als je movement module nog geen tuning ondersteunt: later mappen we dit 1-op-1.
    target_hz: float = 125.0
    steps_min: int = 18
    steps_max: int = 48
    jitter_px: float = 0.8
    accel_bias: float = 0.15
    decel_bias: float = 0.55

    # Belangrijk: overshoot in movement uit, omdat behavior het regelt
    movement_overshoot_chance: float = 0.0


@dataclass(frozen=True)
class CursorConfig:
    behavior: BehaviorConfig = BehaviorConfig()
    motion: MotionConfig = MotionConfig()


#===========================================================================
# Helpers 🔧
#===========================================================================
def _read_json(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _merge_dict_into_dataclass(dc_obj, patch: Dict[str, Any]):
    # Only apply keys that exist on the dataclass
    data = dc_obj.__dict__.copy()
    for k, v in patch.items():
        if k in data and v is not None:
            data[k] = v
    return dc_obj.__class__(**data)


def _get_profile() -> Optional[dict]:
    if not PERSONAL_PROFILE:
        return None
    return _read_json(PROFILE_PATH)


#===========================================================================
# Public API ✅
#===========================================================================
def get_cursor_config(scenario_label: Optional[str] = None) -> CursorConfig:
    """
    Returns:
      CursorConfig(behavior=..., motion=...)
    Merge order:
      defaults -> profile.json (if PERSONAL_PROFILE True) -> scenario overrides
    """
    cfg = CursorConfig()

    prof = _get_profile()
    if isinstance(prof, dict):
        # profile layout suggestion:
        # { "behavior": {...}, "motion": {...} }
        if isinstance(prof.get("behavior"), dict):
            b = _merge_dict_into_dataclass(cfg.behavior, prof["behavior"])
            cfg = CursorConfig(behavior=b, motion=cfg.motion)
        if isinstance(prof.get("motion"), dict):
            m = _merge_dict_into_dataclass(cfg.motion, prof["motion"])
            cfg = CursorConfig(behavior=cfg.behavior, motion=m)

    if scenario_label and scenario_label in SCENARIO_OVERRIDES:
        over = SCENARIO_OVERRIDES[scenario_label]
        if isinstance(over.get("behavior"), dict):
            b = _merge_dict_into_dataclass(cfg.behavior, over["behavior"])
            cfg = CursorConfig(behavior=b, motion=cfg.motion)
        if isinstance(over.get("motion"), dict):
            m = _merge_dict_into_dataclass(cfg.motion, over["motion"])
            cfg = CursorConfig(behavior=cfg.behavior, motion=m)

    return cfg