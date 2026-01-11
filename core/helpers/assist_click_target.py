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
# WAT: Zoekt paars en klikt dicht bij centrum, maar vermijdt mini-objects.
# WAAROM: Minder kans dat hij op kleine paarse rommel klikt (bloem etc).
# ============================================================
def assist_click_target(
    *,
    kleur="paars",
    area="Bot_Area",
    bot_id=1,
    prefer_center=True,
    center_bias=0.18,     # iets hoger: liever grotere targets
    min_size=80,          # hoger: negeert kleine paarse blobs
    jitter_range=10,      # nieuw: klik nét eromheen (menselijker)
    dilate_px=2,
    verbose=True,
) -> bool:

    if verbose:
        print("🟣 Target zoeken via kleurdetectie (centrum + anti-rommel)")

    ok = click_colour(
        kleur=kleur,
        area_name=area,
        bot_id=bot_id,
        prefer_center=prefer_center,
        center_bias=center_bias,
        min_size=min_size,
        jitter_range=jitter_range,
        dilate_px=dilate_px,
        verbose=verbose,
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
        area="Bot_Area",
        bot_id=BOT_ID,
        prefer_center=True,
        center_bias=0.18,
        min_size=200,
        jitter_range=10,
        verbose=True,
    )

    print("RESULT:", ok)
