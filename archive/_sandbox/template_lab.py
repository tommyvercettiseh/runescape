import json
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import load_areas, apply_offset

METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def _write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _color_score(template_rgb: np.ndarray, matched_rgb: np.ndarray) -> float:
    if matched_rgb.shape[:2] != template_rgb.shape[:2]:
        matched_rgb = cv2.resize(matched_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, matched_rgb)
    mae = float(np.mean(diff))
    return round(max(0.0, 100.0 - mae), 2)


def _grab_region_rgb(box) -> np.ndarray:
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))  # RGB


def _crop_interactive() -> tuple[np.ndarray, dict]:
    # full screenshot -> OpenCV ROI select
    shot = np.array(pyautogui.screenshot())
    bgr = cv2.cvtColor(shot, cv2.COLOR_RGB2BGR)

    roi = cv2.selectROI("Crop (drag, ENTER=save, ESC=cancel)", bgr, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    if w == 0 or h == 0:
        raise SystemExit("Geen crop gemaakt (cancel).")

    crop_bgr = bgr[y:y+h, x:x+w]
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)

    return crop_rgb, {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}


def save_template(crop_rgb: np.ndarray, name: str) -> Path:
    if not name.lower().endswith(".png"):
        name += ".png"
    out = Path(IMAGES_DIR) / name
    bgr = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out), bgr)
    return out


def analyze_all_methods(template_path: Path, area_name: str, bot_id: int = 1) -> list[dict]:
    areas = load_areas()
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    tpl_bgr = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if tpl_bgr is None:
        raise FileNotFoundError(f"Template niet leesbaar: {template_path}")

    tpl_rgb = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2RGB)
    tpl_gray = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
    th, tw = tpl_gray.shape[:2]

    box = apply_offset(areas[area_name], bot_id)
    shot_rgb = _grab_region_rgb(box)
    shot_gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)

    out = []
    for method_name, method in METHODS.items():
        res = cv2.matchTemplate(shot_gray, tpl_gray, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        is_sqdiff = method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED")
        top_left = min_loc if is_sqdiff else max_loc

        vorm = (1.0 - float(min_val) if is_sqdiff else float(max_val)) * 100.0
        vorm = round(min(100.0, max(0.0, vorm)), 2)

        x, y = int(top_left[0]), int(top_left[1])
        if x + tw > shot_rgb.shape[1] or y + th > shot_rgb.shape[0]:
            kleur = 0.0
        else:
            patch = shot_rgb[y:y+th, x:x+tw]
            kleur = _color_score(tpl_rgb, patch)

        out.append({
            "method": method_name,
            "vorm": vorm,
            "kleur": kleur,
            "pt": {"x": x, "y": y},
        })

    out.sort(key=lambda d: (d["vorm"], d["kleur"]), reverse=True)
    return out


def store_meta(template_name: str, meta: dict) -> None:
    db = _read_json(META_FILE)
    db[template_name] = meta
    _write_json(META_FILE, db)


def main():
    print("🖼️ Crop een template uit je scherm...")
    crop_rgb, roi = _crop_interactive()

    name = input("Naam template (bv WindowsLogo): ").strip()
    if not name:
        raise SystemExit("Geen naam gegeven.")

    template_path = save_template(crop_rgb, name)
    template_name = template_path.name
    print("✅ opgeslagen:", template_path)

    area_name = input("Area name (bv FullScreen): ").strip()
    bot_id_str = input("Bot ID (1-4, default 1): ").strip()
    bot_id = int(bot_id_str) if bot_id_str else 1

    results = analyze_all_methods(template_path, area_name, bot_id=bot_id)
    best = results[0]

    print("\n🏆 Best:")
    print(best)

    print("\n📋 Top 6:")
    for r in results[:6]:
        print(f"{r['method']:<16} vorm={r['vorm']:6.2f} kleur={r['kleur']:6.2f} pt={r['pt']}")

    meta = {
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "template": template_name,
        "roi_screen": roi,
        "area": area_name,
        "bot_id": bot_id,
        "best": best,
        "all": results,
    }
    store_meta(template_name, meta)
    print("\n💾 metadata opgeslagen:", META_FILE)


if __name__ == "__main__":
    main()
