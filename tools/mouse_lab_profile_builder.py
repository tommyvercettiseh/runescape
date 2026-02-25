import json
import csv
from pathlib import Path
import statistics

def build_profile_from_mouse_lab(run_dir: str):
    run_dir = Path(run_dir)
    trials_path = run_dir / "trials.csv"

    rows = []
    with open(trials_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    def col(name):
        return [float(r[name]) for r in rows if r[name] != ""]

    def pct(vals, p):
        if not vals:
            return 0.0
        vals = sorted(vals)
        k = int((len(vals)-1) * (p/100))
        return vals[k]

    median_speed = col("median_speed_px_s")
    overshoot = col("overshoot_px")
    pre_click = col("pre_click_ms")
    hold = col("click_hold_ms")

    profile = {
        "speed_min_pct": pct(median_speed, 10),
        "speed_base_pct": pct(median_speed, 50),
        "speed_max_pct": pct(median_speed, 90),

        "overshoot_chance": sum(1 for o in overshoot if o > 3) / len(overshoot),

        "settle_min_s": pct(pre_click, 10) / 1000,
        "settle_max_s": pct(pre_click, 90) / 1000,
        "settle_chance": sum(1 for x in pre_click if x > 40) / len(pre_click),

        "press_min_s": pct(hold, 10) / 1000,
        "press_max_s": pct(hold, 90) / 1000,
    }

    out_path = run_dir / "ai_cursor_profile.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    return profile