from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = BASE_DIR / "sessions"
OUT_PATH = BASE_DIR / "master_profile.json"

MOD_KEYS = {"shift", "shift_l", "shift_r", "control", "control_l", "control_r", "alt", "alt_l", "alt_r", "meta", "cmd"}
EDIT_KEYS = {"backspace", "delete"}
ENTER_KEYS = {"enter", "return", "kp_enter"}
SPACE_KEYS = {"space"}

def normalize_key(k: str) -> str:
    k = (k or "").strip().lower()
    if k in {"return", "kp_enter"}:
        return "enter"
    if k in {"escape"}:
        return "esc"
    if k in {"prior"}:
        return "page_up"
    if k in {"next"}:
        return "page_down"
    return k

def key_class(k: str) -> str:
    if k in MOD_KEYS:
        return "mod"
    if k in EDIT_KEYS:
        return "edit"
    if k in ENTER_KEYS:
        return "enter"
    if k in SPACE_KEYS:
        return "space"
    if len(k) == 1 and k.isalpha():
        return "alpha"
    if len(k) == 1 and k.isdigit():
        return "digit"
    return "other"

def pct(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[f])
    return float(s[f] + (s[c] - s[f]) * (k - f))

def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def summarize(xs: List[float]) -> dict:
    return {
        "n": len(xs),
        "mean": mean(xs),
        "p50": pct(xs, 50),
        "p75": pct(xs, 75),
        "p90": pct(xs, 90),
        "p95": pct(xs, 95),
        "p99": pct(xs, 99),
    }

def find_event_files() -> List[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.glob("*/*events.jsonl"))

def build_master_from_events(event_files: List[Path]) -> dict:
    downs: Dict[str, float] = {}
    last_up_ts: Optional[float] = None
    last_event_ts: Optional[float] = None

    holds_by_class: Dict[str, List[float]] = {}
    iki_ms: List[float] = []
    gap_ms: List[float] = []
    correction_chains: List[int] = []
    chain_len = 0

    keypress_count = 0
    backspace_count = 0

    for path in event_files:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)

                ts = float(e.get("ts", 0))
                ev = str(e.get("event", "")).lower()
                key = normalize_key(str(e.get("key", "")))

                kcls = key_class(key)

                if last_event_ts is not None:
                    gap_ms.append((ts - last_event_ts) * 1000.0)
                last_event_ts = ts

                if ev == "down":
                    downs[key] = ts
                    keypress_count += 1

                    if key == "backspace":
                        backspace_count += 1
                        chain_len += 1
                    else:
                        if chain_len > 0:
                            correction_chains.append(chain_len)
                            chain_len = 0

                    if last_up_ts is not None:
                        iki_ms.append((ts - last_up_ts) * 1000.0)

                elif ev == "up":
                    last_up_ts = ts
                    t0 = downs.pop(key, None)
                    if t0 is not None:
                        hold = (ts - t0) * 1000.0
                        holds_by_class.setdefault(kcls, []).append(hold)

    if chain_len > 0:
        correction_chains.append(chain_len)

    holds_summary = {k: summarize(v) for k, v in holds_by_class.items()}
    iki_summary = summarize(iki_ms)
    gap_summary = summarize(gap_ms)
    corr_summary = summarize([float(x) for x in correction_chains])

    alpha = holds_by_class.get("alpha", [])
    alpha_p50 = pct(alpha, 50) if alpha else 70.0
    alpha_p90 = pct(alpha, 90) if alpha else 140.0

    pauses = [g for g in gap_ms if g > 250.0]
    pause_ch = (len(pauses) / max(1, len(gap_ms))) if gap_ms else 0.08
    pause_ch = max(0.02, min(0.35, pause_ch))

    behavior = {
        "press_min_s": 0.012,
        "press_max_s": 0.040,

        "hold_min_s": max(0.035, min(0.140, (alpha_p50 / 1000.0) * 0.85)),
        "hold_max_s": max(0.090, min(0.380, (alpha_p90 / 1000.0) * 1.10)),

        "type_interval_min_s": max(0.012, min(0.060, (iki_summary["p50"] / 1000.0) * 0.55 if iki_summary["n"] else 0.020)),
        "type_interval_max_s": max(0.020, min(0.110, (iki_summary["p75"] / 1000.0) * 0.85 if iki_summary["n"] else 0.055)),

        "pause_chance": float(pause_ch),
        "pause_min_s": 0.14,
        "pause_max_s": 0.65,

        "backspace_per_100_keys": (backspace_count / max(1, keypress_count)) * 100.0,
        "correction_chain_p50": corr_summary["p50"],
        "correction_chain_p90": corr_summary["p90"],

        "mistake_chance": 0.02,
        "mistake_fix_chance": 0.88,

        "force_lower_default": True,
    }

    return {
        "meta": {
            "created_ts": time.time(),
            "sessions": len(event_files),
            "source": "keyboard_lab master builder",
        },
        "stats": {
            "keypress_count": keypress_count,
            "backspace_count": backspace_count,
            "holds_by_class_ms": holds_summary,
            "iki_ms": iki_summary,
            "event_gap_ms": gap_summary,
            "correction_chains": corr_summary,
        },
        "behavior": behavior,
    }

def main():
    files = find_event_files()
    if not files:
        print("❌ No sessions found in tools/keyboard_lab/sessions/")
        return

    profile = build_master_from_events(files)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    print("✅ Master profile built")
    print(f"Sessions: {profile['meta']['sessions']}")
    print(f"Out: {OUT_PATH}")

if __name__ == "__main__":
    main()