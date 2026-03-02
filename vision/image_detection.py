from __future__ import annotations

import sys
import time
import json
import random
from pathlib import Path

import cv2
import numpy as np
import pyautogui

# ============================================================
# BOOTSTRAP
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# PROJECT IMPORTS
# ============================================================
from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset
from core.ansi import ANSI
from helpers.log import log

# ============================================================
# CONSTANTS
# ============================================================
METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"
_TEMPLATE_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}

DEBUG_WINDOW_NAME = "ImageDetect Debug (ESC to close)"


# ============================================================
# VERBOSE NORMALIZER
# ============================================================
def _is_verbose(v) -> bool:
    if v is True:
        return True
    if v is False or v is None:
        return False
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("off", "false", "0", "no", "none", ""):
            return False
        return True
    return bool(v)


# ============================================================
# HIT
# ============================================================
class Hit:
    def __init__(self, x, y, width, height, vorm, kleur):
        self.x = int(x)
        self.y = int(y)
        self.width = int(width)
        self.height = int(height)
        self.vorm = float(vorm)
        self.kleur = float(kleur)


# ============================================================
# SETTINGS
# ============================================================
def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _load_template_settings(image_name: str) -> dict:
    meta = _safe_read_json(META_FILE)
    d = meta.get(image_name, {})
    return {
        "method": d.get("method", "TM_CCOEFF"),
        "min_shape": float(d.get("min_shape", 85)),
        "min_color": float(d.get("min_color", 60)),
    }


# ============================================================
# TEMPLATE CACHE
# ============================================================
def _resolve_template_path(image_name: str) -> Path:
    p = Path(image_name)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name


def _read_template(image_name: str) -> tuple[np.ndarray, np.ndarray]:
    path = _resolve_template_path(image_name)
    key = str(path.resolve())

    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    _TEMPLATE_CACHE[key] = (rgb, gray)
    return rgb, gray


# ============================================================
# SCORING
# ============================================================
def _scoremap_0_1(result: np.ndarray, method_name: str) -> np.ndarray:
    s = cv2.normalize(result, None, 0, 1, cv2.NORM_MINMAX)
    if method_name.startswith("TM_SQDIFF"):
        s = 1.0 - s
    return s


def _color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, template_rgb.shape[:2][::-1])
    diff = cv2.absdiff(template_rgb, patch_rgb)
    return float(np.clip(100 - np.mean(diff), 0, 100))


# ============================================================
# SCREENSHOT HELPERS
# ============================================================
def _grab_area_rgb(x1: int, y1: int, w: int, h: int) -> np.ndarray:
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))


def _pretty_label(image_name: str) -> str:
    return Path(image_name).stem.replace("_", " ").strip().title()


# ============================================================
# LOGGING (Found = volledig groen, area paars)
# ============================================================
def _log_found(image_name: str, area_name: str, *, elapsed: float | None, trace: bool, verbose: bool):
    if not _is_verbose(verbose):
        return
    label = _pretty_label(image_name)
    t = f" | {elapsed:.2f}s" if elapsed is not None else ""
    msg = (
        f"{ANSI.GREEN}"
        f"🟢🖼️  Found | "
        f"{ANSI.CYAN}{label}{ANSI.GREEN} in "
        f"{ANSI.PURPLE}{area_name}{ANSI.GREEN}"
        f"{t}"
        f"{ANSI.RESET}"
    )
    log(True, msg, trace=trace)


def _log_not_found(image_name: str, area_name: str, *, elapsed: float | None, trace: bool, verbose: bool):
    if not _is_verbose(verbose):
        return
    label = _pretty_label(image_name)
    t = f" | {elapsed:.2f}s" if elapsed is not None else ""
    msg = (
        f"{ANSI.RED}"
        f"🔴🖼️  Not found | "
        f"{ANSI.CYAN}{label}{ANSI.RED} in "
        f"{ANSI.PURPLE}{area_name}{ANSI.RED}"
        f"{t}"
        f"{ANSI.RESET}"
    )
    log(True, msg, trace=trace)


