from __future__ import annotations

import sys
import random
import inspect
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any

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
from config.areas import load_coords
from core.bot_offsets import apply_offset
from core.ansi import ANSI
from vision.colours import normalize_colour, compile_ranges_np


Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]


# ============================================================
# LOCAL LOG + TRACE
# ============================================================
def log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)

def trace(_skip: bool = True) -> str:
    stack = inspect.stack()
    idx = 2 if _skip and len(stack) > 2 else 1
    fr = stack[idx]
    return f"{Path(fr.filename).name}:{fr.lineno} in {fr.function}()"


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
# PRETTY PRINT HELPERS
# ============================================================
def _banner(title: str) -> None:
    line = "═" * 60
    log(True, f"\n{ANSI.subtle(line)}")
    log(True, f"{ANSI.BOLD}{title}{ANSI.RESET}")
    log(True, f"{ANSI.subtle(line)}")

def _fmt_value(v: Any) -> str:
    if isinstance(v, bool):
        return ANSI.tf(v)
    if v is None:
        return ANSI.subtle("None")
    if isinstance(v, (tuple, list)) and len(v) == 2 and all(isinstance(x, int) for x in v):
        return ANSI.info(str(v))
    if isinstance(v, str):
        return v
    return str(v)

def _table(rows: List[Tuple[str, Any]], icon: str = "🧾", title: str = "Details") -> None:
    _banner(f"{icon} {title}")
    if not rows:
        log(True, ANSI.subtle("(leeg)"))
        return

    w = max(len(str(k)) for k, _ in rows)
    for k, v in rows:
        key = ANSI.subtle(f"{str(k):<{w}}")
        val = _fmt_value(v)
        log(True, f"{key}  {ANSI.subtle('│')}  {val}")


# ============================================================
# HELPERS
# ============================================================
def _area_bbox(area_name: str, bot_id: int) -> BBox:
    coords = list(load_coords(area_name))
    x1, y1, x2, y2 = apply_offset(coords, bot_id)
    return int(x1), int(y1), int(x2), int(y2)

def _get_mouse_pos() -> Point:
    if pyautogui is not None:
        p = pyautogui.position()
        return int(p.x), int(p.y)
    if _MouseController is not None:
        p = _MouseController().position
        return int(p[0]), int(p[1])
    return 0, 0

def _kernel(px: int) -> Optional[np.ndarray]:
    if not px or px <= 0:
        return None
    k = int(px) * 2 + 1
    return np.ones((k, k), np.uint8)

def _build_mask(colour: str, bbox: BBox) -> Optional[np.ndarray]:
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    np_img = np.array(img)

    if np_img.shape[-1] == 4:
        np_img = np_img[:, :, :3]

    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)

    ranges = COLOR_RANGES_NP.get(colour)
    if not ranges:
        return None

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else cv2.bitwise_or(mask, m)

    return mask

def _apply_padding(mask: np.ndarray, padding: int) -> np.ndarray:
    k = _kernel(int(padding))
    if k is None:
        return mask
    return cv2.erode(mask, k, iterations=1)

def _mask_pct(mask: np.ndarray) -> float:
    return float((mask > 0).mean() * 100.0)

def _pick_random(mask: np.ndarray, x1: int, y1: int) -> Optional[Point]:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    i = random.randrange(len(xs))
    return int(xs[i]) + x1, int(ys[i]) + y1

def _pick_nearest_to_mouse(mask: np.ndarray, x1: int, y1: int, mouse_xy: Point, weighted: bool) -> Optional[Point]:
    ys, xs = np.where(mask > 0)
    n = len(xs)
    if n == 0:
        return None

    mx, my = mouse_xy
    gx = xs.astype(np.int32) + x1
    gy = ys.astype(np.int32) + y1

    dx = gx - mx
    dy = gy - my
    dist2 = (dx * dx + dy * dy).astype(np.float64)

    if not weighted:
        j = int(np.argmin(dist2))
        return int(gx[j]), int(gy[j])

    w = 1.0 / (dist2 + 1.0)
    j = int(random.choices(range(n), weights=w.tolist(), k=1)[0])
    return int(gx[j]), int(gy[j])


