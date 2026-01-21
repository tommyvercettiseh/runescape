from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pyautogui


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HSV_JSON = PROJECT_ROOT / "config" / "hsv_ranges.json"


def load_label(label: str):
    data = json.loads(HSV_JSON.read_text(encoding="utf-8"))
    info = data["labels"][label]
    return tuple(info["lower"]), tuple(info["upper"])


def find_blob_center(bgr, lower, upper, min_area=80):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    mask = cv2.inRange(
        hsv,
        np.array(lower, dtype=np.uint8),
        np.array(upper, dtype=np.uint8),
    )

    k = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None, 0

    c = max(cnts, key=cv2.contourArea)
    area = int(cv2.contourArea(c))
    if area < int(min_area):
        return None, area

    x, y, w, h = cv2.boundingRect(c)
    return (x + w // 2, y + h // 2), area


if __name__ == "__main__":
    label = "fire"
    lower, upper = load_label(label)

    # ROI in het midden van je cursor (makkelijk testen)
    roi_w, roi_h = 800, 600
    cx, cy = pyautogui.position()
    x1, y1 = int(cx - roi_w // 2), int(cy - roi_h // 2)

    img = pyautogui.screenshot(region=(x1, y1, roi_w, roi_h))
    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    center, area = find_blob_center(bgr, lower, upper, min_area=80)

    print("HSV:", lower, upper)
    print("center:", center, "area:", area)
    if center:
        print("ABS:", (x1 + center[0], y1 + center[1]))
