from __future__ import annotations
import sys
from pathlib import Path
import random
import ctypes

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from core.ai_mouse import human_move_to, human_click
except Exception:
    from ai_mouse import human_move_to, human_click

from core.bot_offsets import load_areas, apply_offset, get_bot_id, BOT_OFFSETS

_AREAS = load_areas()


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
    return random.randint(left, right), random.randint(top, bottom)


def move_to_area(area_name, *, bot_id=None, padding=3, click=False):
    bot_id = int(get_bot_id(1) if bot_id is None else bot_id)

    if area_name not in _AREAS:
        sample = ", ".join(list(_AREAS.keys())[:10])
        raise KeyError(f"Area '{area_name}' niet gevonden. Voorbeeld: {sample}")

    x1, y1, x2, y2 = apply_offset(_AREAS[area_name], bot_id)
    x, y = _rand_in_box(x1, y1, x2, y2, padding)

    human_move_to(x, y)

    if click:
        human_click()

    return x, y


def move_in_area(area_name, *, bot_id=1, verbose=True, padding=3, click=False):
    key = area_name.lower()
    area_map = {k.lower(): k for k in _AREAS}

    if key not in area_map:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden")
        return False

    true_key = area_map[key]

    x1, y1, x2, y2 = apply_offset(_AREAS[true_key], int(bot_id))
    x, y = _rand_in_box(x1, y1, x2, y2, padding)

    if verbose:
        ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
        print(f"🖱️ AI {true_key} -> ({x},{y}) offset ({ox},{oy})")

    human_move_to(x, y)

    if click:
        human_click()

    return True

def move_outside_area(area_name, *, bot_id=1, padding=6, click=False, verbose=False):
    bot_id = int(get_bot_id(1) if bot_id is None else bot_id)

    key = str(area_name).lower()
    area_map = {k.lower(): k for k in _AREAS}

    if key not in area_map:
        if verbose:
            print(f"❌ Area '{area_name}' niet gevonden (move_outside_area)")
        return False

    true_key = area_map[key]
    x1, y1, x2, y2 = apply_offset(_AREAS[true_key], bot_id)

    sw = int(ctypes.windll.user32.GetSystemMetrics(0))
    sh = int(ctypes.windll.user32.GetSystemMetrics(1))

    pad = max(0, int(padding))

    # Kandidaten: 4 stroken rondom het gebied (buiten de box)
    candidates = []

    # links
    if x1 - pad > 0:
        candidates.append((0, 0, max(1, x1 - pad), sh))

    # rechts
    if x2 + pad < sw:
        candidates.append((min(sw - 1, x2 + pad), 0, sw, sh))

    # boven
    if y1 - pad > 0:
        candidates.append((0, 0, sw, max(1, y1 - pad)))

    # onder
    if y2 + pad < sh:
        candidates.append((0, min(sh - 1, y2 + pad), sw, sh))

    if not candidates:
        # fallback: als area vrijwel fullscreen is
        return move_to_area(true_key, bot_id=bot_id, padding=3, click=click)

    rx1, ry1, rx2, ry2 = random.choice(candidates)

    # veilige clamp
    rx1 = max(0, min(sw - 1, int(rx1)))
    ry1 = max(0, min(sh - 1, int(ry1)))
    rx2 = max(rx1 + 1, min(sw, int(rx2)))
    ry2 = max(ry1 + 1, min(sh, int(ry2)))

    x = random.randint(rx1, rx2 - 1)
    y = random.randint(ry1, ry2 - 1)

    if verbose:
        print(f"🧭 Outside {true_key} -> ({x},{y})")

    human_move_to(x, y)

    if click:
        human_click()

    return True