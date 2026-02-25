# ============================================================
# BOOTSTRAP
# ============================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS
# ============================================================
import json
import time
import re
import cv2
import numpy as np
import pyautogui
from send_screenshot import send_area_shot
from core.bot_offsets import apply_offset
from helpers.log import log
from vision.colours import normalize_colour, compile_ranges_np

# ============================================================
# ANSI KLEUREN (console only)
# ============================================================
ANSI = {
    "groen": "\033[92m",
    "rood": "\033[91m",
    "geel": "\033[93m",
    "blauw": "\033[94m",
    "cyaan": "\033[96m",
    "paars": "\033[95m",
    "oranje": "\033[38;5;208m",
    "area": "\033[95m",
    "reset": "\033[0m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}

# ============================================================
# CONFIG
# ============================================================
AREAS_FILE = ROOT / "config" / "areas.json"
FULLSCREEN = {"fullscreen", "screen", "full", "full_screen", "full screen"}

# ============================================================
# PRECOMPILE HSV RANGES (centrale bron)
# ============================================================
COLOR_RANGES_NP = compile_ranges_np()

# ============================================================
# MINI CACHE
# ============================================================
_GRAB_CACHE = {}
CACHE_MS = 0

def _now_ms():
    return int(time.time() * 1000)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ============================================================
# HEX / HSV HELPERS
# ============================================================
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

def hex_to_rgb(hex_code: str):
    m = _HEX_RE.match(hex_code.strip())
    if not m:
        raise ValueError(f"Ongeldige HEX kleur: {hex_code}")
    h = m.group(1)
    if len(h) == 3:
        h = "".join([c * 2 for c in h])  # #0FF -> #00FFFF
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (r, g, b)

def rgb_to_hsv_pixel(rgb):
    arr = np.uint8([[list(rgb)]])
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)[0, 0]
    return (int(hsv[0]), int(hsv[1]), int(hsv[2]))

def build_hsv_ranges_from_pixel(h, s, v, tol_h=8, tol_s=60, tol_v=60):
    """
    Snapt HSV ranges rondom 1 pixel.
    Hue wrap fix: als door 0/179 => 2 ranges.
    Output: list[((lo),(hi)), ...] met ints.
    """
    lo_h = h - tol_h
    hi_h = h + tol_h

    lo_s = clamp(s - tol_s, 0, 255)
    hi_s = clamp(s + tol_s, 0, 255)
    lo_v = clamp(v - tol_v, 0, 255)
    hi_v = clamp(v + tol_v, 0, 255)

    if lo_h < 0:
        r1 = ((0, lo_s, lo_v), (clamp(hi_h, 0, 179), hi_s, hi_v))
        r2 = ((clamp(179 + lo_h, 0, 179), lo_s, lo_v), (179, hi_s, hi_v))
        return [r1, r2]

    if hi_h > 179:
        r1 = ((clamp(lo_h, 0, 179), lo_s, lo_v), (179, hi_s, hi_v))
        r2 = ((0, lo_s, lo_v), (clamp(hi_h - 179, 0, 179), hi_s, hi_v))
        return [r1, r2]

    return [((clamp(lo_h, 0, 179), lo_s, lo_v), (clamp(hi_h, 0, 179), hi_s, hi_v))]

def _ranges_to_np(ranges):
    out = []
    for lo, hi in ranges:
        out.append((np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)))
    return out

def _is_hex_string(x):
    if not isinstance(x, str):
        return False
    return _HEX_RE.match(x.strip()) is not None

