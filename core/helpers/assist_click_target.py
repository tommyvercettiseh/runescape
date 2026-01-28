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
# Backwards compatible: accepteert oude/extra kwargs zonder crash
# Default tuning:
#   jitter_range = 2
#   deep_erode_px = 3
# ============================================================
def assist_click_target(
    *,
    kleur="paars",
    area="Bot_Area",
    bot_id=1,

    speed_pct=100.0,
    prefer_center=True,
    center_bias=0.18,

    min_size=80,
    jitter_range=0,          # ✅ jouw default
    dilate_px=2,
    deep_erode_px=8,         # ✅ jouw default
    mode="deep_random",

    verbose=True,

    # optioneel (blijft bestaan, maar hoeft niet)
    pick_strategy="random",  # "random" | "nearest"
    nearest_k=200,
    nearest_weighted=True,

    # ✅ legacy-safe: slik alles in wat oudere code eventueel meestuurt
    **_legacy,
):
    # ------------------------------------------------------------
    # LEGACY ALIASES (oude param namen blijven werken)
    # ------------------------------------------------------------
    # Veel voorkomende varianten:
    # colour/color -> kleur
    # area_name    -> area
    # min_px       -> min_size
    # erode_px     -> deep_erode_px
    # dilate       -> dilate_px
    if "colour" in _legacy and kleur == "paars":
        kleur = _legacy["colour"]
    if "color" in _legacy and kleur == "paars":
        kleur = _legacy["color"]
    if "area_name" in _legacy and area == "Bot_Area":
        area = _legacy["area_name"]

    if "min_px" in _legacy and min_size == 80:
        min_size = _legacy["min_px"]

    if "erode_px" in _legacy and deep_erode_px == 3:
        deep_erode_px = _legacy["erode_px"]
    if "dilate" in _legacy and dilate_px == 2:
        dilate_px = _legacy["dilate"]

    # Sommige oude scripts sturen misschien "min_size_px" ofzo
    if "min_size_px" in _legacy and min_size == 80:
        min_size = _legacy["min_size_px"]

    if verbose:
        print(f"🎯 Assist_Click_Target | kleur={kleur} | area={area} | min_size={min_size}")

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

        # optioneel doorgeven
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
    ok = assist_click_target(
        kleur="cyaan",
        area="Bot_Area_Center",
        bot_id=1,
        min_size=100,        # ✅ voorbeeld: dit is wat jij wil kunnen doen
        verbose=True,
    )
    print("RESULT:", ok)
