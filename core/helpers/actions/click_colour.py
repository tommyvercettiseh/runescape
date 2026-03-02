from __future__ import annotations

import sys
import random
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

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

# ai_mouse (optioneel klikgedrag)
try:
    from core.ai_mouse import human_move_to, human_click
except Exception:
    human_move_to = None
    human_click = None

Point = Tuple[int, int]
BBox = Tuple[int, int, int, int]

COLOR_RANGES_NP = compile_ranges_np()

# Extra ranges (optioneel)
_EXTRA_RANGES = {
    "wit":   [((0, 0, 200), (179, 45, 255))],
    "zwart": [((0, 0, 0), (179, 255, 45))],
    "roze":  [((160, 60, 60), (179, 255, 255))],
}
for k, ranges in _EXTRA_RANGES.items():
    if k not in COLOR_RANGES_NP:
        COLOR_RANGES_NP[k] = [(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)) for lo, hi in ranges]


# ============================================================
# ANSI (DICT SAFE)
# ============================================================
def _ansi(key: str, default: str = "") -> str:
    try:
        return ANSI.get(key, default)
    except Exception:
        return default

def _reset() -> str:
    try:
        return ANSI["reset"]
    except Exception:
        return _ansi("reset", "")

def _bold() -> str:
    return _ansi("bold", "")

def _dim() -> str:
    return _ansi("dim", "")

def _area_col() -> str:
    return _ansi("area", _ansi("paars", ""))


# ============================================================
# UTILS
# ============================================================
def _print(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)

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
    px = int(px)
    if px <= 0:
        return None
    k = px * 2 + 1
    return np.ones((k, k), np.uint8)

def _build_mask(colour: str, bbox: BBox) -> Optional[np.ndarray]:
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    rgb = np.array(img)
    if rgb.shape[-1] == 4:
        rgb = rgb[:, :, :3]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    ranges = COLOR_RANGES_NP.get(colour)
    if not ranges:
        return None

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, lo, hi)
        mask = m if mask is None else cv2.bitwise_or(mask, m)
    return mask

def _apply_padding(mask: np.ndarray, padding: int) -> np.ndarray:
    k = _kernel(padding)
    if k is None:
        return mask
    return cv2.erode(mask, k, iterations=1)

def _mask_pct(mask: np.ndarray) -> float:
    return float((mask > 0).mean() * 100.0)

def _filter_blobs(mask: np.ndarray, min_blob: int) -> tuple[np.ndarray, int, int, int]:
    min_blob = int(min_blob or 0)
    if min_blob <= 0:
        return mask, 0, 0, 0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    kept = np.zeros_like(mask)

    total = len(contours)
    kept_n = 0
    max_area = 0

    for cnt in contours:
        a = int(cv2.contourArea(cnt))
        if a > max_area:
            max_area = a
        if a >= min_blob:
            cv2.drawContours(kept, [cnt], -1, 255, -1)
            kept_n += 1

    return kept, total, kept_n, max_area

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

def _dbg_table(title: str, rows: list[tuple[str, Any]]) -> None:
    reset = _reset()
    print(f"\n{_bold()}{title}{reset}")
    for k, v in rows:
        print(f"{_dim()}{k:>16}{reset} : {v}")