# ============================================================
# PUBLIC API (jouw naming intact)
# ============================================================
def detect_colour(
    kleur=None,
    area_name=None,
    bot_id: int = 1,

    padding: int = 3,
    nearest_mouse: bool = True,
    nearest_weighted: bool = True,

    debug: bool = False,
    trace_on: bool = False,

    **_legacy,
) -> Tuple[bool, Optional[Point], Dict[str, object]]:
    if kleur is None:
        kleur = _legacy.get("colour") or _legacy.get("color") or "paars"
    if area_name is None:
        area_name = _legacy.get("area") or _legacy.get("area_name") or "Bot_Area"

    kleur = normalize_colour(str(kleur))

    info: Dict[str, object] = {
        "kleur": kleur,
        "area_name": area_name,
        "bot_id": int(bot_id),
        "padding": int(padding),
        "nearest_mouse": bool(nearest_mouse),
        "nearest_weighted": bool(nearest_weighted),
    }

    if kleur not in COLOR_RANGES_NP:
        info["reason"] = "Unknown colour"
        if debug:
            rows = [
                ("Status", ANSI.fail("Failed")),
                ("Reason", info["reason"]),
                ("Kleur", ANSI.info(kleur)),
            ]
            if trace_on:
                rows.append(("Caller", trace(True)))
            _table(rows, icon="❌", title="Detect Colour")
        return False, None, info

    bbox = _area_bbox(area_name, bot_id)
    x1, y1, x2, y2 = bbox
    info["bbox"] = bbox

    mask0 = _build_mask(kleur, bbox)
    if mask0 is None:
        info["reason"] = "Mask build failed"
        if debug:
            rows = [
                ("Status", ANSI.fail("Failed")),
                ("Reason", info["reason"]),
                ("Kleur", ANSI.info(kleur.upper())),
                ("Area", ANSI.area(area_name)),
                ("Bot", bot_id),
            ]
            if trace_on:
                rows.append(("Caller", trace(True)))
            _table(rows, icon="🚫", title="Detect Colour")
        return False, None, info

    info["mask_pct_pre"] = f"{_mask_pct(mask0):.2f}%"
    info["pixels_pre"] = int((mask0 > 0).sum())

    mask = _apply_padding(mask0, int(padding))
    info["pixels_after_padding"] = int((mask > 0).sum())

    if info["pixels_after_padding"] <= 0:
        info["reason"] = "No pixels after padding (padding too high?)"
        if debug:
            rows = [
                ("Status", ANSI.fail("Failed")),
                ("Reason", info["reason"]),
                ("Kleur", ANSI.info(kleur.upper())),
                ("Area", ANSI.area(area_name)),
                ("Bot", bot_id),
                ("Padding", padding),
                ("Pixels pre", f"{info['pixels_pre']:,}"),
                ("Pixels after", f"{info['pixels_after_padding']:,}"),
            ]
            if trace_on:
                rows.append(("Caller", trace(True)))
            _table(rows, icon="🚫", title="Detect Colour")
        return False, None, info

    mouse_xy = _get_mouse_pos()
    info["mouse_xy"] = mouse_xy

    if nearest_mouse:
        pt = _pick_nearest_to_mouse(mask, x1, y1, mouse_xy, weighted=bool(nearest_weighted))
    else:
        pt = _pick_random(mask, x1, y1)

    if pt is None:
        info["reason"] = "Pick failed"
        if debug:
            rows = [
                ("Status", ANSI.fail("Failed")),
                ("Reason", info["reason"]),
                ("Kleur", ANSI.info(kleur.upper())),
                ("Area", ANSI.area(area_name)),
                ("Bot", bot_id),
            ]
            if trace_on:
                rows.append(("Caller", trace(True)))
            _table(rows, icon="🚫", title="Detect Colour")
        return False, None, info

    info["point"] = pt

    if debug:
        rows = [
            ("Status", ANSI.ok("Ok")),
            ("Kleur", ANSI.info(kleur.upper())),
            ("Area", ANSI.area(area_name)),
            ("Bot", bot_id),
            ("Padding", padding),
            ("Nearest Mouse", nearest_mouse),
            ("Nearest Weighted", nearest_weighted),
            ("Mouse", mouse_xy),
            ("Point", pt),
            ("Mask % pre", info["mask_pct_pre"]),
            ("Pixels pre", f"{info['pixels_pre']:,}"),
            ("Pixels after", f"{info['pixels_after_padding']:,}"),
        ]
        if trace_on:
            rows.append(("Caller", trace(True)))
        _table(rows, icon="🧪", title="Detect Colour")

    return True, pt, info


def click_colour(
    kleur=None,
    area_name=None,
    bot_id: int = 1,

    padding: int = 3,
    nearest_mouse: bool = True,
    nearest_weighted: bool = True,

    debug: bool = False,
    trace_on: bool = False,

    **_legacy,
) -> Tuple[bool, Optional[Point]]:
    ok, pt, _info = detect_colour(
        kleur=kleur,
        area_name=area_name,
        bot_id=bot_id,
        padding=padding,
        nearest_mouse=nearest_mouse,
        nearest_weighted=nearest_weighted,
        debug=debug,
        trace_on=trace_on,
        **_legacy,
    )
    return ok, pt


# ============================================================
# RUN (test)
# ============================================================
if __name__ == "__main__":
    ok, pt = click_colour(
        "cyaan",
        "Bot_Area",
        bot_id=1,
        padding=4,
        nearest_mouse=True,
        nearest_weighted=True,
        debug=True,
        trace_on=True,
    )
    print(ANSI.ok("OK ✅") if ok else ANSI.fail("FAIL ❌"), pt)