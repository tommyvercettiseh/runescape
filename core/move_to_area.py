from __future__ import annotations

# ============================================================
# BOOTSTRAP
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Runescape/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import random

# ✅ Robuuste import (na ai_cursor refactor)
try:
    from core.ai_cursor import move_cursor, CursorMotionConfig
except Exception:
    from ai_cursor import move_cursor, CursorMotionConfig

from core.bot_offsets import load_areas, apply_offset, get_bot_id, BOT_OFFSETS

# ============================================================
# AREAS CACHE
# ============================================================
_AREAS_CACHE = {}


def _get_areas(pack=None):
    key = (pack or "").replace("\\", "/").strip() or "__default__"
    if key not in _AREAS_CACHE:
        _AREAS_CACHE[key] = load_areas(pack if key != "__default__" else None)
    return _AREAS_CACHE[key]


def _rand_in_box(x1, y1, x2, y2, pad):
    pad = max(0, int(pad))

    left = x1 + pad
    top = y1 + pad
    right = x2 - pad - 1
    bottom = y2 - pad - 1

    if right < left:
        left, right = x1, max(x1, x2 - 1)
    if bottom < top:
        top, bottom = y1, max(y1, y2 - 1)

    return (
        random.randint(left, right),
        random.randint(top, bottom),
    )


def _screen_size():
    import ctypes
    return (
        int(ctypes.windll.user32.GetSystemMetrics(0)),
        int(ctypes.windll.user32.GetSystemMetrics(1)),
    )


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _safe_randint(a, b):
    a = int(a)
    b = int(b)
    if a > b:
        a, b = b, a
    return random.randint(a, b)


# ============================================================
# MOVE TO AREA
# ============================================================
def move_to_area(
    area_name,
    *,
    bot_id=None,
    pack=None,
    duration=0.55,
    fps=144,
    padding=3,
    jitter=0.18,
):
    bot_id = int(bot_id if bot_id is not None else get_bot_id(1))
    areas = _get_areas(pack)

    if area_name not in areas:
        sample = ", ".join(list(areas.keys())[:10])
        raise KeyError(f"Area '{area_name}' niet gevonden. Voorbeeld: {sample}")

    x1, y1, x2, y2 = apply_offset(areas[area_name], bot_id)
    x, y = _rand_in_box(x1, y1, x2, y2, padding)

    dur = max(0.14, float(duration) * random.uniform(1 - jitter, 1 + jitter))
    if random.random() < 0.28:
        dur *= random.uniform(1.2, 1.7)

    motion = CursorMotionConfig(duration=dur, fps=int(fps))
    move_cursor((x, y), config=motion)
    return (x, y)


def move_in_area(
    area_name,
    *,
    bot_id=1,
    pack=None,
    verbose=True,
    duration=0.55,
    fps=144,
    padding=0,
    jitter=0.18,
):
    areas = _get_areas(pack)

    area_key = str(area_name).lower()
    area_map = {k.lower(): k for k in areas}
    if area_key not in area_map:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden")
        return False

    true_key = area_map[area_key]
    x1, y1, x2, y2 = apply_offset(areas[true_key], int(bot_id))
    x, y = _rand_in_box(x1, y1, x2, y2, padding)

    dur = max(0.14, float(duration) * random.uniform(1 - jitter, 1 + jitter))
    if random.random() < 0.28:
        dur *= random.uniform(1.2, 1.7)

    if verbose:
        ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
        print(f"🖱️ {true_key} -> ({x},{y}) offset ({ox},{oy}) dur={dur:.2f}s fps={fps}")

    motion = CursorMotionConfig(duration=dur, fps=int(fps))
    move_cursor((x, y), config=motion)
    return True


def move_outside_area(
    area_name,
    *,
    bot_id=1,
    pack=None,
    verbose=True,
    duration=0.55,
    fps=144,
    padding=6,         # padding binnen area (voor de box)
    outside_margin=30, # hoe ver "buiten" minimaal
    jitter=0.18,
):
    areas = _get_areas(pack)

    area_key = str(area_name).lower()
    area_map = {k.lower(): k for k in areas}
    if area_key not in area_map:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden")
        return False

    true_key = area_map[area_key]
    x1, y1, x2, y2 = apply_offset(areas[true_key], int(bot_id))

    # nette box (met padding)
    pad = max(0, int(padding))
    left = x1 + pad
    top = y1 + pad
    right = x2 - pad - 1
    bottom = y2 - pad - 1

    # ✅ FIX: als padding de box "inverted"
    if right < left:
        left, right = x1, max(x1, x2 - 1)
    if bottom < top:
        top, bottom = y1, max(y1, y2 - 1)

    sw, sh = _screen_size()
    m = max(5, int(outside_margin))

    # clamp box naar scherm
    L = _clamp(left, 0, sw - 1)
    R = _clamp(right, 0, sw - 1)
    T = _clamp(top, 0, sh - 1)
    B = _clamp(bottom, 0, sh - 1)

    side = random.choice(("left", "right", "top", "bottom"))

    if side == "left":
        x = _safe_randint(0, _clamp(L - m, 0, sw - 1))
        y = _safe_randint(T, B)

    elif side == "right":
        x = _safe_randint(_clamp(R + m, 0, sw - 1), sw - 1)
        y = _safe_randint(T, B)

    elif side == "top":
        x = _safe_randint(L, R)
        y = _safe_randint(0, _clamp(T - m, 0, sh - 1))

    else:  # bottom
        x = _safe_randint(L, R)
        y = _safe_randint(_clamp(B + m, 0, sh - 1), sh - 1)

    dur = max(0.14, float(duration) * random.uniform(1 - jitter, 1 + jitter))
    if random.random() < 0.28:
        dur *= random.uniform(1.2, 1.7)

    if verbose:
        ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
        print(f"🖱️ OUTSIDE {true_key} -> ({x},{y}) side={side} offset ({ox},{oy}) dur={dur:.2f}s fps={fps}")

    motion = CursorMotionConfig(duration=dur, fps=int(fps))
    move_cursor((x, y), config=motion)
    return True


# ============================================================
# SELF TEST
# ============================================================
if __name__ == "__main__":
    print("\n🧪 move_to_area SELF TEST (Info_Area)\nNiet bewegen met je muis 🙂\n")
    import time
    time.sleep(2)

    pack = None
    areas = _get_areas(pack)

    if "Info_Area" not in areas:
        raise SystemExit("❌ Info_Area niet gevonden in areas")

    for bid in (1, 2, 3, 4):
        print(f"\n🤖 Bot {bid} -> Info_Area")
        move_in_area("Info_Area", bot_id=bid, pack=pack, verbose=True, padding=3)
        time.sleep(0.6)

    print("\n✅ klaar\n")