# ============================================================
# PUBLIC API (naming intact)
# ============================================================
def detect_colour(
    kleur=None,
    area_name=None,
    bot_id: int = 1,

    padding: int = 3,
    nearest_mouse: bool = True,
    nearest_weighted: bool = True,

    min_blob: int = 400,

    debug: bool = False,
    trace_on: bool = False,

    **_legacy,
) -> tuple[bool, Optional[Point], Dict[str, object]]:
    if kleur is None:
        kleur = _legacy.get("colour") or _legacy.get("color") or "paars"
    if area_name is None:
        area_name = _legacy.get("area") or _legacy.get("area_name") or "Bot_Area"

    # backward compat keys
    min_blob = int(_legacy.get("min_blob", min_blob) or 0)
    if not min_blob:
        min_blob = int(_legacy.get("min_blob_area") or _legacy.get("min_size") or 0)

    kleur = normalize_colour(str(kleur))

    info: Dict[str, object] = {
        "kleur": kleur,
        "area_name": area_name,
        "bot_id": int(bot_id),
        "padding": int(padding),
        "nearest_mouse": bool(nearest_mouse),
        "nearest_weighted": bool(nearest_weighted),
        "min_blob": int(min_blob),
    }

    if kleur not in COLOR_RANGES_NP:
        info["reason"] = "Unknown colour"
        if debug:
            _dbg_table("❌ Detect Colour", [
                ("Status", "FAIL"),
                ("Reason", info["reason"]),
                ("Kleur", kleur),
                ("Area", area_name),
                ("Bot", bot_id),
            ])
        return False, None, info

    bbox = _area_bbox(area_name, bot_id)
    x1, y1, x2, y2 = bbox
    info["bbox"] = bbox

    mask0 = _build_mask(kleur, bbox)
    if mask0 is None:
        info["reason"] = "Mask build failed"
        if debug:
            _dbg_table("🚫 Detect Colour", [
                ("Status", "FAIL"),
                ("Reason", info["reason"]),
                ("Kleur", kleur),
                ("Area", area_name),
                ("Bot", bot_id),
            ])
        return False, None, info

    info["mask_pct_pre"] = f"{_mask_pct(mask0):.2f}%"
    info["pixels_pre"] = int((mask0 > 0).sum())

    mask = _apply_padding(mask0, int(padding))
    info["pixels_after_padding"] = int((mask > 0).sum())

    # ✅ blob filter
    mask, blobs_total, blobs_kept, blob_max_area = _filter_blobs(mask, min_blob)
    info["blobs_total"] = int(blobs_total)
    info["blobs_kept"] = int(blobs_kept)
    info["blob_max_area"] = int(blob_max_area)
    info["pixels_after_blobs"] = int((mask > 0).sum())

    if info["pixels_after_blobs"] <= 0:
        info["reason"] = "No pixels after blob filter"
        if debug:
            _dbg_table("🚫 Detect Colour", [
                ("Status", "FAIL"),
                ("Reason", info["reason"]),
                ("Kleur", kleur),
                ("Area", area_name),
                ("Bot", bot_id),
                ("Padding", padding),
                ("Min blob", min_blob),
                ("Blobs total", info["blobs_total"]),
                ("Blobs kept", info["blobs_kept"]),
                ("Max blob area", info["blob_max_area"]),
                ("Pixels pre", info["pixels_pre"]),
                ("Pixels after padding", info["pixels_after_padding"]),
                ("Pixels after blobs", info["pixels_after_blobs"]),
            ])
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
            _dbg_table("🚫 Detect Colour", [
                ("Status", "FAIL"),
                ("Reason", info["reason"]),
                ("Kleur", kleur),
                ("Area", area_name),
                ("Bot", bot_id),
            ])
        return False, None, info

    info["point"] = pt

    if debug:
        area_ansi = _area_col()
        reset = _reset()
        _dbg_table("🧪 Detect Colour", [
            ("Status", "OK"),
            ("Kleur", kleur),
            ("Area", f"{area_ansi}{area_name}{reset}"),
            ("Bot", bot_id),
            ("Padding", padding),
            ("Min blob", min_blob),
            ("Blobs total", info.get("blobs_total", 0)),
            ("Blobs kept", info.get("blobs_kept", 0)),
            ("Max blob area", info.get("blob_max_area", 0)),
            ("Nearest Mouse", nearest_mouse),
            ("Nearest Weighted", nearest_weighted),
            ("Mouse", mouse_xy),
            ("Point", pt),
            ("Mask % pre", info["mask_pct_pre"]),
            ("Pixels pre", info["pixels_pre"]),
            ("Pixels after padding", info["pixels_after_padding"]),
            ("Pixels after blobs", info["pixels_after_blobs"]),
        ])

    return True, pt, info


def click_colour(
    kleur=None,
    area_name=None,
    bot_id: int = 1,

    padding: int = 3,
    nearest_mouse: bool = True,
    nearest_weighted: bool = True,

    min_blob: int = 400,

    debug: bool = False,
    trace_on: bool = False,

    **_legacy,
) -> tuple[bool, Optional[Point]]:
    """
    Compat return: (ok, pt)

    Extra (optioneel):
      do_click=True  -> klikt ook echt (ai_mouse)
      button="left"
      min_size / min_blob_area / min_blob -> blob filtering
    """
    do_click = bool(_legacy.get("do_click", False))
    button = str(_legacy.get("button", "left"))

    ok, pt, _info = detect_colour(
        kleur=kleur,
        area_name=area_name,
        bot_id=bot_id,
        padding=padding,
        nearest_mouse=nearest_mouse,
        nearest_weighted=nearest_weighted,
        min_blob=min_blob,
        debug=debug,
        trace_on=trace_on,
        **_legacy,
    )

    if ok and pt and do_click:
        if human_move_to is None or human_click is None:
            debug and _print(True, "⚠️ Ai_mouse niet beschikbaar, do_click skipped")
        else:
            x, y = int(pt[0]), int(pt[1])
            human_move_to(x, y)
            human_click(button=button, mode="safe_tap")

    return ok, pt


# ============================================================
# TEST
# ============================================================
if __name__ == "__main__":
    ok, pt = click_colour(
        "cyaan",
        "Bot_Area",
        bot_id=1,
        padding=4,
        nearest_mouse=True,
        nearest_weighted=True,
        min_blob=400,
        debug=True,
        trace_on=True,
        do_click=True,
    )
    print(("OK ✅" if ok else "FAIL ❌"), pt)