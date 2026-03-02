from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Optional, Dict, Any

# ============================================================
# 🎛️ Top switch
# ============================================================
PERSONAL_PROFILE = True

# relative to repo root when running as module: python -m core.ai_keyboard...
PROFILE_PATH = Path("tools/keyboard_lab/master_profile.json")
PERSONAL_PROFILE = True

SCENARIO_OVERRIDES: Dict[str, Dict[str, Dict[str, Any]]] = {}

# ============================================================
# Data model
# ============================================================
@dataclass(frozen=True)
class KeyboardBehaviorConfig:
    press_min_s: float = 0.012
    press_max_s: float = 0.040

    hold_min_s: float = 0.050
    hold_max_s: float = 0.220

    type_interval_min_s: float = 0.018
    type_interval_max_s: float = 0.060

    pause_chance: float = 0.06
    pause_min_s: float = 0.14
    pause_max_s: float = 0.65

    # corrections
    backspace_per_100_keys: float = 5.0
    correction_chain_p50: float = 2.0
    correction_chain_p90: float = 5.0

    # optional typos
    mistake_chance: float = 0.02
    mistake_fix_chance: float = 0.88

    force_lower_default: bool = True

@dataclass(frozen=True)
class KeyboardConfig:
    behavior: KeyboardBehaviorConfig = KeyboardBehaviorConfig()

# ============================================================
# Helpers
# ============================================================
def _read_json(path: Path) -> Optional[dict]:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def _merge(dc_obj, patch: Dict[str, Any]):
    data = dc_obj.__dict__.copy()
    for k, v in patch.items():
        if k in data and v is not None:
            data[k] = v
    return dc_obj.__class__(**data)

def get_keyboard_config(scenario_label: Optional[str] = None) -> KeyboardConfig:
    cfg = KeyboardConfig()

    if PERSONAL_PROFILE:
        prof = _read_json(PROFILE_PATH)
        if isinstance(prof, dict) and isinstance(prof.get("behavior"), dict):
            cfg = KeyboardConfig(behavior=_merge(cfg.behavior, prof["behavior"]))

    if scenario_label and scenario_label in SCENARIO_OVERRIDES:
        over = SCENARIO_OVERRIDES[scenario_label]
        if isinstance(over.get("behavior"), dict):
            cfg = KeyboardConfig(behavior=_merge(cfg.behavior, over["behavior"]))

    return cfg