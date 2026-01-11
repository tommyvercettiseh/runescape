from __future__ import annotations

import sys
from pathlib import Path
import random

import cv2
import numpy as np
from PIL import ImageGrab, Image, ImageTk

import tkinter as tk
from tkinter import ttk

# ============================================================
# BOOTSTRAP (project root)
# ============================================================
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]  # Runescape/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# IMPORTS (project)
# ============================================================
from config.areas import load_coords

# ============================================================
# BOT OFFSETS
# ============================================================
BOT_OFFSETS = {
    1: (0, 0),
    2: (958, 0),
    3: (0, 498),
    4: (958, 498),
}

def _area_bbox(area_name: str, bot_id: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = load_coords(area_name)
    ox, oy = BOT_OFFSETS.get(int(bot_id), (0, 0))
    return x1 + ox, y1 + oy, x2 + ox, y2 + oy

# ============================================================
# COLOURS (HSV ranges: lower/upper)
# ============================================================
COLOR_ALIASES = {
    "cyaan": "cyan",
    "paars": "purple",
    "roze": "pink",
    "groen": "green",
    "geel": "yellow",
    "oranje": "orange",
    "rood": "red",
    "blauw": "blue",
    "wit": "white",
    "zwart": "black",
}

COLOR_RANGES = {
    "cyan":   ((80, 80, 80),   (100, 255, 255)),
    "blue":   ((100, 80, 60),  (130, 255, 255)),
    "purple": ((130, 60, 60),  (160, 255, 255)),
    "pink":   ((160, 60, 60),  (179, 255, 255)),
    "green":  ((35, 70, 70),   (85, 255, 255)),
    "yellow": ((20, 80, 80),   (35, 255, 255)),
    "orange": ((10, 80, 80),   (20, 255, 255)),
    "red":    ((0, 80, 80),    (10, 255, 255)),
    "white":  ((0, 0, 200),    (179, 45, 255)),
    "black":  ((0, 0, 0),      (179, 255, 45)),
}

def _grab_area_rgb(bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))  # PIL RGB
    return np.array(img)

def _make_mask(hsv: np.ndarray, kleur_key: str) -> np.ndarray:
    lower, upper = map(np.array, COLOR_RANGES[kleur_key])
    return cv2.inRange(hsv, lower, upper)

def _centroid_of_biggest(mask: np.ndarray, min_size: int = 15):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contours = [c for c in contours if cv2.contourArea(c) >= int(min_size)]
    if not contours:
        return None

    biggest = max(contours, key=cv2.contourArea)
    M = cv2.moments(biggest)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    area_px = float(cv2.contourArea(biggest))
    return (cx, cy, area_px)

def _draw_cross(img_bgr: np.ndarray, x: int, y: int, size: int = 8):
    h, w = img_bgr.shape[:2]
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    cv2.line(img_bgr, (x - size, y), (x + size, y), (0, 255, 0), 2)
    cv2.line(img_bgr, (x, y - size), (x, y + size), (0, 255, 0), 2)

def _overlay_dim_except_mask(rgb: np.ndarray, mask: np.ndarray, dim_alpha: float = 0.5) -> np.ndarray:
    """
    rest 50% donker, mask blijft helder (en krijgt een klein kleurtje erover)
    """
    rgb = rgb.copy().astype(np.float32)

    # dim alles
    rgb *= (1.0 - dim_alpha)

    # pixels die in mask zitten terug helder + highlight
    on = mask > 0
    # originele helderheid terug (ongeveer)
    # (we pakken gewoon 2x dim terug naar 100%, werkt lekker zichtbaar)
    rgb[on] *= (1.0 / max(1e-6, (1.0 - dim_alpha)))

    # highlight (licht groen)
    rgb[on, 1] = np.clip(rgb[on, 1] + 80, 0, 255)

    return rgb.astype(np.uint8)

