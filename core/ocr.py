# core/ocr.py
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import re
from typing import Optional

import cv2
import numpy as np
import pyautogui
import pytesseract

from config.areas import load_coords
from core.bot_offsets import apply_offset


def print_exact(text: str) -> None:
    # Monospace box, behoudt spaties en tabs
    print("┌─ OCR RAW ─────────────────────────")
    for line in (text or "").splitlines():
        print("│ " + line)
    print("└───────────────────────────────────")


def ocr_text(
    area_name: str,
    *,
    bot_id: int = 1,
    lang: str = "eng",
    psm: int = 7,
    whitelist: Optional[str] = None,
    preprocess: str = "thresh",   # "none" | "gray" | "thresh"
    scale: int = 2,
    verbose: bool = False,
) -> str:
    x1, y1, x2, y2 = load_coords(area_name)

    # apply_offset wil list [x1,y1,x2,y2]
    x1, y1, x2, y2 = apply_offset([int(x1), int(y1), int(x2), int(y2)], bot_id=bot_id)

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)

    if w <= 0 or h <= 0:
        raise ValueError(f"Area '{area_name}' coords fout: {[x1,y1,x2,y2]}")

    img = pyautogui.screenshot(region=(x, y, w, h))
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    if scale > 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    if preprocess != "none":
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if preprocess == "thresh":
        img = cv2.GaussianBlur(img, (3, 3), 0)
        img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    cfg = f"--oem 3 --psm {psm}"
    if whitelist:
        cfg += f' -c tessedit_char_whitelist="{whitelist}"'

    # ✅ RAW output: geen re.sub cleanup, geen strip
    text = pytesseract.image_to_string(img, lang=lang, config=cfg) or ""

    if verbose:
        print(f"🔎 OCR [{area_name}] bot={bot_id} region={(x,y,w,h)}")
        print_exact(text)

    return text


def ocr_number(area_name: str, *, bot_id: int = 1, verbose: bool = False) -> Optional[int]:
    txt = ocr_text(
        area_name,
        bot_id=bot_id,
        psm=7,
        whitelist="0123456789",
        preprocess="thresh",
        scale=2,
        verbose=verbose,
    )
    digits = re.sub(r"\D+", "", txt or "")
    return int(digits) if digits else None


if __name__ == "__main__":
    BOT_ID = 1
    AREA = "Run_Energy"

    print("🧪 OCR test")
    txt = ocr_number(AREA, bot_id=BOT_ID, verbose=True)
    print("📄 RESULT RAW (ook retour):")
    print_exact(txt)
