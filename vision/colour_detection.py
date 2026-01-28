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
import cv2
import numpy as np
import pyautogui

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
def _build_mask(hsv, colour):
    ranges = COLOR_RANGES_NP.get(colour)
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

def _line(colour, area, bot_id, percent, threshold, biggest, min_size, ok):
    icon = "🟢" if ok else "🔴"
    kleur_ansi = ANSI.get(colour, "")
    reset = ANSI["reset"]
    area_ansi = ANSI["area"]

    pct_txt = _fmt_pct(percent)
    pct_req = f"Min {_fmt_pct(threshold)}%" if threshold is not None else "Min n/a"

    if min_size and min_size > 0:
        blob_txt = f" | Blob {biggest}px (min {min_size})"
    else:
        blob_txt = f" | Blob {biggest}px"

    return (
        f"{icon} "
        f"{kleur_ansi}{colour.capitalize()}{reset} in "
        f"{area_ansi}{area}{reset} | "
        f"{pct_txt}% | {pct_req} | Bot {bot_id}{blob_txt}"
    )

def _debug_line(colour, area, bot_id, percent, biggest, threshold, min_size):
    reset = ANSI["reset"]
    kleur_ansi = ANSI.get(colour, "")
    area_ansi = ANSI["area"]
    dim = ANSI["dim"]

    thr_txt = "n/a" if threshold is None else f"{_fmt_pct(threshold)}%"
    ms_txt = "n/a" if not min_size or min_size <= 0 else str(int(min_size))

    return (
        f"{dim}🧪 Debug{reset} | "
        f"{kleur_ansi}{colour}{reset} | "
        f"{area_ansi}{area}{reset} | "
        f"Bot {bot_id} | "
        f"pct={_fmt_pct(percent)}% | blob={int(biggest)}px | "
        f"thr={thr_txt} | min_size={ms_txt}"
    )

def _make_stats(colour, percent, biggest, threshold, ok):
    return {
        "colour": colour,
        "percent": float(percent),
        "biggest": int(biggest),
        "threshold": None if threshold is None else float(threshold),
        "ok": bool(ok),
    }

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
    return_stats=False,    # ✅ nieuw
):
    """
    verbose=True:
      fail  -> altijd loggen
      ok    -> alleen loggen als debug=True

    timeout=0  -> 1 check
    timeout>0  -> wachten tot ok of timeout

    return_stats=True -> return (ok, stats)
    """

    colour = normalize_colour(colour)
    t_end = time.time() + timeout if timeout and timeout > 0 else None

    while True:
        rgb = grab_area_rgb(area, bot_id=bot_id, areas=areas)

        if blur and blur >= 3:
            b = int(blur)
            if b % 2 == 0:
                b += 1
            rgb = cv2.GaussianBlur(rgb, (b, b), 0)

        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        mask = _build_mask(hsv, colour)

        if mask is None:
            log(verbose, f"❌ onbekende kleur: {colour}", trace)
            if return_stats:
                return False, _make_stats(colour, 0.0, 0, None, False)
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

        # ✅ debug: altijd laten zien hoeveel % en px (handig bij ok én fail)
        if verbose and debug:
            log(True, _debug_line(colour, area, bot_id, percent, biggest, threshold, min_size), trace)

        if ok:
            if verbose and debug:
                log(True, _line(colour, area, bot_id, percent, threshold, biggest, min_size, True), trace)

            if return_stats:
                return True, _make_stats(colour, percent, biggest, threshold, True)
            return (True, biggest) if return_blob else True

        if not timeout or timeout <= 0 or time.time() >= t_end:
            log(verbose, _line(colour, area, bot_id, percent, threshold, biggest, min_size, False), trace)

            if return_stats:
                return False, _make_stats(colour, percent, biggest, threshold, False)
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
    Scant 1 area en geeft per kleur:
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
        mask = _build_mask(hsv, c)
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

        header = f"{ANSI['dim']}{'Kleur':<10} {'%':>8} {'Blob(px)':>10}{reset}"
        log(True, header, trace)
        log(True, f"{ANSI['dim']}{'-'*30}{reset}", trace)

        for r in results:
            c = r["colour"]
            pct = _fmt_pct(r["percent"])
            blob = r["biggest"]
            kleur_ansi = ANSI.get(c, "")
            line = f"{kleur_ansi}{c:<10}{reset} {pct:>8}% {blob:>10}"
            log(True, line, trace)

    return results

# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    # Voorbeeld 1: debug prints (laat % en blob zien)
    ok = detect_colour(
        "groen",
        "Skilling_Area",
        percentage=None,
        bot_id=1,
        verbose=True,
        min_size=75,
        debug=True,
        trace=True,
    )
    print("Found!" if ok else "Not found")

    # Voorbeeld 2: stats terug zonder spam prints
    ok2, stats = detect_colour(
        "groen",
        "Skilling_Area",
        bot_id=1,
        verbose=False,
        min_size=75,
        return_stats=True,
    )
    print("OK:", ok2, "STATS:", stats)
