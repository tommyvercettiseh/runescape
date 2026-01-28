from __future__ import annotations

import sys
import time
from pathlib import Path

import pyautogui

# ============================================================
# BOOTSTRAP (AUTO: zoekt Runescape root)
# ============================================================
HERE = Path(__file__).resolve()
ROOT = None
for p in [HERE] + list(HERE.parents):
    if (p / "core").exists() and (p / "config").exists():
        ROOT = p
        break

if ROOT is None:
    raise SystemExit("❌ Project root niet gevonden (map met 'core' en 'config').")

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ============================================================
# IMPORTS
# ============================================================
from ai_keyboard import hold_key_range
from core.move_to_area import move_to_area
from core.ai_cursor import click
from helpers.random_sleep import sleep_custom
from vision.colour_detection import detect_colour
from vision.colours import normalize_colour


# ============================================================
# KEYMAP
# ============================================================
ACTION_KEYS = {
    "tilt_up": "up",
    "tilt_down": "down",
    "rotate_left": "left",
    "rotate_right": "right",
}


# ============================================================
# RESET VIEW
# ============================================================
def reset_view(*, bot_id=1, do_scroll=True, scroll_ticks=10, scroll_amount=-240):
    move_to_area("Chat_Area", bot_id=bot_id)
    click()
    sleep_custom(1.10, 2.25)
    move_to_area("Bot_Area", bot_id=bot_id)
    sleep_custom(0.10, 0.25)

    if do_scroll:
        for _ in range(int(scroll_ticks)):
            pyautogui.scroll(int(scroll_amount))
            sleep_custom(0.02, 0.06)

    hold_key_range(ACTION_KEYS["tilt_up"], 2.0, 2.2)
    sleep_custom(0.12, 0.25)
    return True


# ============================================================
# STEP APPLY
# ============================================================
def apply_step(step: dict, *, bot_id=1):
    stype = str(step.get("type", "hold"))
    name = str(step.get("name", ""))

    if stype == "sleep":
        time.sleep(float(step.get("sec", step.get("sleep", 0.15))))
        return True

    if stype == "scroll":
        for _ in range(int(step.get("ticks", 6))):
            pyautogui.scroll(int(step.get("amount", -240)))
            sleep_custom(0.02, 0.06)
        return True

    key = ACTION_KEYS.get(name)
    if not key:
        return False

    hold_key_range(
        key,
        float(step.get("min_sec", 0.25)),
        float(step.get("max_sec", 0.40)),
    )
    return True


# ============================================================
# DEFAULT SEARCH PLAN
# ============================================================
DEFAULT_SEARCH_PLAN = [
    {"type": "hold", "name": "tilt_up", "min_sec": 2.0, "max_sec": 2.2},
    {"type": "scroll", "ticks": 8, "amount": -240},
    {"type": "hold", "name": "rotate_left", "min_sec": 0.45, "max_sec": 0.70},
    {"type": "hold", "name": "rotate_left", "min_sec": 0.45, "max_sec": 0.70},
    {"type": "hold", "name": "rotate_right", "min_sec": 0.90, "max_sec": 1.20},
    {"type": "hold", "name": "rotate_left", "min_sec": 0.40, "max_sec": 0.65},
    {"type": "hold", "name": "tilt_down", "min_sec": 0.20, "max_sec": 0.35},
]


# ============================================================
# FIND TARGET (NO CLICK)
# ============================================================
def assist_find_target(
    *,
    kleur="paars",
    area="Bot_Area",
    bot_id=1,
    min_size=80,

    reset_first=True,
    max_passes=1,
    pause_between=0.15,
    search_plan=None,

    timeout=0.0,
    interval=0.20,

    verbose=True,
    **_legacy,
):
    # aliases
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

    plan = search_plan or DEFAULT_SEARCH_PLAN
    start = time.time()

    def _hits():
        k = normalize_colour(kleur)  # bv "cyan" -> "cyaan"
        return detect_colour(
            k,
            area,
            None,            # 👈 belangrijk: geen extra positional "1"
            bot_id=bot_id,
            verbose=False,
            min_size=min_size,
        ) or 0

    def _wait(label, pass_nr):
        deadline = time.time() + float(timeout or 0.0)
        while True:
            h = _hits()
            if h > 0:
                return {
                    "found": True,
                    "pass": pass_nr,
                    "step": label,
                    "hits": int(h),
                    "elapsed_s": round(time.time() - start, 3),
                }
            if time.time() >= deadline:
                return None
            time.sleep(float(interval))

    if verbose:
        print("🔍 Searching target…")

    hit = _wait("direct", 0)
    if hit:
        if verbose:
            print("✅ Found (direct)")
        return hit

    for p in range(int(max_passes)):
        pass_nr = p + 1

        if reset_first:
            reset_view(bot_id=bot_id)
            time.sleep(float(pause_between))

            hit = _wait("reset", pass_nr)
            if hit:
                if verbose:
                    print("✅ Found after reset")
                return hit

        for step in plan:
            label = step.get("name", step.get("type", "?"))
            apply_step(step, bot_id=bot_id)
            time.sleep(float(pause_between))

            hit = _wait(label, pass_nr)
            if hit:
                if verbose:
                    print(f"✅ Found after step: {label}")
                return hit

    if verbose:
        print("❌ Not found")

    return {
        "found": False,
        "pass": int(max_passes),
        "step": None,
        "hits": 0,
        "elapsed_s": round(time.time() - start, 3),
    }


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    res = assist_find_target(
        kleur="cyaan",
        area="Bot_Area",
        bot_id=1,
        min_size=50,
        max_passes=2,
        timeout=0.8,
        interval=0.20,
        verbose=True,
    )
    print("RESULT:", res)
