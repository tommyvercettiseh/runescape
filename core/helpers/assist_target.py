from __future__ import annotations

import sys
import os
from pathlib import Path

# ============================================================
# BOOTSTRAP 🚀
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.helpers.assist_click_target import assist_click_target
from core.helpers.assist_find_target import assist_find_target


def assist_target(
    *,
    kleur="paars",
    area="Bot_Area",
    bot_id=None,            # safer default
    min_size=100,

    do_click=True,

    # FIND TUNING
    reset_first=True,
    max_passes=1,
    pause_between=0.15,
    search_plan=None,

    # CLICK TUNING
    speed_pct=100.0,
    prefer_center=True,
    center_bias=0.18,
    jitter_range=0,
    dilate_px=2,
    deep_erode_px=6,
    mode="deep_random",

    verbose=True,
    **_legacy,
):
    # ========================================================
    # RESOLVE BOT_ID 🧠
    # ========================================================
    if bot_id is None:
        bot_id = int(os.getenv("BOT_ID", "1"))

    # ========================================================
    # ALIASES 🔁
    # ========================================================
    if "colour" in _legacy and kleur == "paars":
        kleur = _legacy["colour"]
    if "color" in _legacy and kleur == "paars":
        kleur = _legacy["color"]
    if "area_name" in _legacy and area == "Bot_Area":
        area = _legacy["area_name"]
    if "min_px" in _legacy and min_size == 80:
        min_size = _legacy["min_px"]
    if "min_size_px" in _legacy and min_size == 80:
        min_size = _legacy["min_size_px"]

    kleur_txt = str(kleur).capitalize()

    verbose and print(
        f"⏳  🎯  Assist target starten   | Bot {bot_id} | {kleur_txt} | {area} | min {min_size}"
    )

    # ========================================================
    # FIND 🔍
    # ========================================================
    info = assist_find_target(
        kleur=kleur,
        area=area,
        bot_id=bot_id,
        min_size=min_size,
        reset_first=reset_first,
        max_passes=max_passes,
        pause_between=pause_between,
        search_plan=search_plan,
        verbose=verbose,
        **_legacy,
    )

    if not info.get("found"):
        verbose and print("❌  🎯  Target niet gevonden")
        return {"ok": False, "stage": "find", "info": info, "bot_id": bot_id}

    if not do_click:
        verbose and print("✅  🎯  Target gevonden      | click overgeslagen")
        return {"ok": True, "stage": "found_only", "info": info, "bot_id": bot_id}

    # ========================================================
    # CLICK 🖱️
    # ========================================================
    verbose and print("⏳  🖱️  Target aanklikken")

    ok = assist_click_target(
        kleur=kleur,
        area=area,
        bot_id=bot_id,
        min_size=min_size,
        speed_pct=speed_pct,
        prefer_center=prefer_center,
        center_bias=center_bias,
        jitter_range=jitter_range,
        dilate_px=dilate_px,
        deep_erode_px=deep_erode_px,
        mode=mode,
        verbose=verbose,
        **_legacy,
    )

    if not ok:
        verbose and print("❌  🖱️  Click mislukt")
        return {"ok": False, "stage": "click", "info": info, "bot_id": bot_id}

    verbose and print("✅  🎯  Target aangeklikt")

    return {"ok": True, "stage": "clicked", "info": info, "bot_id": bot_id}


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    res = assist_target(
        kleur="cyaan",
        area="Bot_Area",
        bot_id=None,
        min_size=100,
        max_passes=2,
        verbose=True,
    )

    print("\n📊  RESULTAAT:", "✅  SUCCES" if res["ok"] else "❌  GEFAALD")
    print(res)
