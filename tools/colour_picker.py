# tools/colour_palette_picker.py
# Area -> Screenshot -> Kleurpalette -> Klik kleur -> Grijs-out preview + HEX + HSV 🎨🧪
#
# Vereist: pyautogui, opencv-python, numpy, tkinter (standaard)
#
# Flow
# 1) Kies area + bot_id
# 2) Klik "📸 Screenshot"
# 3) Klik kleur-tegel
# 4) Bekijk preview "FILTER" (alles grijs behalve match)
# 5) Lees HEX + HSV, copy met knop

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
import pyautogui

# ============================================================
# BOOTSTRAP repo root
# ============================================================
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bot_offsets import load_areas, apply_offset


# ============================================================
# Helpers
# ============================================================
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def rgb_to_hex(rgb):
    r, g, b = [int(x) for x in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"

def rgb_to_hsv(rgb):
    arr = np.uint8([[list(rgb)]])
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)[0, 0]
    return int(hsv[0]), int(hsv[1]), int(hsv[2])

def grab_area_rgb(area_name, bot_id, areas):
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 2 or h <= 2:
        return None

    shot = np.array(pyautogui.screenshot(region=(x1, y1, w, h)))  # RGB
    return shot

def gray_out_non_mask(rgb_img, mask):
    bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    out = gray3.copy()
    out[mask > 0] = bgr[mask > 0]

    # klein groen accent
    out = out.astype(np.int16)
    out[:, :, 1] = np.clip(out[:, :, 1] + (mask > 0).astype(np.int16) * 70, 0, 255)
    return out.astype(np.uint8)

def palette_kmeans(rgb_img, k=18, sample_max=12000):
    """
    Return: centers_rgb (k,3) als ints, plus counts per cluster
    """
    small = rgb_img
    h, w = small.shape[:2]
    scale = 1.0
    if max(h, w) > 640:
        scale = 640 / float(max(h, w))
        small = cv2.resize(small, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    pixels = small.reshape(-1, 3)
    if len(pixels) > sample_max:
        idx = np.random.choice(len(pixels), size=sample_max, replace=False)
        pixels = pixels[idx]

    Z = np.float32(pixels)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 18, 1.0)
    flags = cv2.KMEANS_PP_CENTERS
    compactness, labels, centers = cv2.kmeans(Z, k, None, criteria, 3, flags)

    labels = labels.flatten()
    centers = np.clip(centers, 0, 255).astype(np.uint8)

    counts = np.bincount(labels, minlength=k)
    order = np.argsort(-counts)

    centers = centers[order]
    counts = counts[order]
    return centers, counts

def mask_by_hsv_center(rgb_img, center_rgb, tol_h, tol_s, tol_v):
    hsv_img = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
    h, s, v = rgb_to_hsv(center_rgb)

    lo_h = h - tol_h
    hi_h = h + tol_h
    lo_s = clamp(s - tol_s, 0, 255)
    hi_s = clamp(s + tol_s, 0, 255)
    lo_v = clamp(v - tol_v, 0, 255)
    hi_v = clamp(v + tol_v, 0, 255)

    if lo_h < 0:
        # wrap 0
        m1 = cv2.inRange(hsv_img, (0, lo_s, lo_v), (hi_h, hi_s, hi_v))
        m2 = cv2.inRange(hsv_img, (179 + lo_h, lo_s, lo_v), (179, hi_s, hi_v))
        return cv2.bitwise_or(m1, m2)

    if hi_h > 179:
        # wrap 179
        m1 = cv2.inRange(hsv_img, (lo_h, lo_s, lo_v), (179, hi_s, hi_v))
        m2 = cv2.inRange(hsv_img, (0, lo_s, lo_v), (hi_h - 179, hi_s, hi_v))
        return cv2.bitwise_or(m1, m2)

    return cv2.inRange(hsv_img, (lo_h, lo_s, lo_v), (hi_h, hi_s, hi_v))


