from __future__ import annotations

import sys
import random
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageGrab

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pynput.mouse import Controller as _MouseController
except Exception:
    _MouseController = None


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
# IMPORTS (project)
# ============================================================
from core.ai_cursor import move_and_click
from config.areas import load_coords
from core.bot_offsets import apply_offset
from helpers.log import log
from helpers.trace import trace as _trace
from vision.colours import normalize_colour, compile_ranges_np


# ============================================================
# LOGGING HELPERS
# ============================================================
def _title(msg):
    log(True, f"\n{'=' * 52}\n{msg}\n{'=' * 52}")

def _table(rows, icon="🧾", title="Details"):
    if not rows:
        _title(f"{icon} {title}")
        log(True, "(leeg)")
        return
    left_w = max(len(str(k)) for k, _ in rows)
    _title(f"{icon} {title}")
    for k, v in rows:
        kk = str(k).strip().title()
        log(True, f"{kk:<{left_w}} | {v}")

def _done(verbose, trace, msg="click uitgevoerd"):
    log(verbose, f"✅ Done  {msg}", trace)


# ============================================================
# HSV RANGES
# ============================================================
COLOR_RANGES_NP = compile_ranges_np()

_EXTRA_RANGES = {
    "wit":   [((0, 0, 200), (179, 45, 255))],
    "zwart": [((0, 0, 0), (179, 255, 45))],
    "roze":  [((160, 60, 60), (179, 255, 255))],
}

for k, ranges in _EXTRA_RANGES.items():
    if k not in COLOR_RANGES_NP:
        COLOR_RANGES_NP[k] = [(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)) for lo, hi in ranges]


# ============================================================
# HELPERS
# ============================================================
def _area_bbox(area_name, bot_id):
    coords = list(load_coords(area_name))
    x1, y1, x2, y2 = apply_offset(coords, bot_id)
    return int(x1), int(y1), int(x2), int(y2)

def _colour_mask_in_bbox(kleur, bbox):
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    np_img = np.array(img)

    if np_img.shape[-1] == 4:
        np_img = np_img[:, :, :3]

    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)

    ranges = COLOR_RANGES_NP.get(kleur)
    if not ranges:
        return None

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else cv2.bitwise_or(mask, m)

    return mask

def _mask_pct(mask):
    return float((mask > 0).mean() * 100.0)

def _rand_from_mask(mask, x1, y1):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    i = random.randrange(len(xs))
    return int(xs[i]) + int(x1), int(ys[i]) + int(y1)

def _get_mouse_pos():
    if pyautogui is not None:
        p = pyautogui.position()
        return int(p.x), int(p.y)
    if _MouseController is not None:
        p = _MouseController().position
        return int(p[0]), int(p[1])
    return 0, 0

def _nearest_from_mask(mask, x1, y1, mouse_xy, k_nearest=200, weighted=True):
    ys, xs = np.where(mask > 0)
    n = len(xs)
    if n == 0:
        return None

    mx, my = mouse_xy
    gx = xs.astype(np.int32) + int(x1)
    gy = ys.astype(np.int32) + int(y1)

    dx = gx - int(mx)
    dy = gy - int(my)
    dist2 = dx * dx + dy * dy

    k = max(1, min(int(k_nearest), n))
    idxs = np.arange(n, dtype=np.int32) if k == n else np.argpartition(dist2, k - 1)[:k]

    if not weighted:
        j = int(random.choice(list(idxs)))
        return int(gx[j]), int(gy[j])

    d = dist2[idxs].astype(np.float64)
    w = 1.0 / (d + 1.0)
    pick = random.choices(list(idxs), weights=list(w), k=1)[0]
    j = int(pick)
    return int(gx[j]), int(gy[j])

