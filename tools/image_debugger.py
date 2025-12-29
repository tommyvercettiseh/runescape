import sys
from pathlib import Path

# Zorg dat project-root in sys.path staat
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import os
import math
import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk

from core.paths import IMAGES_DIR, CONFIG_DIR
from core.bot_offsets import apply_offset, load_areas


METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

# ========== utils ==========

def _human_dt(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

def _resolve_template_path(image_name_or_path: str) -> Path:
    p = Path(image_name_or_path)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name_or_path

def _read_template_rgb_gray(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden/leesbaar: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return rgb, gray

def _color_score(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, patch_rgb)
    mae = float(np.mean(diff))
    return float(np.clip(100.0 - mae, 0.0, 100.0))

def _grab_region(box_xyxy):
    x1, y1, x2, y2 = box_xyxy
    w, h = x2 - x1, y2 - y1
    img = pyautogui.screenshot(region=(x1, y1, w, h))
    return np.array(img)  # RGB

def _scoremap_01(result: np.ndarray, method_name: str) -> np.ndarray:
    """
    Scoremap altijd 0..1 waarbij 1 = beste match.
    Dit voorkomt '100 overal' door raw ranges van non-normed methods.
    """
    norm = cv2.normalize(result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        norm = 1.0 - norm
    return norm

@dataclass
class TemplateRow:
    name: str
    path: str
    size_kb: int
    mtime: float


# ========== GUI ==========

class ImageDebugger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🧪 Image Debugger")
        self.geometry("1400x900")
        self.minsize(1100, 700)
        self.bind("<Escape>", lambda e: self.destroy())

        self.areas = {}
        self.templates: list[TemplateRow] = []
        self.preview_cache: dict[str, ImageTk.PhotoImage] = {}
        self.method_previews: dict[str, ImageTk.PhotoImage] = {}

        self.bot_id = tk.IntVar(value=1)
        self.area_var = tk.StringVar(value="")
        self.method_var = tk.StringVar(value="ALL")

        self.min_vorm = tk.DoubleVar(value=85.0)
        self.min_kleur = tk.DoubleVar(value=60.0)

        self._build_ui()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()

    # ---------- UI ----------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        top = ttk.Panedwindow(self, orient="horizontal")
        top.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        left = ttk.Frame(top)
        right = ttk.Frame(top)
        top.add(left, weight=3)
        top.add(right, weight=2)

        # LEFT: template list
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ttk.Label(left, text="Templates (assets/images)").grid(row=0, column=0, sticky="w")

        self.template_search = tk.StringVar()
        ent = ttk.Entry(left, textvariable=self.template_search)
        ent.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        ent.bind("<KeyRelease>", lambda e: self._refresh_template_tree())

        self.tree = ttk.Treeview(left, columns=("naam", "kb", "mtime"), show="headings", selectmode="browse")
        self.tree.heading("naam", text="Bestandsnaam")
        self.tree.heading("kb", text="KB")
        self.tree.heading("mtime", text="Gewijzigd")
        self.tree.column("naam", width=520, anchor="w")
        self.tree.column("kb", width=70, anchor="e")
        self.tree.column("mtime", width=150, anchor="center")
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._update_main_preview())

        sy = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sy.set)
        sy.grid(row=2, column=1, sticky="ns")

        btnrow = ttk.Frame(left)
        btnrow.grid(row=3, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(btnrow, text="📸 Crop screenshot", command=self._crop_screenshot).pack(side="left", padx=(0, 6))
        ttk.Button(btnrow, text="✏️ Rename", command=self._rename_template).pack(side="left", padx=(0, 6))
        ttk.Button(btnrow, text="🔁 Refresh", command=self._refresh_all).pack(side="left")

        # RIGHT: preview + controls + results
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(5, weight=1)

        self.preview_label = tk.Label(right)
        self.preview_label.grid(row=0, column=0, sticky="n", pady=(0, 4))

        self.preview_text = ttk.Label(right, text="Geen template geselecteerd")
        self.preview_text.grid(row=1, column=0, sticky="n", pady=(0, 10))

        # Controls
        controls = ttk.LabelFrame(right, text="Test settings")
        controls.grid(row=2, column=0, sticky="ew", padx=4, pady=6)
        controls.grid_columnconfigure(1, weight=1)

        # Bot selector
        botrow = ttk.Frame(controls)
        botrow.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(6, 4), padx=8)
        ttk.Label(botrow, text="Bot").pack(side="left")
        for i in (1, 2, 3, 4):
            ttk.Radiobutton(botrow, text=str(i), value=i, variable=self.bot_id).pack(side="left", padx=4)

        # Area dropdown
        ttk.Label(controls, text="Area").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.area_cb = ttk.Combobox(controls, textvariable=self.area_var, values=[], width=35)
        self.area_cb.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        # Method dropdown
        ttk.Label(controls, text="Methode").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        method_values = ["ALL"] + list(METHODS.keys())
        self.method_cb = ttk.Combobox(controls, textvariable=self.method_var, values=method_values, width=20)
        self.method_cb.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self.method_cb.set("ALL")

        # Thresholds
        thr = ttk.Frame(controls)
        thr.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 8))
        ttk.Label(thr, text="Min vorm").pack(side="left")
        ttk.Entry(thr, textvariable=self.min_vorm, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(thr, text="Min kleur").pack(side="left")
        ttk.Entry(thr, textvariable=self.min_kleur, width=6).pack(side="left", padx=6)

        action = ttk.Frame(right)
        action.grid(row=3, column=0, sticky="ew", padx=4, pady=(2, 6))
        ttk.Button(action, text="🔲 Toon area", command=self._show_area_overlay).pack(side="left", padx=(0, 6))
        ttk.Button(action, text="🔍 Analyseer", command=self._analyze).pack(side="left")

        # Results list
        ttk.Label(right, text="Resultaten (0..100, 100 = beste match in die methode)").grid(row=4, column=0, sticky="w", padx=6)
        self.results = tk.Listbox(right, height=7)
        self.results.grid(row=5, column=0, sticky="nsew", padx=6, pady=(2, 6))

        # Preview gallery (horiz)
        ttk.Label(right, text="Preview per methode").grid(row=6, column=0, sticky="w", padx=6)
        gal_container = ttk.Frame(right)
        gal_container.grid(row=7, column=0, sticky="nsew", padx=6, pady=(2, 6))
        right.grid_rowconfigure(7, weight=1)

        self.gal_canvas = tk.Canvas(gal_container, highlightthickness=0)
        sx = ttk.Scrollbar(gal_container, orient="horizontal", command=self.gal_canvas.xview)
        self.gal_canvas.configure(xscrollcommand=sx.set)
        self.gal_canvas.pack(side="top", fill="both", expand=True)
        sx.pack(side="bottom", fill="x")

        self.gal_inner = ttk.Frame(self.gal_canvas)
        self.gal_win = self.gal_canvas.create_window((0, 0), window=self.gal_inner, anchor="nw")
        self.gal_inner.bind("<Configure>", lambda e: self._resize_gallery())

    def _resize_gallery(self):
        self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all"))
        self.gal_canvas.itemconfig(self.gal_win, height=self.gal_inner.winfo_reqheight())

    # ---------- data ----------
    def _load_areas(self):
        try:
            self.areas = load_areas()
            names = sorted(self.areas.keys())
            self.area_cb["values"] = names
            if names and (self.area_var.get() not in names):
                self.area_var.set(names[0])
        except Exception as e:
            messagebox.showerror("Areas", str(e))
            self.areas = {}
            self.area_cb["values"] = []

    def _scan_templates(self):
        self.templates = []
        base = Path(IMAGES_DIR)
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)

        for p in base.glob("*.png"):
            try:
                st = p.stat()
                size_kb = max(1, math.ceil(st.st_size / 1024))
                self.templates.append(
                    TemplateRow(
                        name=p.name,
                        path=str(p),
                        size_kb=size_kb,
                        mtime=st.st_mtime,
                    )
                )
            except Exception:
                pass

        self.templates.sort(key=lambda r: r.mtime, reverse=True)

    def _refresh_template_tree(self):
        q = (self.template_search.get() or "").strip().lower()

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = self.templates
        if q:
            rows = [r for r in rows if q in r.name.lower()]

        for r in rows:
            self.tree.insert("", "end", iid=r.name, values=(r.name, r.size_kb, _human_dt(r.mtime)))

        if rows:
            cur = self.tree.selection()
            if not cur:
                self.tree.selection_set(rows[0].name)
                self.tree.see(rows[0].name)

    def _refresh_all(self):
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._update_main_preview()

    def _selected_template_name(self) -> str:
        sel = self.tree.selection()
        return sel[0] if sel else ""

    def _update_main_preview(self):
        name = self._selected_template_name()
        if not name:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Geen template geselecteerd")
            return

        try:
            p = _resolve_template_path(name)
            img = Image.open(p)
            img.thumbnail((380, 380))
            imgtk = ImageTk.PhotoImage(img)
            self.preview_cache["main"] = imgtk
            self.preview_label.configure(image=imgtk)
            self.preview_text.configure(text=name)
        except Exception:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Preview niet beschikbaar")

    # ---------- tools ----------
    def _show_area_overlay(self):
        area = self.area_var.get()
        if area not in self.areas:
            return messagebox.showerror("Area", "Selecteer een geldige area")

        try:
            box = apply_offset(self.areas[area], int(self.bot_id.get()))
            x1, y1, x2, y2 = box
            ov = tk.Toplevel(self)
            ov.attributes("-fullscreen", True)
            ov.attributes("-alpha", 0.25)
            ov.configure(bg="black")
            c = tk.Canvas(ov, bg="black")
            c.pack(fill="both", expand=True)
            c.create_rectangle(x1, y1, x2, y2, outline="red", width=3)
            c.create_text(x1 + 6, y1 - 14, text=f"{area} (bot {int(self.bot_id.get())})", anchor="nw", fill="red")
            c.bind("<Button-1>", lambda e: ov.destroy())
        except Exception as e:
            messagebox.showerror("Overlay", str(e))

    def _crop_screenshot(self):
        # fullscreen overlay, drag rectangle, save to assets/images
        self.withdraw()
        screen = pyautogui.screenshot()

        crop = tk.Toplevel(self)
        crop.attributes("-fullscreen", True)
        crop.attributes("-alpha", 0.30)
        crop.configure(bg="black")

        cv = tk.Canvas(crop, cursor="cross")
        cv.pack(fill="both", expand=True)

        coords = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

        def md(e):
            coords["x1"], coords["y1"] = e.x, e.y

        def mg(e):
            coords["x2"], coords["y2"] = e.x, e.y
            cv.delete("r")
            cv.create_rectangle(coords["x1"], coords["y1"], coords["x2"], coords["y2"], outline="red", width=2, tags="r")

        def mu(e):
            crop.destroy()
            self.deiconify()

            x1, y1 = min(coords["x1"], coords["x2"]), min(coords["y1"], coords["y2"])
            x2, y2 = max(coords["x1"], coords["x2"]), max(coords["y1"], coords["y2"])

            if (x2 - x1) < 5 or (y2 - y1) < 5:
                return

            region = screen.crop((x1, y1, x2, y2))
            fn = f"crop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            out = Path(IMAGES_DIR) / fn
            region.save(out)

            self._refresh_all()
            if self.tree.exists(fn):
                self.tree.selection_set(fn)
                self.tree.see(fn)
            messagebox.showinfo("✅ Opgeslagen", f"{fn}\n{out}")

        cv.bind("<ButtonPress-1>", md)
        cv.bind("<B1-Motion>", mg)
        cv.bind("<ButtonRelease-1>", mu)

    def _rename_template(self):
        cur = self._selected_template_name()
        if not cur:
            return messagebox.showerror("Rename", "Geen template geselecteerd")

        new = simpledialog.askstring("Rename", f"Nieuwe naam voor:\n{cur}", initialvalue=cur, parent=self)
        if not new:
            return

        if not new.lower().endswith(".png"):
            new += ".png"

        old_path = _resolve_template_path(cur)
        new_path = _resolve_template_path(new)
        if new_path.exists():
            return messagebox.showerror("Rename", "Bestand bestaat al")

        try:
            os.rename(old_path, new_path)
            self._refresh_all()
            if self.tree.exists(new):
                self.tree.selection_set(new)
                self.tree.see(new)
        except Exception as e:
            messagebox.showerror("Rename", str(e))

    # ---------- analysis ----------
    def _analyze(self):
        tpl_name = self._selected_template_name()
        if not tpl_name:
            return messagebox.showerror("Analyse", "Selecteer een template")

        area = self.area_var.get()
        if area not in self.areas:
            return messagebox.showerror("Analyse", "Selecteer een geldige area")

        try:
            min_v = float(self.min_vorm.get())
            min_c = float(self.min_kleur.get())
        except Exception:
            return messagebox.showerror("Analyse", "Ongeldige thresholds")

        tpl_path = _resolve_template_path(tpl_name)
        try:
            tpl_rgb, tpl_gray = _read_template_rgb_gray(tpl_path)
        except Exception as e:
            return messagebox.showerror("Template", str(e))

        box = apply_offset(self.areas[area], int(self.bot_id.get()))
        shot_rgb = _grab_region(box)
        shot_gray = cv2.cvtColor(shot_rgb, cv2.COLOR_RGB2GRAY)

        th, tw = tpl_gray.shape[:2]
        if shot_gray.shape[0] < th or shot_gray.shape[1] < tw:
            return messagebox.showerror("Analyse", "Template is groter dan je area")

        wanted = self.method_var.get()
        method_list = list(METHODS.keys()) if wanted == "ALL" else [wanted]

        results = []
        self.method_previews.clear()

        for mname in method_list:
            meth = METHODS[mname]
            res = cv2.matchTemplate(shot_gray, tpl_gray, meth)
            scores = _scoremap_01(res, mname)

            _, best, _, best_loc = cv2.minMaxLoc(scores)
            vorm = float(np.clip(best * 100.0, 0.0, 100.0))

            x, y = int(best_loc[0]), int(best_loc[1])
            patch = shot_rgb[y : y + th, x : x + tw]
            kleur = _color_score(tpl_rgb, patch) if patch.shape[:2] == tpl_rgb.shape[:2] else 0.0

            ok = (vorm >= min_v) and (kleur >= min_c)

            results.append((mname, round(vorm, 2), round(kleur, 2), ok, (x, y)))

            # build preview
            vis = shot_rgb.copy()
            col = (0, 255, 0) if ok else (255, 0, 0)
            cv2.rectangle(vis, (x, y), (x + tw, y + th), col, 2)

            prev = Image.fromarray(vis)
            prev.thumbnail((330, 220))
            self.method_previews[mname] = ImageTk.PhotoImage(prev)

        results.sort(key=lambda r: r[1], reverse=True)

        self.results.delete(0, tk.END)
        for mname, vorm, kleur, ok, loc in results:
            mark = "✅" if ok else "❌"
            self.results.insert(tk.END, f"{mark} {vorm:6.2f}% vorm  🎨 {kleur:6.2f}%  {mname}  loc={loc}")

        for w in self.gal_inner.winfo_children():
            w.destroy()

        for mname, _, _, _, _ in results:
            fr = ttk.Frame(self.gal_inner)
            ttk.Label(fr, text=mname, font=("Arial", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 2))
            img = self.method_previews.get(mname)
            lb = ttk.Label(fr, image=img)
            lb.image = img
            lb.pack(padx=6, pady=(0, 6))
            fr.pack(side="left", padx=6, pady=6)

        self._resize_gallery()


if __name__ == "__main__":
    app = ImageDebugger()
    app.mainloop()