# ============================================================
# App
# ============================================================
class App:
    def __init__(self):
        self.areas = load_areas()
        self.area_names = sorted(list(self.areas.keys()))

        self.shot_rgb = None
        self.palette_centers = None
        self.palette_counts = None
        self.selected_center = None

        self.root = tk.Tk()
        self.root.title("Colour Palette Picker 🎨")
        self.root.geometry("760x520")
        self.root.attributes("-topmost", True)

        self.area_var = tk.StringVar(value=self.area_names[0] if self.area_names else "Bot_Area")
        self.bot_id_var = tk.IntVar(value=1)

        self.k_var = tk.IntVar(value=18)
        self.tol_h = tk.IntVar(value=8)
        self.tol_s = tk.IntVar(value=60)
        self.tol_v = tk.IntVar(value=60)

        self.hex_var = tk.StringVar(value="HEX: ")
        self.hsv_var = tk.StringVar(value="HSV: ")
        self.info_var = tk.StringVar(value="1) Kies area  2) Klik Screenshot  3) Klik een kleur-tegel 🙂")

        self.build_ui()

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="x")

        ttk.Label(top, text="Area").pack(side="left")
        if self.area_names:
            cmb = ttk.Combobox(top, textvariable=self.area_var, values=self.area_names, width=28, state="readonly")
            cmb.pack(side="left", padx=8)
        else:
            ttk.Entry(top, textvariable=self.area_var, width=30).pack(side="left", padx=8)

        ttk.Label(top, text="bot_id").pack(side="left")
        ttk.Spinbox(top, from_=1, to=8, textvariable=self.bot_id_var, width=5).pack(side="left", padx=8)

        ttk.Button(top, text="📸 Screenshot", command=self.on_screenshot).pack(side="left", padx=8)

        ttk.Label(top, text="K kleuren").pack(side="left")
        ttk.Spinbox(top, from_=6, to=40, textvariable=self.k_var, width=5).pack(side="left", padx=6)
        ttk.Button(top, text="🎛️ Rebuild palette", command=self.rebuild_palette).pack(side="left")

        mid = ttk.Frame(outer)
        mid.pack(fill="x", pady=(12, 8))

        def slider_row(label, var, fr, to):
            row = ttk.Frame(mid)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=10).pack(side="left")
            s = ttk.Scale(row, from_=fr, to=to, orient="horizontal", command=lambda _=None: self.apply_filter())
            s.pack(side="left", fill="x", expand=True, padx=8)
            s.set(var.get())
            # sync back to var
            def on_release(_):
                var.set(int(float(s.get())))
                self.apply_filter()
            s.bind("<ButtonRelease-1>", on_release)
            return s

        slider_row("tol_h", self.tol_h, 1, 30)
        slider_row("tol_s", self.tol_s, 0, 180)
        slider_row("tol_v", self.tol_v, 0, 180)

        meta = ttk.Frame(outer)
        meta.pack(fill="x", pady=(8, 8))
        ttk.Label(meta, textvariable=self.hex_var, font=("Consolas", 12)).pack(anchor="w")
        ttk.Label(meta, textvariable=self.hsv_var, font=("Consolas", 12)).pack(anchor="w")

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="📋 Copy HEX", command=self.copy_hex).pack(side="left")
        ttk.Button(btns, text="📋 Copy HSV", command=self.copy_hsv).pack(side="left", padx=8)

        ttk.Label(outer, textvariable=self.info_var).pack(anchor="w")

        self.palette_frame = ttk.LabelFrame(outer, text="Kleuren gevonden (klik een tegel)")
        self.palette_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.palette_canvas = tk.Canvas(self.palette_frame, highlightthickness=0)
        self.palette_canvas.pack(fill="both", expand=True)

    def on_screenshot(self):
        area = self.area_var.get().strip()
        bot_id = int(self.bot_id_var.get())

        shot = grab_area_rgb(area, bot_id, self.areas)
        if shot is None:
            self.info_var.set("Screenshot faalde 😅 check area coords")
            return

        self.shot_rgb = shot
        cv2.imshow("SCREENSHOT (original)", cv2.cvtColor(self.shot_rgb, cv2.COLOR_RGB2BGR))
        cv2.waitKey(1)

        self.info_var.set("Screenshot klaar ✅ palette wordt gebouwd…")
        self.rebuild_palette()

    def rebuild_palette(self):
        if self.shot_rgb is None:
            self.info_var.set("Eerst Screenshot klikken 🙂")
            return

        k = int(self.k_var.get())
        centers, counts = palette_kmeans(self.shot_rgb, k=k)
        self.palette_centers = centers
        self.palette_counts = counts
        self.selected_center = None

        self.render_palette_tiles()
        self.info_var.set("Klik een kleur-tegel 👇")

    def render_palette_tiles(self):
        self.palette_canvas.delete("all")
        if self.palette_centers is None:
            return

        tiles_per_row = 6
        tile = 80
        pad = 10

        for i, rgb in enumerate(self.palette_centers):
            r, g, b = [int(x) for x in rgb]
            hx = rgb_to_hex((r, g, b))

            row = i // tiles_per_row
            col = i % tiles_per_row
            x1 = pad + col * (tile + pad)
            y1 = pad + row * (tile + pad)
            x2 = x1 + tile
            y2 = y1 + tile

            rect = self.palette_canvas.create_rectangle(x1, y1, x2, y2, fill=hx, outline="#111", width=2)
            txt = self.palette_canvas.create_text(x1 + 6, y2 - 10, text=f"{i+1}", anchor="w", fill="white")

            # click binding
            def make_cb(idx):
                return lambda _e=None: self.on_pick_tile(idx)
            self.palette_canvas.tag_bind(rect, "<Button-1>", make_cb(i))
            self.palette_canvas.tag_bind(txt, "<Button-1>", make_cb(i))

        # resize scroll area
        rows = (len(self.palette_centers) + tiles_per_row - 1) // tiles_per_row
        h = pad + rows * (tile + pad) + pad
        w = pad + tiles_per_row * (tile + pad) + pad
        self.palette_canvas.config(scrollregion=(0, 0, w, h))

    def on_pick_tile(self, idx):
        if self.palette_centers is None or self.shot_rgb is None:
            return

        self.selected_center = tuple(int(x) for x in self.palette_centers[idx])
        hx = rgb_to_hex(self.selected_center)
        hsv = rgb_to_hsv(self.selected_center)

        self.hex_var.set(f"HEX: {hx}")
        self.hsv_var.set(f"HSV: {hsv}")

        self.apply_filter()

    def apply_filter(self):
        if self.shot_rgb is None or self.selected_center is None:
            return

        mask = mask_by_hsv_center(
            self.shot_rgb,
            self.selected_center,
            tol_h=int(self.tol_h.get()),
            tol_s=int(self.tol_s.get()),
            tol_v=int(self.tol_v.get()),
        )

        filt = gray_out_non_mask(self.shot_rgb, mask)

        cv2.imshow("FILTER (grijs behalve match)", filt)
        cv2.imshow("MASK", mask)
        cv2.waitKey(1)

        nonzero = int(cv2.countNonZero(mask))
        self.info_var.set(f"Match pixels: {nonzero}  tweak tol_h/tol_s/tol_v tot het klopt ✅")

    def copy_hex(self):
        val = self.hex_var.get().replace("HEX: ", "").strip()
        if not val:
            self.info_var.set("Klik eerst een kleur-tegel 🙂")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.root.update()
        self.info_var.set(f"HEX gekopieerd ✅ {val}")

    def copy_hsv(self):
        val = self.hsv_var.get().replace("HSV: ", "").strip()
        if not val:
            self.info_var.set("Klik eerst een kleur-tegel 🙂")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.root.update()
        self.info_var.set(f"HSV gekopieerd ✅ {val}")

    def run(self):
        self.root.mainloop()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass


if __name__ == "__main__":
    App().run()
