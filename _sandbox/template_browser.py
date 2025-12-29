import json
import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

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


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def write_json(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def color_score(template_rgb: np.ndarray, matched_rgb: np.ndarray) -> float:
    if matched_rgb.shape[:2] != template_rgb.shape[:2]:
        matched_rgb = cv2.resize(matched_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, matched_rgb)
    mae = float(np.mean(diff))
    return round(max(0.0, 100.0 - mae), 2)


def grab_region_rgb(box) -> np.ndarray:
    x1, y1, x2, y2 = box
    w, h = x2 - x1, y2 - y1
    return np.array(pyautogui.screenshot(region=(x1, y1, w, h)))  # RGB


def analyze_all_methods(template_path: Path, area_name: str, bot_id: int) -> list[dict]:
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
    shot_rgb = grab_region_rgb(box)
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
            kleur = color_score(tpl_rgb, patch)

        out.append({"method": method_name, "vorm": vorm, "kleur": kleur, "pt": {"x": x, "y": y}})

    out.sort(key=lambda d: (d["vorm"], d["kleur"]), reverse=True)
    return out


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Template Browser (quick test)")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.areas = load_areas()
        self.templates = self.scan_templates()

        self.template_var = tk.StringVar(value=self.templates[0] if self.templates else "")
        self.area_var = tk.StringVar(value=("FullScreen" if "FullScreen" in self.areas else (next(iter(self.areas), ""))))
        self.bot_var = tk.IntVar(value=1)

        self.preview_img = None

        self.build_ui()
        self.refresh_preview()

        self.bind("<Escape>", lambda e: self.destroy())

    def scan_templates(self):
        if not Path(IMAGES_DIR).exists():
            return []
        files = sorted([p.name for p in Path(IMAGES_DIR).glob("*.png")], key=str.lower)
        return files

    def build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky="nsw", padx=8, pady=8)

        ttk.Label(left, text="Templates").pack(anchor="w")

        self.listbox = tk.Listbox(left, width=35, height=28)
        self.listbox.pack(fill="y", expand=True)

        for t in self.templates:
            self.listbox.insert(tk.END, t)

        self.listbox.bind("<<ListboxSelect>>", self.on_select_template)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Refresh", command=self.on_refresh).pack(side="left")
        ttk.Button(btns, text="Analyze", command=self.on_analyze).pack(side="right")

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        self.preview_label = ttk.Label(right)
        self.preview_label.grid(row=0, column=0, sticky="n")

        controls = ttk.Frame(right)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 6))

        ttk.Label(controls, text="Area").grid(row=0, column=0, padx=(0, 6))
        self.area_cb = ttk.Combobox(controls, textvariable=self.area_var, values=sorted(self.areas.keys()), width=35)
        self.area_cb.grid(row=0, column=1, padx=(0, 12))

        ttk.Label(controls, text="Bot").grid(row=0, column=2, padx=(0, 6))
        bot_cb = ttk.Combobox(controls, textvariable=self.bot_var, values=[1, 2, 3, 4], width=5)
        bot_cb.grid(row=0, column=3)

        self.best_label = ttk.Label(right, text="Best: (nog niet geanalyseerd)", font=("Arial", 11, "bold"))
        self.best_label.grid(row=2, column=0, sticky="w", pady=(6, 4))

        self.results = tk.Listbox(right, height=16)
        self.results.grid(row=3, column=0, sticky="nsew")

        ttk.Label(right, text="Tip: verander area/bot en druk Analyze. Esc sluit.").grid(row=4, column=0, sticky="w", pady=(8, 0))

    def on_select_template(self, _evt=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        name = self.listbox.get(sel[0])
        self.template_var.set(name)
        self.refresh_preview()

    def refresh_preview(self):
        name = self.template_var.get()
        if not name:
            return
        p = Path(IMAGES_DIR) / name
        try:
            img = Image.open(p)
            img.thumbnail((520, 320))
            self.preview_img = ImageTk.PhotoImage(img)
            self.preview_label.configure(image=self.preview_img)
        except Exception:
            self.preview_label.configure(text="preview error")

    def on_refresh(self):
        self.areas = load_areas()
        self.area_cb.configure(values=sorted(self.areas.keys()))

        self.templates = self.scan_templates()
        self.listbox.delete(0, tk.END)
        for t in self.templates:
            self.listbox.insert(tk.END, t)

        if self.templates:
            self.template_var.set(self.templates[0])
            self.listbox.selection_set(0)
            self.refresh_preview()

    def on_analyze(self):
        name = self.template_var.get()
        area = self.area_var.get()
        bot = int(self.bot_var.get())

        if not name:
            return messagebox.showerror("Fout", "Geen template geselecteerd")
        if not area:
            return messagebox.showerror("Fout", "Geen area gekozen")

        p = Path(IMAGES_DIR) / name

        try:
            res = analyze_all_methods(p, area, bot)
        except Exception as e:
            return messagebox.showerror("Analyse error", str(e))

        self.results.delete(0, tk.END)
        best = res[0]
        self.best_label.configure(text=f"Best: {best['method']} | vorm={best['vorm']:.2f} | kleur={best['kleur']:.2f} | pt={best['pt']}")

        for r in res:
            self.results.insert(tk.END, f"{r['vorm']:6.2f}%  {r['kleur']:6.2f}%   {r['method']:<16} pt={r['pt']}")

        db = read_json(META_FILE)
        db[name] = {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "template": name,
            "area": area,
            "bot_id": bot,
            "best": best,
            "all": res,
        }
        write_json(META_FILE, db)

    # end class


if __name__ == "__main__":
    App().mainloop()
