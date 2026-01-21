from __future__ import annotations

import sys
from pathlib import Path

# ============================================================
# BOOTSTRAP
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
from core.click_colour import click_colour


# ============================================================
# ASSIST CLICK TARGET (COLOUR BASED)
# ============================================================
def assist_click_target(
    *,
    kleur="paars",
    area="Bot_Area",
    bot_id=1,
    speed_pct: float = 100.0,
    prefer_center=True,
    center_bias=0.18,
    min_size=80,
    jitter_range=1,
    dilate_px=2,
    deep_erode_px=5,
    mode="deep_random",
    verbose=True,

    # ✅ nieuw (maar defaults houden alles exact hetzelfde)
    pick_strategy: str = "random",     # "random" | "nearest"
    nearest_k: int = 200,
    nearest_weighted: bool = True,
) -> bool:

    if verbose:
        print("🟣 Target zoeken via kleurdetectie (centrum + anti-rommel)")

    ok = click_colour(
        kleur,
        area,
        bot_id=bot_id,
        mode=mode,
        deep_erode_px=deep_erode_px,
        jitter_range=jitter_range,
        min_size=min_size,
        dilate_px=dilate_px,
        prefer_center=prefer_center,
        center_bias=center_bias,
        speed_pct=speed_pct,
        verbose=verbose,

        # ✅ doorgeven aan click_colour
        pick_strategy=pick_strategy,
        nearest_k=nearest_k,
        nearest_weighted=nearest_weighted,
    )

    if not ok and verbose:
        print("🫥 Geen target gevonden")
    if ok and verbose:
        print("✅ Target aangeklikt")

    return ok


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    BOT_ID = 1

    ok = assist_click_target(
        kleur="paars",
        area="Bot_Area_Center",
        bot_id=BOT_ID,
        speed_pct=200,
        prefer_center=True,
        center_bias=0.18,
        min_size=200,
        jitter_range=10,
        verbose=True,

        # ✅ alleen als je het wil activeren
        pick_strategy="nearest",
        nearest_k=150,
        nearest_weighted=True,
    )

    print("RESULT:", ok)