class ColourPickerUI(tk.Tk):
    def __init__(self, area_name: str, bot_id: int, default_colour: str = "purple"):
        super().__init__()
        self.title("Colour Picker Debug")
        self.attributes("-topmost", True)

        self.area_name = area_name
        self.bot_id = bot_id

        self.colour_var = tk.StringVar(value=default_colour)
        self.opacity_var = tk.DoubleVar(value=0.50)
        self.min_size_var = tk.IntVar(value=15)

        self.info_var = tk.StringVar(value="Klik in de screenshot om RGB/HSV te picken 😈")

        self._rgb = None
        self._hsv = None
        self._mask = None

        self._img_left_tk = None
        self._img_right_tk = None

        self._build()
        self.refresh()

    def _build(self):
        root = ttk.Frame(self, padding=10)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        top = ttk.Frame(root)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(10, weight=1)

        ttk.Label(top, text="Kleur:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        kleur_box = ttk.Combobox(top, textvariable=self.colour_var, values=list(COLOR_RANGES.keys()), width=10, state="readonly")
        kleur_box.grid(row=0, column=1, sticky="w")
        kleur_box.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(top, text="Opacity dim:").grid(row=0, column=2, sticky="w", padx=(12, 6))
        op = ttk.Scale(top, from_=0.10, to=0.85, variable=self.opacity_var, command=lambda e: self.refresh_mask_only())
        op.grid(row=0, column=3, sticky="ew")
        ttk.Label(top, textvariable=self.opacity_var, width=5).grid(row=0, column=4, sticky="w", padx=(6, 0))

        ttk.Label(top, text="Min size:").grid(row=0, column=5, sticky="w", padx=(12, 6))
        ms = ttk.Spinbox(top, from_=1, to=5000, textvariable=self.min_size_var, width=6, command=self.refresh)
        ms.grid(row=0, column=6, sticky="w")

        ttk.Button(top, text="Refresh screenshot", command=self.refresh).grid(row=0, column=7, sticky="w", padx=(12, 0))

        ttk.Label(root, textvariable=self.info_var).grid(row=1, column=0, sticky="w", pady=(8, 8))

        panels = ttk.Frame(root)
        panels.grid(row=2, column=0, sticky="nsew")
        root.rowconfigure(2, weight=1)
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(0, weight=1)

        self.left = ttk.Label(panels)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left.bind("<Button-1>", self.on_click_left)

        self.right = ttk.Label(panels)
        self.right.grid(row=0, column=1, sticky="nsew")

    def refresh(self):
        bbox = _area_bbox(self.area_name, self.bot_id)
        rgb = _grab_area_rgb(bbox)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

        kleur = self.colour_var.get().strip().lower()
        mask = _make_mask(hsv, kleur)

        self._rgb, self._hsv, self._mask = rgb, hsv, mask
        self._render_left()
        self._render_right()

        pct = (mask > 0).mean() * 100.0
        cen = _centroid_of_biggest(mask, min_size=int(self.min_size_var.get()))
        if cen:
            cx, cy, area_px = cen
            self.info_var.set(f"Mask: {pct:.1f}%  grootste vlak: {area_px:.0f}px  centroid: ({cx},{cy}) ✅  (klik om te picken)")
        else:
            self.info_var.set(f"Mask: {pct:.1f}%  geen vlak ≥ {self.min_size_var.get()}px ⚠️  (klik om te picken)")

    def refresh_mask_only(self):
        if self._rgb is None or self._mask is None:
            return
        self._render_right()

    def _render_left(self):
        img = Image.fromarray(self._rgb)
        self._img_left_tk = ImageTk.PhotoImage(img)
        self.left.configure(image=self._img_left_tk)

    def _render_right(self):
        rgb = self._rgb.copy()
        mask = self._mask

        overlay = _overlay_dim_except_mask(rgb, mask, dim_alpha=float(self.opacity_var.get()))
        bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)

        cen = _centroid_of_biggest(mask, min_size=int(self.min_size_var.get()))
        if cen:
            cx, cy, _ = cen
            _draw_cross(bgr, cx, cy)

        out_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(out_rgb)

        self._img_right_tk = ImageTk.PhotoImage(img)
        self.right.configure(image=self._img_right_tk)

    def on_click_left(self, event):
        if self._rgb is None or self._hsv is None:
            return

        x, y = int(event.x), int(event.y)
        h, w = self._rgb.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return

        r, g, b = self._rgb[y, x].tolist()
        hh, ss, vv = self._hsv[y, x].tolist()

        # kleine hint: voor ranges tunen
        self.info_var.set(
            f"Pick @ ({x},{y})  RGB=({r},{g},{b})  HSV=({hh},{ss},{vv}) 🎯"
        )

if __name__ == "__main__":
    # kies je eigen defaults
    ui = ColourPickerUI(area_name="Bot_Area", bot_id=1, default_colour="purple")
    ui.mainloop()