def _resolve_colour_input(colour, *, tol_h=8, tol_s=60, tol_v=60, colour_space="auto"):
    """
    Ondersteunt:
      1) kleurnaam in vision/colours.py (bijv 'cyaan')
      2) HEX string '#00FFFF' of '0FF'
      3) HSV tuple (H 0..179, S 0..255, V 0..255) bijv (90,255,255)
      4) RGB tuple (R 0..255, G 0..255, B 0..255) (alleen als colour_space='rgb' of auto detect)
    Return:
      (label, ranges_np, meta)
      label = string voor logging
      ranges_np = list[(lo_np, hi_np)]
      meta = dict met debug info
    """
    meta = {"input": colour, "type": None}

    # 1) HEX
    if _is_hex_string(colour):
        rgb = hex_to_rgb(colour)
        hsv = rgb_to_hsv_pixel(rgb)
        ranges = build_hsv_ranges_from_pixel(hsv[0], hsv[1], hsv[2], tol_h, tol_s, tol_v)
        meta.update({"type": "hex", "rgb": rgb, "hsv_pixel": hsv, "ranges": ranges})
        return f"hex({colour.strip()})", _ranges_to_np(ranges), meta

    # 2) tuple/list (HSV of RGB)
    if isinstance(colour, (tuple, list)) and len(colour) == 3:
        a, b, c = [int(x) for x in colour]

        # force
        if str(colour_space).lower() == "hsv":
            hsv = (clamp(a, 0, 179), clamp(b, 0, 255), clamp(c, 0, 255))
            ranges = build_hsv_ranges_from_pixel(hsv[0], hsv[1], hsv[2], tol_h, tol_s, tol_v)
            meta.update({"type": "hsv", "hsv_pixel": hsv, "ranges": ranges})
            return f"hsv{hsv}", _ranges_to_np(ranges), meta

        if str(colour_space).lower() == "rgb":
            rgb = (clamp(a, 0, 255), clamp(b, 0, 255), clamp(c, 0, 255))
            hsv = rgb_to_hsv_pixel(rgb)
            ranges = build_hsv_ranges_from_pixel(hsv[0], hsv[1], hsv[2], tol_h, tol_s, tol_v)
            meta.update({"type": "rgb", "rgb": rgb, "hsv_pixel": hsv, "ranges": ranges})
            return f"rgb{rgb}", _ranges_to_np(ranges), meta

        # auto:
        # als eerste <= 179 dan nemen we aan HSV (jouw use-case: (90,255,255))
        if 0 <= a <= 179 and 0 <= b <= 255 and 0 <= c <= 255:
            hsv = (a, b, c)
            ranges = build_hsv_ranges_from_pixel(hsv[0], hsv[1], hsv[2], tol_h, tol_s, tol_v)
            meta.update({"type": "hsv", "hsv_pixel": hsv, "ranges": ranges})
            return f"hsv{hsv}", _ranges_to_np(ranges), meta

        # anders RGB
        rgb = (clamp(a, 0, 255), clamp(b, 0, 255), clamp(c, 0, 255))
        hsv = rgb_to_hsv_pixel(rgb)
        ranges = build_hsv_ranges_from_pixel(hsv[0], hsv[1], hsv[2], tol_h, tol_s, tol_v)
        meta.update({"type": "rgb", "rgb": rgb, "hsv_pixel": hsv, "ranges": ranges})
        return f"rgb{rgb}", _ranges_to_np(ranges), meta

    # 3) kleurnaam in dict
    colour_name = normalize_colour(colour)
    ranges = COLOR_RANGES_NP.get(colour_name)
    if ranges:
        meta.update({"type": "name", "name": colour_name})
        return colour_name, ranges, meta

    meta.update({"type": "unknown"})
    return normalize_colour(colour), None, meta

# ============================================================
# AREAS
# ============================================================
def load_areas():
    if not AREAS_FILE.exists():
        return {}

    try:
        data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}

    out = {}
    for name, v in data.items():
        if isinstance(v, dict) and "coords" in v:
            out[name] = v["coords"]
        elif isinstance(v, list):
            out[name] = v
    return out

# ============================================================
# SCREEN GRAB
# ============================================================
def grab_area_rgb(area, bot_id=1, areas=None):
    if areas is None:
        areas = load_areas()

    key = (str(area).lower(), int(bot_id))
    if CACHE_MS > 0 and key in _GRAB_CACHE:
        ts, img = _GRAB_CACHE[key]
        if _now_ms() - ts <= CACHE_MS:
            return img.copy()

    if str(area).lower() in FULLSCREEN:
        img = np.array(pyautogui.screenshot())
    else:
        for name, coords in areas.items():
            if name.lower() == str(area).lower():
                x1, y1, x2, y2 = apply_offset(coords, bot_id)
                img = np.array(pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1)))
                break
        else:
            raise Exception(f"Area niet gevonden: {area}")

    if img.shape[-1] == 4:
        img = img[:, :, :3]

    if CACHE_MS > 0:
        _GRAB_CACHE[key] = (_now_ms(), img)

    return img

# ============================================================
# MASK HELPERS
# ============================================================
def _build_mask(hsv, ranges):
    """ranges = list[(lo_np, hi_np)]"""
    if not ranges:
        return None

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    return mask

