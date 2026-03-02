from __future__ import annotations

from pathlib import Path
import numpy as np
import cv2
import pyautogui


def read_template_rgb_gray(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden of niet leesbaar: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return rgb, gray


def grab_region_rgb(box_xyxy):
    x1, y1, x2, y2 = box_xyxy
    w, h = x2 - x1, y2 - y1
    img = pyautogui.screenshot(region=(x1, y1, w, h))
    return np.array(img)


def crop_rgb(img_rgb: np.ndarray, x1: int, y1: int, x2: int, y2: int):
    h, w = img_rgb.shape[:2]
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return img_rgb
    return img_rgb[y1:y2, x1:x2]