def _filter_mask_by_min_component_area(mask, min_area):
    if not min_area or min_area <= 0:
        return mask, None

    num, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)

    keep = np.zeros(num, dtype=np.uint8)
    kept = 0
    for lab in range(1, num):
        area = stats[lab, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep[lab] = 1
            kept += 1

    filtered = (keep[labels] * 255).astype(np.uint8)
    return filtered, kept


# ============================================================
# CLICK COLOUR (robust + alias-safe + wait/retry)
# ============================================================
def click_colour(
    kleur=None,
    area_name=None,
    bot_id=1,

    button="left",
    speed_pct=100.0,

    mode="deep_random",          # 'mask_random' | 'deep_random' | 'center'
    threshold=0.005,             # alleen warning
    jitter_range=2,
    min_size=40,
    dilate_px=2,
    deep_erode_px=3,
    deep_tries=10,

    pick_strategy="random",      # 'random' | 'nearest'
    nearest_k=200,
    nearest_weighted=True,

    prefer_center=True,
    center_bias=0.18,

    timeout=0.0,                 # ✅ nieuw: wacht tot kleur verschijnt
    interval=0.25,               # ✅ nieuw: polling interval

    verbose=True,
    trace=False,
    debug=False,

    # legacy safe
    **_legacy,
):
    # ---------------------------
    # ALIASES (zodat alles blijft werken)
    # ---------------------------
    if kleur is None:
        kleur = _legacy.get("colour") or _legacy.get("color") or "paars"
    if area_name is None:
        area_name = _legacy.get("area") or _legacy.get("area_name") or "Bot_Area"

    if "min_px" in _legacy and (min_size == 40):
        min_size = _legacy["min_px"]
    if "min_size_px" in _legacy and (min_size == 40):
        min_size = _legacy["min_size_px"]

    if "erode_px" in _legacy and (deep_erode_px == 3):
        deep_erode_px = _legacy["erode_px"]

    kleur = normalize_colour(kleur)

    if kleur not in COLOR_RANGES_NP:
        if verbose:
            rows = [("Status", "Failed"), ("Reason", "Unknown colour"), ("Colour", kleur)]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="❌", title="Click Colour")
        return False

    # ---------------------------
    # WAIT LOOP (mask rebuild per poging)
    # ---------------------------
    t0 = time.time()
    deadline = t0 + float(timeout or 0.0)

    tries = 0
    while True:
        tries += 1

        bbox = _area_bbox(area_name, bot_id)
        x1, y1, x2, y2 = bbox

        mask = _colour_mask_in_bbox(kleur, bbox)
        if mask is None:
            if time.time() >= deadline:
                if verbose:
                    rows = [
                        ("Status", "Failed"),
                        ("Reason", "Mask build failed"),
                        ("Colour", kleur),
                        ("Area", area_name),
                        ("Bot", bot_id),
                    ]
                    if trace:
                        rows.append(("Caller", _trace(True)))
                    _table(rows, icon="❌", title="Click Colour")
                return False
            time.sleep(float(interval))
            continue

        pct = _mask_pct(mask)
        mask_pixels_pre = int((mask > 0).sum())

        # dilate
        if dilate_px and dilate_px > 0:
            k = int(dilate_px) * 2 + 1
            kernel = np.ones((k, k), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)

        mask_pixels_post = int((mask > 0).sum())

        # min_size filter
        mask, kept_components = _filter_mask_by_min_component_area(mask, int(min_size))
        mask_pixels_filtered = int((mask > 0).sum())

        # als er niks meer over is, eventueel wachten
        if mask_pixels_filtered <= 0:
            if time.time() >= deadline:
                if verbose:
                    rows = [
                        ("Status", "Failed"),
                        ("Reason", "No pixels after filtering"),
                        ("Colour", kleur.upper()),
                        ("Area", area_name),
                        ("Bot", bot_id),
                        ("Tries", tries),
                        ("Timeout", f"{timeout:.2f}s"),
                        ("Mask Coverage", f"{pct:.2f}%"),
                        ("Mask Pixels (pre)", f"{mask_pixels_pre:,}"),
                        ("Mask Pixels (post)", f"{mask_pixels_post:,}"),
                        ("Mask Pixels (filtered)", f"{mask_pixels_filtered:,}"),
                        ("Min Size", f"{min_size} px"),
                    ]
                    if kept_components is not None:
                        rows.append(("Kept Components", kept_components))
                    if trace:
                        rows.append(("Caller", _trace(True)))
                    _table(rows, icon="🚫", title="Click Colour")
                return False

            time.sleep(float(interval))
            continue

        # ---------------------------
        # PICK COORDS
        # ---------------------------
        mouse_xy = _get_mouse_pos()

        def _pick(mask_to_use):
            if (pick_strategy or "").lower().strip() == "nearest":
                return _nearest_from_mask(
                    mask_to_use,
                    x1, y1,
                    mouse_xy=mouse_xy,
                    k_nearest=nearest_k,
                    weighted=nearest_weighted,
                )
            return _rand_from_mask(mask_to_use, x1, y1)

        chosen = None

        if mode in ("mask_random", "deep_random"):
            if mode == "deep_random" and deep_erode_px and deep_erode_px > 0:
                kk = int(deep_erode_px) * 2 + 1
                kernel = np.ones((kk, kk), np.uint8)
                deep_mask = cv2.erode(mask, kernel, iterations=1)
            else:
                deep_mask = mask

            for _ in range(max(1, int(deep_tries))):
                chosen = _pick(deep_mask)
                if chosen is not None:
                    break

            if chosen is None:
                chosen = _pick(mask)

            if chosen is None:
                if time.time() >= deadline:
                    if verbose:
                        rows = [
                            ("Status", "Failed"),
                            ("Reason", "Pick failed"),
                            ("Mode", mode),
                            ("Colour", kleur.upper()),
                            ("Area", area_name),
                            ("Bot", bot_id),
                            ("Tries", tries),
                            ("Timeout", f"{timeout:.2f}s"),
                        ]
                        if trace:
                            rows.append(("Caller", _trace(True)))
                        _table(rows, icon="🚫", title="Click Colour")
                    return False

                time.sleep(float(interval))
                continue

            mx, my = chosen

            tx = int(mx) + random.randint(-int(jitter_range), int(jitter_range))
            ty = int(my) + random.randint(-int(jitter_range), int(jitter_range))

            move_and_click((tx, ty), button=button, speed_pct=speed_pct)

            if verbose and debug:
                rows = [
                    ("Status", "Ok (click)"),
                    ("Mode", mode),
                    ("Colour", kleur.upper()),
                    ("Area", area_name),
                    ("Bot", bot_id),
                    ("Bbox", f"({x1},{y1},{x2},{y2})"),
                    ("Mask Coverage", f"{pct:.2f}%"),
                    ("Min Size", f"{min_size} px"),
                    ("Chosen", f"({mx},{my})"),
                    ("Click", f"({tx},{ty})  button={button}  speed={speed_pct:.0f}%"),
                    ("Tries", tries),
                ]
                if pct < (threshold * 100.0):
                    rows.append(("Warning", f"Coverage low: {pct:.3f}%"))
                if (pick_strategy or "").lower().strip() == "nearest":
                    rows.append(("Pick", f"Nearest  k={nearest_k} weighted={nearest_weighted}"))
                    rows.append(("Mouse", f"({mouse_xy[0]},{mouse_xy[1]})"))
                if trace:
                    rows.append(("Caller", _trace(True)))
                _table(rows, icon="🧪", title="Click Colour")

            _done(verbose and debug, trace)
            return True

        # ---------------------------
        # CENTER MODE
        # ---------------------------
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = [c for c in contours if cv2.contourArea(c) >= int(min_size)]

        if not contours:
            if time.time() >= deadline:
                if verbose:
                    rows = [
                        ("Status", "Failed"),
                        ("Reason", "No contours"),
                        ("Mode", "center"),
                        ("Colour", kleur.upper()),
                        ("Area", area_name),
                        ("Bot", bot_id),
                        ("Tries", tries),
                    ]
                    if trace:
                        rows.append(("Caller", _trace(True)))
                    _table(rows, icon="🚫", title="Click Colour")
                return False

            time.sleep(float(interval))
            continue

        cx_area = (x1 + x2) // 2
        cy_area = (y1 + y2) // 2

        def _center_score(contour):
            M = cv2.moments(contour)
            if M["m00"] == 0:
                return 1e18
            cx0 = int(M["m10"] / M["m00"]) + x1
            cy0 = int(M["m01"] / M["m00"]) + y1
            dist2 = (cx0 - cx_area) ** 2 + (cy0 - cy_area) ** 2
            area0 = cv2.contourArea(contour)
            return dist2 - (float(center_bias) * float(area0))

        gekozen = min(contours, key=_center_score) if prefer_center else max(contours, key=cv2.contourArea)

        M = cv2.moments(gekozen)
        if M["m00"] == 0:
            if time.time() >= deadline:
                if verbose:
                    rows = [("Status", "Failed"), ("Reason", "Moments m00=0"), ("Mode", "center")]
                    if trace:
                        rows.append(("Caller", _trace(True)))
                    _table(rows, icon="⚠️", title="Click Colour")
                return False

            time.sleep(float(interval))
            continue

        cx = int(M["m10"] / M["m00"]) + x1
        cy = int(M["m01"] / M["m00"]) + y1

        tx = int(cx) + random.randint(-int(jitter_range), int(jitter_range))
        ty = int(cy) + random.randint(-int(jitter_range), int(jitter_range))

        move_and_click((tx, ty), button=button, speed_pct=speed_pct)

        if verbose and debug:
            rows = [
                ("Status", "Ok (click)"),
                ("Mode", "center"),
                ("Colour", kleur.upper()),
                ("Area", area_name),
                ("Bot", bot_id),
                ("Centroid", f"({cx},{cy})"),
                ("Click", f"({tx},{ty})  button={button}  speed={speed_pct:.0f}%"),
                ("Tries", tries),
            ]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="🧲", title="Click Colour")

        _done(verbose and debug, trace)
        return True


# ============================================================
# RUN (test)
# ============================================================
if __name__ == "__main__":
    ok = click_colour(
        "cyaan",
        "Bot_Area",
        bot_id=1,
        mode="deep_random",
        deep_erode_px=3,
        jitter_range=3,
        min_size=50,
        dilate_px=0,
        timeout=2.0,
        interval=0.25,
        verbose=True,
        trace=True,
        debug=True,
    )
    print("OK ✅" if ok else "FAIL ❌")