def _largest_blob_area(mask_u8):
    bin_u8 = (mask_u8 > 0).astype(np.uint8)
    num, _, stats, _ = cv2.connectedComponentsWithStats(bin_u8, connectivity=8)
    if num <= 1:
        return 0
    return int(stats[1:, cv2.CC_STAT_AREA].max())

def _fmt_pct(x):
    return f"{x:.2f}".replace(".", ",")

def _normalize_threshold(p):
    if p <= 1.0:
        return p * 100.0
    return p

def _line(label, area, bot_id, percent, threshold, biggest, min_size, ok):
    icon = "🟢" if ok else "🔴"
    # als label een bekende kleurnaam is, pak ANSI, anders geen
    kleur_ansi = ANSI.get(label, "")
    reset = ANSI["reset"]
    area_ansi = ANSI["area"]

    pct_txt = _fmt_pct(percent)
    pct_req = f"Min {_fmt_pct(threshold)}%" if threshold is not None else "Min n/a"

    if min_size and min_size > 0:
        blob_txt = f" | Blob {biggest}px (min {min_size})"
    else:
        blob_txt = f" | Blob {biggest}px"

    shown = label if not isinstance(label, str) else label
    return (
        f"{icon} "
        f"{kleur_ansi}{shown}{reset} in "
        f"{area_ansi}{area}{reset} | "
        f"{pct_txt}% | {pct_req} | Bot {bot_id}{blob_txt}"
    )

def _debug_line(label, area, bot_id, percent, biggest, threshold, min_size, meta=None):
    reset = ANSI["reset"]
    kleur_ansi = ANSI.get(label, "")
    area_ansi = ANSI["area"]
    dim = ANSI["dim"]

    thr_txt = "n/a" if threshold is None else f"{_fmt_pct(threshold)}%"
    ms_txt = "n/a" if not min_size or min_size <= 0 else str(int(min_size))

    extra = ""
    if meta and isinstance(meta, dict):
        if meta.get("type") in {"hex", "hsv", "rgb"}:
            extra = f" | src={meta.get('type')} hsv={meta.get('hsv_pixel')}"

    return (
        f"{dim}🧪 Debug{reset} | "
        f"{kleur_ansi}{label}{reset} | "
        f"{area_ansi}{area}{reset} | "
        f"Bot {bot_id} | "
        f"pct={_fmt_pct(percent)}% | blob={int(biggest)}px | "
        f"thr={thr_txt} | min_size={ms_txt}{extra}"
    )

def _make_stats(label, percent, biggest, threshold, ok, meta=None):
    out = {
        "label": label,
        "percent": float(percent),
        "biggest": int(biggest),
        "threshold": None if threshold is None else float(threshold),
        "ok": bool(ok),
    }
    if meta:
        out["meta"] = meta
    return out

# ============================================================
# CORE
# ============================================================
def detect_colour(
    colour,
    area,
    percentage=None,
    bot_id=1,
    verbose=False,
    blur=3,
    areas=None,
    min_size=0,
    timeout=0,
    interval=0.2,
    trace=False,
    debug=False,
    return_blob=False,
    return_stats=False,
    # 🆕 dynamic inputs
    tol_h=8,
    tol_s=60,
    tol_v=60,
    colour_space="auto",   # auto | hsv | rgb
):
    """
    Ondersteunt nu:
      detect_colour("cyaan", "Bot_Area")
      detect_colour("#00FFFF", "Bot_Area", tol_h=10, tol_s=80, tol_v=80)
      detect_colour((90,255,255), "Bot_Area")          # HSV pixel (OpenCV)
      detect_colour((0,255,255), "Bot_Area")           # HSV pixel (OpenCV)
      detect_colour((0,255,255), "Bot_Area", colour_space="hsv")
      detect_colour((0,255,255), "Bot_Area", colour_space="rgb")  # force RGB
    """

    label, ranges, meta = _resolve_colour_input(
        colour,
        tol_h=int(tol_h),
        tol_s=int(tol_s),
        tol_v=int(tol_v),
        colour_space=colour_space,
    )

    t_end = time.time() + timeout if timeout and timeout > 0 else None

    while True:
        rgb = grab_area_rgb(area, bot_id=bot_id, areas=areas)

        if blur and blur >= 3:
            b = int(blur)
            if b % 2 == 0:
                b += 1
            rgb = cv2.GaussianBlur(rgb, (b, b), 0)

        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        mask = _build_mask(hsv, ranges)

        if mask is None:
            log(verbose, f"❌ onbekende kleur input: {colour}", trace)
            if return_stats:
                return False, _make_stats(label, 0.0, 0, None, False, meta)
            return (False, 0) if return_blob else False

        percent = (mask > 0).mean() * 100.0
        biggest = _largest_blob_area(mask)

        if percentage is not None and percentage > 0:
            threshold = _normalize_threshold(percentage)
            ok = percent >= threshold
        else:
            threshold = None
            ok = percent > 0.0

        if min_size and min_size > 0:
            ok = ok and biggest >= min_size

        if verbose and debug:
            log(True, _debug_line(label, area, bot_id, percent, biggest, threshold, min_size, meta), trace)

        if ok:
            if verbose and debug:
                log(True, _line(label, area, bot_id, percent, threshold, biggest, min_size, True), trace)

            if return_stats:
                return True, _make_stats(label, percent, biggest, threshold, True, meta)
            return (True, biggest) if return_blob else True

        if not timeout or timeout <= 0 or time.time() >= t_end:
            log(verbose, _line(label, area, bot_id, percent, threshold, biggest, min_size, False), trace)

            if return_stats:
                return False, _make_stats(label, percent, biggest, threshold, False, meta)
            return (False, biggest) if return_blob else False

        time.sleep(interval)