# ============================================================
# DEBUG POPUP (1 window, ESC closes)
# Links: area
# Rechts: template
# Box: alleen als echte hit (thresholds gehaald)
# ============================================================
def _debug_popup(
    *,
    image_name: str,
    area_name: str,
    bot_id: int,
    shot_rgb: np.ndarray,
    tpl_rgb: np.ndarray,
    loc: tuple[int, int] | None,
    tw: int,
    th: int,
    vorm: float,
    kleur: float,
    min_shape: float,
    min_color: float,
    is_hit: bool,
):
    left = shot_rgb.copy()

    if loc is not None and is_hit:
        rx, ry = loc
        cv2.rectangle(left, (rx, ry), (rx + tw, ry + th), (0, 255, 0), 2)

    label = _pretty_label(image_name)
    status = "HIT ✅" if is_hit else "NO HIT ❌"
    header = f"{status} | {label} in {area_name} | bot={bot_id}"
    sub = f"vorm={vorm:.1f}/{min_shape:.1f}  kleur={kleur:.1f}/{min_color:.1f}"

    cv2.putText(left, header, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(left, sub, (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
    cv2.putText(left, "ESC = close", (10, left.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    right = tpl_rgb.copy()
    if right.shape[0] != left.shape[0]:
        scale = left.shape[0] / right.shape[0]
        right = cv2.resize(right, (max(1, int(right.shape[1] * scale)), left.shape[0]))

    combined = np.concatenate([left, right], axis=1)
    bgr = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)

    cv2.imshow(DEBUG_WINDOW_NAME, bgr)

    while True:
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break

    cv2.destroyWindow(DEBUG_WINDOW_NAME)


# ============================================================
# BEST MATCH (single)
# ============================================================
def _best_match_in_shot(shot_rgb: np.ndarray, tpl_rgb: np.ndarray, tpl_gray: np.ndarray, method_name: str):
    gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)
    th, tw = tpl_gray.shape[:2]

    best_loc = None
    best_vorm = 0.0
    best_kleur = 0.0

    method_names = list(METHODS.keys()) if method_name == "ALL" else [method_name]

    for mname in method_names:
        mval = METHODS.get(mname)
        if mval is None:
            continue

        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)
        _, score, _, loc = cv2.minMaxLoc(scoremap)

        vorm = float(score * 100.0)
        rx, ry = int(loc[0]), int(loc[1])

        patch = shot_rgb[ry:ry + th, rx:rx + tw]
        if patch.shape[:2] != (th, tw):
            continue

        kleur = _color_score(tpl_rgb, patch)

        if vorm > best_vorm:
            best_vorm = vorm
            best_kleur = kleur
            best_loc = (rx, ry)

    return best_loc, round(best_vorm, 2), round(best_kleur, 2)


# ============================================================
# SINGLE PASS DETECT
# Return: (Hit|None, dbg dict)
# ============================================================
def _detect_image_once(image_name: str, area_name: str, *, bot_id: int, areas: dict | None):
    cfg = _load_template_settings(image_name)
    method = cfg["method"]
    min_shape = float(cfg["min_shape"])
    min_color = float(cfg["min_color"])

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 1 or h <= 1:
        return None, None

    shot = _grab_area_rgb(x1, y1, w, h)
    loc, vorm, kleur = _best_match_in_shot(shot, tpl_rgb, tpl_gray, method)

    is_hit = bool(loc) and (float(vorm) >= float(min_shape)) and (float(kleur) >= float(min_color))

    hit = None
    if is_hit and loc:
        rx, ry = int(loc[0]), int(loc[1])
        hit = Hit(
            x=x1 + rx,
            y=y1 + ry,
            width=tw,
            height=th,
            vorm=round(float(vorm), 2),
            kleur=round(float(kleur), 2),
        )

    dbg = {
        "cfg": cfg,
        "shot": shot,
        "tpl": tpl_rgb,
        "loc": loc,
        "tw": tw,
        "th": th,
        "vorm": float(vorm),
        "kleur": float(kleur),
        "min_shape": float(min_shape),
        "min_color": float(min_color),
        "is_hit": bool(is_hit),
    }
    return hit, dbg


# ============================================================
# PUBLIC API: detect_image
# ============================================================
def detect_image(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
    areas: dict | None = None,
    verbose=True,
    timeout: float | None = None,
    interval: float = 1.0,
    trace: bool = False,
    debug: bool = False,
):
    v = _is_verbose(verbose)
    start = time.time()

    last_dbg = None

    hit, dbg = _detect_image_once(image_name, area_name, bot_id=bot_id, areas=areas)
    last_dbg = dbg

    if hit:
        _log_found(image_name, area_name, elapsed=time.time() - start, trace=trace, verbose=v)
        if debug and last_dbg:
            _debug_popup(
                image_name=image_name,
                area_name=area_name,
                bot_id=bot_id,
                shot_rgb=last_dbg["shot"],
                tpl_rgb=last_dbg["tpl"],
                loc=last_dbg["loc"],
                tw=last_dbg["tw"],
                th=last_dbg["th"],
                vorm=last_dbg["vorm"],
                kleur=last_dbg["kleur"],
                min_shape=last_dbg["min_shape"],
                min_color=last_dbg["min_color"],
                is_hit=True,
            )
        return hit

    if timeout is None or float(timeout) <= 0:
        _log_not_found(image_name, area_name, elapsed=time.time() - start, trace=trace, verbose=v)
        if debug and last_dbg:
            _debug_popup(
                image_name=image_name,
                area_name=area_name,
                bot_id=bot_id,
                shot_rgb=last_dbg["shot"],
                tpl_rgb=last_dbg["tpl"],
                loc=last_dbg["loc"],
                tw=last_dbg["tw"],
                th=last_dbg["th"],
                vorm=last_dbg["vorm"],
                kleur=last_dbg["kleur"],
                min_shape=last_dbg["min_shape"],
                min_color=last_dbg["min_color"],
                is_hit=False,
            )
        return None

    end = start + float(timeout)
    sleep_s = max(0.01, float(interval))

    while time.time() < end:
        time.sleep(sleep_s)
        hit, dbg = _detect_image_once(image_name, area_name, bot_id=bot_id, areas=areas)
        last_dbg = dbg

        if hit:
            _log_found(image_name, area_name, elapsed=time.time() - start, trace=trace, verbose=v)
            if debug and last_dbg:
                _debug_popup(
                    image_name=image_name,
                    area_name=area_name,
                    bot_id=bot_id,
                    shot_rgb=last_dbg["shot"],
                    tpl_rgb=last_dbg["tpl"],
                    loc=last_dbg["loc"],
                    tw=last_dbg["tw"],
                    th=last_dbg["th"],
                    vorm=last_dbg["vorm"],
                    kleur=last_dbg["kleur"],
                    min_shape=last_dbg["min_shape"],
                    min_color=last_dbg["min_color"],
                    is_hit=True,
                )
            return hit

    _log_not_found(image_name, area_name, elapsed=time.time() - start, trace=trace, verbose=v)
    if debug and last_dbg:
        _debug_popup(
            image_name=image_name,
            area_name=area_name,
            bot_id=bot_id,
            shot_rgb=last_dbg["shot"],
            tpl_rgb=last_dbg["tpl"],
            loc=last_dbg["loc"],
            tw=last_dbg["tw"],
            th=last_dbg["th"],
            vorm=last_dbg["vorm"],
            kleur=last_dbg["kleur"],
            min_shape=last_dbg["min_shape"],
            min_color=last_dbg["min_color"],
            is_hit=False,
        )
    return None


# ============================================================
# BACKWARDS COMPAT: detect_images (clean logging, no spam)
# ============================================================
# ============================================================
# BACKWARDS COMPAT: detect_images (bulletproof, no log helpers)
# ============================================================
def detect_images(
    images,
    area_name,
    bot_id=1,
    areas=None,
    verbose=False,
    max_hits=60,
    nms_radius=0,
    trace=False,        # genegeerd (compat)
    trace_depth=0,      # genegeerd (compat)
    pick="random",      # "random" of "first"
    debug=False,
):
    """
    Bulletproof detect_images voor click_image.

    Compat:
      click_image roept detect_images(img, area, max_hits=1) aan -> werkt.

    Gedrag:
      images mag str of list[str] zijn.
      Als list en pick="random" -> random volgorde templates.
      Return: list[Hit] (zoals click_image verwacht)
    """

    def _dbg(msg: str):
        if debug:
            print(msg)

    # ✅ string-safe
    if isinstance(images, (str, Path)):
        image_list = [str(images)]
    else:
        try:
            image_list = [str(x) for x in list(images) if x]
        except TypeError:
            image_list = [str(images)]

    if not image_list:
        _dbg("⚠️ detect_images: empty image list")
        return []

    # ✅ random template order
    if pick == "random" and len(image_list) > 1:
        random.shuffle(image_list)

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    # area grab 1x per template
    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 1 or h <= 1:
        _dbg(f"⚠️ detect_images: invalid area size for {area_name} (w={w}, h={h})")
        return []

    for image_name in image_list:
        try:
            cfg = _load_template_settings(image_name)
            method = cfg["method"]
            min_shape = float(cfg["min_shape"])
            min_color = float(cfg["min_color"])
            tpl_rgb, tpl_gray = _read_template(image_name)
        except FileNotFoundError:
            _dbg(f"⚠️ missing template: {image_name}")
            continue
        except Exception as e:
            _dbg(f"⚠️ template error {image_name}: {e}")
            continue

        th, tw = tpl_gray.shape[:2]

        shot = _grab_area_rgb(x1, y1, w, h)
        gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)

        method_names = list(METHODS.keys()) if method == "ALL" else [method]
        minimum_score_0_1 = float(min_shape) / 100.0

        hits: list[Hit] = []

        for mname in method_names:
            mval = METHODS.get(mname)
            if mval is None:
                continue

            res = cv2.matchTemplate(gray, tpl_gray, mval)
            scoremap = _scoremap_0_1(res, mname)

            ys, xs = np.where(scoremap >= minimum_score_0_1)
            if len(xs) == 0:
                continue

            scores = scoremap[ys, xs]
            order = np.argsort(scores)[::-1]

            rad = int(nms_radius) if int(nms_radius) > 0 else max(6, int(min(tw, th) * 0.55))

            picked = []
            for idx in order:
                rx = int(xs[idx])
                ry = int(ys[idx])
                score_0_1 = float(scores[idx])
                vorm = float(score_0_1 * 100.0)

                # NMS
                too_close = False
                for px, py, _ in picked:
                    dx = rx - px
                    dy = ry - py
                    if (dx * dx + dy * dy) <= (rad * rad):
                        too_close = True
                        break
                if too_close:
                    continue

                patch = shot[ry:ry + th, rx:rx + tw]
                if patch.shape[:2] != (th, tw):
                    continue

                kleur = _color_score(tpl_rgb, patch)
                if kleur < float(min_color):
                    continue

                picked.append((rx, ry, vorm))

                hits.append(
                    Hit(
                        x=x1 + rx,
                        y=y1 + ry,
                        width=tw,
                        height=th,
                        vorm=round(vorm, 2),
                        kleur=round(kleur, 2),
                    )
                )

                if len(hits) >= int(max_hits):
                    break

            if len(hits) >= int(max_hits):
                break

        if hits:
            _dbg(f"✅ found: {image_name} | hits={len(hits)}")
            return hits

        _dbg(f"❌ not found: {image_name}")

        if pick == "first":
            return []

    return []


# ============================================================
# CLI TEST
# ============================================================
if __name__ == "__main__":
    print("⚠️ CLI test: zorg dat je doelvenster zichtbaar is. Start in 2s...")
    time.sleep(2)

    hit = detect_image(
        "xp.png",
        "Info_Area",
        bot_id=1,
        verbose=True,
        timeout=5,
        interval=1.0,
        trace=False,
        debug=True,
    )

    print(f"🏁 Result: {ANSI.GREEN}OK ✅{ANSI.RESET}" if hit else f"🏁 Result: {ANSI.RED}FAIL ❌{ANSI.RESET}")