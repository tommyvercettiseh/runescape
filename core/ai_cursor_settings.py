# core/ai_cursor_settings.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

# 1) Default profiel (fallback)
mouse_profile: Dict[str, float] = {
    # movement-side
    "speed_min": 700,
    "speed_max": 1500,
    "overshoot_min": 4,
    "overshoot_max": 22,
    "drift_scale": 0.0007,
    "micro_tremor_max": 0.22,
    "step_micro_pause_chance": 0.006,
    "step_long_pause_chance": 0.0012,

    # ai_cursor-side
    "pre_click_s": 0.085,
    "click_hold_s": 0.035,
    "close_px": 2.0,
    "settle_s": 0.065,
}

def _as_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def _stat(d: dict, key: str, which: str) -> Optional[float]:
    """
    master_profile.json shape:
      globals -> <metric> -> {p10,p50,p90,...}
    """
    try:
        blk = d["globals"][key]
        return _as_float(blk.get(which))
    except Exception:
        return None

def load_mouse_profile(profile_path: str | Path) -> Dict[str, float]:
    """
    Laadt een mouse profile JSON dat al "knobs" bevat (speed_min, pre_click_s, etc.)
    en merged met defaults.
    """
    p = Path(profile_path)
    data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return mouse_profile

    merged = dict(mouse_profile)
    for k, v in data.items():
        fv = _as_float(v)
        if fv is not None:
            merged[k] = fv

    mouse_profile.clear()
    mouse_profile.update(merged)
    return mouse_profile

def load_master_profile(master_path: str | Path) -> Dict[str, float]:
    """
    Laadt master_profile.json (stats: p10/p50/p90) en mapt naar runtime knobs.
    """
    p = Path(master_path)
    mp: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(mp, dict) or "globals" not in mp:
        return mouse_profile

    merged = dict(mouse_profile)

    # 1) SPEED
    # In master_profile heb je o.a. max_speed_px_s (p10/p90) die veel dichter bij "move snelheid" ligt
    # dan median_speed (die wordt omlaag getrokken door pauses/settle).
    s_min = _stat(mp, "max_speed_px_s", "p10")
    s_max = _stat(mp, "max_speed_px_s", "p90")
    if s_min is not None and s_max is not None:
        merged["speed_min"] = max(150.0, s_min * 0.55)   # conservatief: niet 1:1 piek
        merged["speed_max"] = max(merged["speed_min"] + 50.0, s_max * 0.70)

    # 2) OVERSHOOT
    o_min = _stat(mp, "overshoot_px", "p10")
    o_max = _stat(mp, "overshoot_px", "p90")
    if o_min is not None:
        merged["overshoot_min"] = max(1.0, o_min * 0.70)
    if o_max is not None:
        merged["overshoot_max"] = max(merged["overshoot_min"] + 1.0, o_max * 0.95)

    # 3) PRE-CLICK (ms → s)
    pre_ms = _stat(mp, "pre_click_ms", "p50")
    if pre_ms is not None:
        merged["pre_click_s"] = max(0.0, pre_ms / 1000.0)

    # 4) CLICK HOLD (ms → s)
    # Staat bij jou nu 0.0 in master_profile, dus we only set als het > 0 is.
    hold_ms = _stat(mp, "click_hold_ms", "p50")
    if hold_ms is not None and hold_ms > 0.0:
        merged["click_hold_s"] = max(0.006, min(0.22, hold_ms / 1000.0))

    # 5) Settle en close radius kun je uit tail_time / end_error afleiden (optioneel)
    tail_ms = _stat(mp, "tail_time_ms", "p50")
    if tail_ms is not None:
        merged["settle_s"] = max(0.02, min(0.25, tail_ms / 1000.0))

    end_err = _stat(mp, "end_radial_error", "p50")
    if end_err is not None:
        merged["close_px"] = max(1.0, min(12.0, end_err * 0.35))

    mouse_profile.clear()
    mouse_profile.update(merged)
    return mouse_profile