# ============================================================
# MULTI COLOUR SCAN (handig voor debug)
# ============================================================
def detect_colours(
    area,
    bot_id=1,
    colours=None,
    verbose=True,
    blur=3,
    areas=None,
    min_size=0,
    top_n=None,
    sort_by="percent",
    trace=False,
):
    """
    Scant 1 area en geeft per kleur (alleen uit vision/colours.py dict):
      percent: hoeveel % van pixels matcht die kleur
      biggest: grootste blob (px)

    min_size > 0:
      laat alleen kleuren zien waarvan biggest >= min_size
    """

    if colours is None:
        colours = list(COLOR_RANGES_NP.keys())

    norm = []
    for c in colours:
        c2 = normalize_colour(c)
        if c2 in COLOR_RANGES_NP:
            norm.append(c2)

    if not norm:
        log(verbose, "❌ detect_colours: geen geldige kleuren meegegeven", trace)
        return []

    rgb = grab_area_rgb(area, bot_id=bot_id, areas=areas)

    if blur and blur >= 3:
        b = int(blur)
        if b % 2 == 0:
            b += 1
        rgb = cv2.GaussianBlur(rgb, (b, b), 0)

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    results = []
    for c in norm:
        mask = _build_mask(hsv, COLOR_RANGES_NP.get(c))
        if mask is None:
            continue

        percent = (mask > 0).mean() * 100.0
        biggest = _largest_blob_area(mask)

        if min_size and min_size > 0 and biggest < min_size:
            continue

        results.append({"colour": c, "percent": float(percent), "biggest": int(biggest)})

    if sort_by == "blob":
        results.sort(key=lambda r: (r["biggest"], r["percent"]), reverse=True)
    else:
        results.sort(key=lambda r: (r["percent"], r["biggest"]), reverse=True)

    if top_n is not None:
        results = results[: int(top_n)]

    if verbose:
        area_ansi = ANSI["area"]
        reset = ANSI["reset"]
        log(True, f"\n{ANSI['bold']}🎨 Colour scan{reset} in {area_ansi}{area}{reset} | Bot {bot_id}", trace)

        if not results:
            log(True, f"{ANSI['dim']}(niets gevonden boven filter/min_size){reset}", trace)
            return results

        header = f"{ANSI['dim']}{'Kleur':<16} {'%':>8} {'Blob(px)':>10}{reset}"
        log(True, header, trace)
        log(True, f"{ANSI['dim']}{'-'*38}{reset}", trace)

        for r in results:
            c = r["colour"]
            pct = _fmt_pct(r["percent"])
            blob = r["biggest"]
            kleur_ansi = ANSI.get(c, "")
            line = f"{kleur_ansi}{c:<16}{reset} {pct:>8}% {blob:>10}"
            log(True, line, trace)

    return results

# ============================================================
# QUICK TEST
# ============================================================
if __name__ == "__main__":

    if detect_colour("#00FFFF", "Bot_Area", bot_id=1):
        print("Other players around!")
        send_area_shot("Chat_Area", "⚠️ Other players nearby 👀", bot_id=1)
