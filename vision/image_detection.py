from __future__ import annotations

# === START BOOTSTRAP ===
# • WAT: zorgt dat imports vanuit project-root werken bij direct runnen.
# • WAAROM: maakt module portable voor CLI tests zonder hardcoded paden.
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === END BOOTSTRAP ===


# === START IMPORTS ===
# • WAT: alle externe/standaard imports die deze module nodig heeft.
# • WAAROM: centraal en voorspelbaar, voorkomt verborgen dependencies.
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset
# === END IMPORTS ===


# === START CONSTANTS ===
# • WAT: template matching method mapping + template meta/config + cache.
# • WAAROM: voorkomt magic values en maakt gedrag configureerbaar.
METHODS: Dict[str, int] = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"
_TEMPLATE_CACHE: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

VERBOSE_OFF = "off"
VERBOSE_SHORT = "short"
VERBOSE_DEBUG = "debug"
# === END CONSTANTS ===


# === START MODELS ===
# • WAT: dataclass voor een match-resultaat.
# • WAAROM: consistente return-structuur voor wrappers en callers.
@dataclass(frozen=True)
class Match:
    x: int
    y: int
    width: int
    height: int
    vorm: float
    kleur: float
    method: str
# === END MODELS ===


# === START SETTINGS ===
# • WAT: lezen van template meta instellingen (method/drempels).
# • WAAROM: defaults per template zonder code-aanpassingen.
def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import json
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
# === END SETTINGS ===


# === START TEMPLATE CACHE ===
# • WAT: resolve + cached inlezen van templates (bgr/rgb/gray).
# • WAAROM: sneller herhaald detecteren en minder disk IO.
def _resolve_template_path(image_name: str) -> Path:
    p = Path(image_name)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name


def _read_template(image_name: str):
    path = _resolve_template_path(image_name)
    key = str(path.resolve())

    if key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[key]

    bgr = cv2.imread(str(path))
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden: {path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    _TEMPLATE_CACHE[key] = (bgr, rgb, gray)
    return bgr, rgb, gray
# === END TEMPLATE CACHE ===


# === START SCORING ===
# • WAT: vormscore normalisatie + kleurvergelijking.
# • WAAROM: uniforme scoring over verschillende cv2 methods.
def _scoremap_0_1(result: np.ndarray, method: str) -> np.ndarray:
    s = cv2.normalize(result, None, 0, 1, cv2.NORM_MINMAX)
    if method.startswith("TM_SQDIFF"):
        s = 1.0 - s
    return s


def _color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, template_rgb.shape[:2][::-1])
    diff = cv2.absdiff(template_rgb, patch_rgb)
    return float(np.clip(100 - np.mean(diff), 0, 100))
# === END SCORING ===


# === START HELPERS ===
# • WAT: low-level helpers voor 1 detectie-run binnen één screenshot.
# • WAAROM: hergebruik tussen detect_image en detect_image_timeout, zonder duplicatie.
def _grab_area_rgb(x1: int, y1: int, w: int, h: int) -> np.ndarray:
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))


def _best_match_in_shot(
    shot_rgb: np.ndarray,
    tpl_rgb: np.ndarray,
    tpl_gray: np.ndarray,
    method_name: str,
) -> Tuple[Optional[Tuple[int, int]], float, float, str]:
    """
    Returns:
      (loc_xy, vorm_score_0_100, kleur_score_0_100, method_used)
    """
    gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)
    th, tw = tpl_gray.shape[:2]

    candidates: List[Tuple[Optional[Tuple[int, int]], float, float, str]] = []

    for mname, mval in METHODS.items():
        if method_name != "ALL" and mname != method_name:
            continue

        res = cv2.matchTemplate(gray, tpl_gray, mval)
        scoremap = _scoremap_0_1(res, mname)
        _, score, _, loc = cv2.minMaxLoc(scoremap)

        vorm = float(score * 100)
        rx, ry = map(int, loc)

        patch = shot_rgb[ry:ry + th, rx:rx + tw]
        if patch.shape[:2] != (th, tw):
            # match ligt (deels) buiten screenshot, skip
            candidates.append((None, vorm, 0.0, mname))
            continue

        kleur = _color_score(tpl_rgb, patch)
        candidates.append(((rx, ry), vorm, float(kleur), mname))

    if not candidates:
        return None, 0.0, 0.0, method_name

    # kies hoogste vormscore als "beste" (zelfde als je huidige detect_image selectie)
    best = max(candidates, key=lambda t: t[1])
    return best[0], round(best[1], 2), round(best[2], 2), best[3]
# === END HELPERS ===


# === START LOGGING ===
# • WAT: korte, scanbare output voor success/fail.
# • WAAROM: consistent logging gedrag voor alle detect functies.
def _log(image: str, ok: bool, area: str, bot: int, hit: Optional[Match], verbose: str):
    if verbose == VERBOSE_OFF:
        return

    if not ok:
        print(f"🔴 {image} not found in {area} for bot {bot}")
        return

    print(
        f"🟢 {image} found in {area} for bot {bot} | "
        f"Vorm={int(hit.vorm)}% | Kleur={int(hit.kleur)}% | method={hit.method}"
    )

    if verbose == VERBOSE_DEBUG:
        print(f"   abs_xy=({hit.x},{hit.y}) size=({hit.width}x{hit.height})")
# === END LOGGING ===


