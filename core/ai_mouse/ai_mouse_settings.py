from __future__ import annotations

import json
import os
from pathlib import Path

MOUSE_PROFILE: dict = {
    "speed_min": 800.0,
    "speed_max": 1800.0,
    "overshoot_min": 4.0,
    "overshoot_max": 18.0,
    "close_px": 2.2,
    "micro_tremor_max": 0.16,

    "pre_click_s": 0.10,
    "click_hold_s": 0.03,
    "settle_s": 0.08,
}

def load_master_profile(path: str) -> None:
    try:
        p = Path(path)
        if not p.exists():
            return
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            return
        for k, v in data.items():
            MOUSE_PROFILE[k] = v
    except Exception:
        return

def maybe_load_profile_from_env() -> None:
    path = os.getenv("AI_CURSOR_PROFILE", "").strip()
    if path and os.path.exists(path):
        load_master_profile(path)