# === START CORE LOGIC ===
# • WAT: gedeelde kernlogica om thresholds/method te bepalen (meta + overrides).
# • WAAROM: voorkomt verspreide defaults en maakt API dynamisch uitbreidbaar.
def _resolve_detection_params(
    image_name: str,
    method_name: Optional[str],
    vorm_drempel: Optional[float],
    kleur_drempel: Optional[float],
) -> Tuple[str, float, float]:
    cfg = _load_template_settings(image_name)

    method = method_name or cfg["method"]
    min_shape = float(vorm_drempel if vorm_drempel is not None else cfg["min_shape"])
    min_color = float(kleur_drempel if kleur_drempel is not None else cfg["min_color"])

    if method != "ALL" and method not in METHODS:
        raise KeyError(f"Ongeldige methode: {method}")

    return method, min_shape, min_color
# === END CORE LOGIC ===


# === START API ===
# • WAT: publieke detect functies (1x check en timeout variant).
# • WAAROM: callers hoeven geen cv2/pyautogui details te kennen.
def detect_image(
    image_name: str,
    area_name: str,
    bot_id: int = 1,
    areas: Optional[Dict[str, List[int]]] = None,
    verbose: str = "short",
) -> Optional[Match]:

    method, min_shape, min_color = _resolve_detection_params(
        image_name=image_name,
        method_name=None,
        vorm_drempel=None,
        kleur_drempel=None,
    )

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    _, tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1

    shot = _grab_area_rgb(x1, y1, w, h)
    loc, vorm, kleur, used_method = _best_match_in_shot(shot, tpl_rgb, tpl_gray, method)

    best: Optional[Match] = None
    if loc is not None and vorm >= min_shape and kleur >= min_color:
        rx, ry = loc
        best = Match(x1 + rx, y1 + ry, tw, th, vorm, kleur, used_method)

    _log(image_name, bool(best), area_name, bot_id, best, verbose)
    return best


def detect_image_timeout(
    image_name: str,
    area_name: str,
    method_name: Optional[str] = None,
    vorm_drempel: Optional[float] = None,
    kleur_drempel: Optional[float] = None,
    bot_id: int = 1,
    timeout_sec: float = 0,
    sleep_sec: float = 0.1,
    areas: Optional[Dict[str, List[int]]] = None,
    verbose: str = "short",
) -> Optional[Match]:
    """
    Timeout-variant op basis van jouw originele werkwijze:
    - timeout_sec <= 0  => 1 directe check
    - timeout_sec > 0   => blijf proberen tot deadline
    """

    method, min_shape, min_color = _resolve_detection_params(
        image_name=image_name,
        method_name=method_name,
        vorm_drempel=vorm_drempel,
        kleur_drempel=kleur_drempel,
    )

    areas = areas or load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    _, tpl_rgb, tpl_gray = _read_template(image_name)
    th, tw = tpl_gray.shape[:2]

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1

    start_ts = time.time()
    deadline = (start_ts + float(timeout_sec)) if timeout_sec and timeout_sec > 0 else None

    if verbose != VERBOSE_OFF:
        print(
            f"🔎 Start detect_image_timeout area={area_name} method={method} "
            f"timeout={timeout_sec}s drempels vorm={min_shape} kleur={min_color}"
        )

    last_vorm = 0.0
    last_kleur = 0.0
    last_method = method

    while True:
        shot = _grab_area_rgb(x1, y1, w, h)
        loc, vorm, kleur, used_method = _best_match_in_shot(shot, tpl_rgb, tpl_gray, method)

        last_vorm, last_kleur, last_method = vorm, kleur, used_method

        if loc is not None and vorm >= min_shape and kleur >= min_color:
            rx, ry = loc
            hit = Match(x1 + rx, y1 + ry, tw, th, vorm, kleur, used_method)

            if verbose != VERBOSE_OFF:
                elapsed = time.time() - start_ts
                print(
                    f"✅ Gevonden binnen {elapsed:.2f}s op ({hit.x}, {hit.y}) "
                    f"vorm={hit.vorm} kleur={hit.kleur} w={hit.width} h={hit.height}"
                )
            _log(image_name, True, area_name, bot_id, hit, verbose)
            return hit

        # directe check (timeout_sec <= 0)
        if deadline is None:
            if verbose != VERBOSE_OFF:
                print(
                    f"❌ Niet gevonden bij directe check. Laatste scores vorm={last_vorm} kleur={last_kleur} method={last_method}"
                )
            _log(image_name, False, area_name, bot_id, None, verbose)
            return None

        # timeout check
        if time.time() >= deadline:
            if verbose != VERBOSE_OFF:
                elapsed = time.time() - start_ts
                print(
                    f"⏱️ Timeout na {elapsed:.2f}s. Niet gevonden. Laatste scores vorm={last_vorm} kleur={last_kleur} method={last_method}"
                )
            _log(image_name, False, area_name, bot_id, None, verbose)
            return None

        time.sleep(float(max(0.0, sleep_sec)))
# === END API ===


# === START CLI TEST ===
# • WAT: veilige handmatige tests.
# • WAAROM: snel verifiëren zonder extra tooling.
if __name__ == "__main__":
    print("⚠️ CLI test: zorg dat je doelvenster zichtbaar is. Start in 2s...")
    time.sleep(2)

    detect_image("jagex.png", "Bot_Area", bot_id=1, verbose="short")

    # Timeout variant (voorbeeld)
    detect_image_timeout(
        "jagex.png",
        "Bot_Area",
        bot_id=1,
        timeout_sec=3,
        sleep_sec=0.1,
        verbose="short",
    )
# === END CLI TEST ===
