# =========================
# START: BOOTSTRAP / IMPORTS
# =========================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import os
import math
import json
from dataclasses import dataclass
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
# =========================
# END: BOOTSTRAP / IMPORTS
# =========================


# ==================================
# START: CONFIG (JOUW KEUZES HIER)
# ==================================
# Optie A: alles in 1 bestand
META_FILE = Path(CONFIG_DIR) / "templates_meta.json"

# Optie B: 1 json per template (overzichtelijker, meer files)
USE_PER_TEMPLATE_FILES = False
PER_TEMPLATE_DIR = Path(CONFIG_DIR) / "templates"

# Tip: ik zou standaard A doen, en B alleen als je echt veel templates hebt
# ==================================
# END: CONFIG
# ==================================


# =========================
# START: UTILITIES
# =========================
def ensure_directories():
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    if USE_PER_TEMPLATE_FILES:
        PER_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def human_datetime(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def resolve_template_path(image_name_or_path: str) -> Path:
    path = Path(image_name_or_path)
    return path if path.is_absolute() else Path(IMAGES_DIR) / image_name_or_path


def read_template_rgb_gray(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden/leesbaar: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return rgb, gray


def grab_region_rgb(box_xyxy):
    x1, y1, x2, y2 = box_xyxy
    width, height = x2 - x1, y2 - y1
    img = pyautogui.screenshot(region=(x1, y1, width, height))
    return np.array(img)  # RGB


def color_score_0_100(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, patch_rgb)
    mae = float(np.mean(diff))
    return float(np.clip(100.0 - mae, 0.0, 100.0))


def scoremap_0_1(match_result: np.ndarray, method_name: str) -> np.ndarray:
    normalized = cv2.normalize(match_result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        normalized = 1.0 - normalized
    return normalized


def find_all_matches_with_nms(
    scores_0_1: np.ndarray,
    template_width: int,
    template_height: int,
    minimum_score_0_1: float,
    maximum_hits: int = 50,
    nms_radius_pixels: int | None = None,
):
    if nms_radius_pixels is None:
        nms_radius_pixels = max(5, int(min(template_width, template_height) * 0.50))

    ys, xs = np.where(scores_0_1 >= float(minimum_score_0_1))
    if len(xs) == 0:
        return []

    values = scores_0_1[ys, xs]
    order = np.argsort(values)[::-1]

    picked = []
    for index in order:
        x = int(xs[index])
        y = int(ys[index])
        score = float(values[index])

        too_close = False
        for px, py, _ in picked:
            dx = x - px
            dy = y - py
            if (dx * dx + dy * dy) <= (nms_radius_pixels * nms_radius_pixels):
                too_close = True
                break

        if too_close:
            continue

        picked.append((x, y, score))
        if len(picked) >= int(maximum_hits):
            break

    return picked
# =========================
# END: UTILITIES
# =========================


# =======================================
# START: METADATA IO (JSON OPSLAAN/LADEN)
# =======================================
def _safe_read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _template_meta_path(template_name: str) -> Path:
    stem = Path(template_name).stem
    return PER_TEMPLATE_DIR / f"{stem}.json"


def load_all_metadata() -> dict:
    if USE_PER_TEMPLATE_FILES:
        PER_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        meta = {}
        for p in PER_TEMPLATE_DIR.glob("*.json"):
            d = _safe_read_json(p)
            name = d.get("template")
            if name:
                meta[str(name)] = d
        return meta

    return _safe_read_json(META_FILE)


def save_template_metadata(template_name: str, settings_dict: dict):
    if USE_PER_TEMPLATE_FILES:
        payload = {"template": template_name, **settings_dict}
        _safe_write_json(_template_meta_path(template_name), payload)
        return

    meta = _safe_read_json(META_FILE)
    meta[template_name] = settings_dict
    _safe_write_json(META_FILE, meta)
# =======================================
# END: METADATA IO
# =======================================


# =========================
# START: DATA MODELS
# =========================
@dataclass
class TemplateRow:
    name: str
    path: str
    size_kb: int
    mtime: float


@dataclass
class TemplateSettings:
    method: str = "ALL"
    min_shape: float = 85.0
    min_color: float = 60.0

    @staticmethod
    def from_dict(d: dict):
        return TemplateSettings(
            method=str(d.get("method", "ALL")),
            min_shape=float(d.get("min_shape", 85.0)),
            min_color=float(d.get("min_color", 60.0)),
        )

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "min_shape": self.min_shape,
            "min_color": self.min_color,
        }
# =========================
# END: DATA MODELS
# =========================


# =========================
# START: GUI APP
# =========================
class ImageDebugger(tk.Tk):
    def __init__(self):
        super().__init__()
        ensure_directories()

        self.title("🧪 Image Debugger")
        self.geometry("1450x900")
        self.minsize(1150, 720)
        self.bind("<Escape>", lambda e: self.destroy())

        self.areas = {}
        self.templates: list[TemplateRow] = []

        self.preview_cache: dict[str, ImageTk.PhotoImage] = {}
        self.method_previews: dict[str, ImageTk.PhotoImage] = {}

        self.bot_id = tk.IntVar(value=1)
        self.area_var = tk.StringVar(value="")
        self.method_var = tk.StringVar(value="ALL")

        self.minimum_shape_score = tk.DoubleVar(value=85.0)
        self.minimum_color_score = tk.DoubleVar(value=60.0)

        # Dit zijn debug knobs, niet opslaan in JSON
        self.maximum_hits = tk.IntVar(value=30)
        self.nms_radius = tk.IntVar(value=0)

        self.template_metadata = load_all_metadata()

        self._build_ui()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._load_selected_template_settings_into_ui()

    # -------------------------
    # START: UI BUILD
    # -------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        top = ttk.Panedwindow(self, orient="horizontal")
        top.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        left = ttk.Frame(top)
        right = ttk.Frame(top)
        top.add(left, weight=3)
        top.add(right, weight=2)

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ttk.Label(left, text="Templates (assets/images)").grid(row=0, column=0, sticky="w")

        self.template_search = tk.StringVar()
        entry = ttk.Entry(left, textvariable=self.template_search)
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        entry.bind("<KeyRelease>", lambda e: self._refresh_template_tree())

        self.tree = ttk.Treeview(left, columns=("name", "kb", "modified"), show="headings", selectmode="browse")
        self.tree.heading("name", text="Bestandsnaam")
        self.tree.heading("kb", text="KB")
        self.tree.heading("modified", text="Gewijzigd")

        self.tree.column("name", width=560, anchor="w")
        self.tree.column("kb", width=70, anchor="e")
        self.tree.column("modified", width=150, anchor="center")

        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_template_selected())

        scrollbar_y = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        scrollbar_y.grid(row=2, column=1, sticky="ns")

        buttons = ttk.Frame(left)
        buttons.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(buttons, text="📸 Crop + Resize", command=self._crop_and_resize_template).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="💾 Save preset", command=self._save_current_template_settings).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="✏️ Rename", command=self._rename_template).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="🔁 Refresh", command=self._refresh_all).pack(side="left")

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(6, weight=1)

        self.preview_label = tk.Label(right)
        self.preview_label.grid(row=0, column=0, sticky="n", pady=(0, 4))

        self.preview_text = ttk.Label(right, text="Geen template geselecteerd")
        self.preview_text.grid(row=1, column=0, sticky="n", pady=(0, 10))

        controls = ttk.LabelFrame(right, text="Test settings")
        controls.grid(row=2, column=0, sticky="ew", padx=4, pady=6)
        controls.grid_columnconfigure(1, weight=1)

        botrow = ttk.Frame(controls)
        botrow.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(6, 4), padx=8)
        ttk.Label(botrow, text="Bot").pack(side="left")
        for i in (1, 2, 3, 4):
            ttk.Radiobutton(botrow, text=str(i), value=i, variable=self.bot_id).pack(side="left", padx=4)

        ttk.Label(controls, text="Area").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.area_cb = ttk.Combobox(controls, textvariable=self.area_var, values=[], width=35)
        self.area_cb.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        ttk.Label(controls, text="Methode").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        method_values = ["ALL"] + list(METHODS.keys())
        self.method_cb = ttk.Combobox(controls, textvariable=self.method_var, values=method_values, width=20)
        self.method_cb.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self.method_cb.set("ALL")

        threshold_row = ttk.Frame(controls)
        threshold_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 2))
        ttk.Label(threshold_row, text="Min shape").pack(side="left")
        ttk.Entry(threshold_row, textvariable=self.minimum_shape_score, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(threshold_row, text="Min color").pack(side="left")
        ttk.Entry(threshold_row, textvariable=self.minimum_color_score, width=6).pack(side="left", padx=6)

        hits_row = ttk.Frame(controls)
        hits_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 8))
        ttk.Label(hits_row, text="Max hits (debug)").pack(side="left")
        ttk.Entry(hits_row, textvariable=self.maximum_hits, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(hits_row, text="NMS radius (0=auto)").pack(side="left")
        ttk.Entry(hits_row, textvariable=self.nms_radius, width=6).pack(side="left", padx=6)

        action = ttk.Frame(right)
        action.grid(row=3, column=0, sticky="ew", padx=4, pady=(2, 6))
        ttk.Button(action, text="🔲 Toon area", command=self._show_area_overlay).pack(side="left", padx=(0, 6))
        ttk.Button(action, text="🔍 Analyze", command=self._analyze).pack(side="left")

        ttk.Label(right, text="Resultaten (per methode)").grid(row=4, column=0, sticky="w", padx=6)
        self.results = tk.Listbox(right, height=8)
        self.results.grid(row=5, column=0, sticky="nsew", padx=6, pady=(2, 6))

        ttk.Label(right, text="Preview per methode (rectangles)").grid(row=6, column=0, sticky="w", padx=6)
        gal_container = ttk.Frame(right)
        gal_container.grid(row=7, column=0, sticky="nsew", padx=6, pady=(2, 6))
        right.grid_rowconfigure(7, weight=1)

        self.gal_canvas = tk.Canvas(gal_container, highlightthickness=0)
        scrollbar_x = ttk.Scrollbar(gal_container, orient="horizontal", command=self.gal_canvas.xview)
        self.gal_canvas.configure(xscrollcommand=scrollbar_x.set)

        self.gal_canvas.pack(side="top", fill="both", expand=True)
        scrollbar_x.pack(side="bottom", fill="x")

        self.gal_inner = ttk.Frame(self.gal_canvas)
        self.gal_win = self.gal_canvas.create_window((0, 0), window=self.gal_inner, anchor="nw")
        self.gal_inner.bind("<Configure>", lambda e: self._resize_gallery())

    def _resize_gallery(self):
        self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all"))
        self.gal_canvas.itemconfig(self.gal_win, height=self.gal_inner.winfo_reqheight())
    # -------------------------
    # END: UI BUILD
    # -------------------------

    # -------------------------
    # START: DATA LOAD
    # -------------------------
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
        base.mkdir(parents=True, exist_ok=True)

        for path in base.glob("*.png"):
            try:
                st = path.stat()
                size_kb = max(1, math.ceil(st.st_size / 1024))
                self.templates.append(TemplateRow(name=path.name, path=str(path), size_kb=size_kb, mtime=st.st_mtime))
            except Exception:
                pass

        self.templates.sort(key=lambda r: r.mtime, reverse=True)

    def _refresh_template_tree(self):
        query = (self.template_search.get() or "").strip().lower()

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = self.templates
        if query:
            rows = [r for r in rows if query in r.name.lower()]

        for r in rows:
            self.tree.insert("", "end", iid=r.name, values=(r.name, r.size_kb, human_datetime(r.mtime)))

        if rows:
            current = self.tree.selection()
            if not current:
                self.tree.selection_set(rows[0].name)
                self.tree.see(rows[0].name)

    def _refresh_all(self):
        self.template_metadata = load_all_metadata()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._update_main_preview()
        self._load_selected_template_settings_into_ui()
    # -------------------------
    # END: DATA LOAD
    # -------------------------

    # -------------------------
    # START: TEMPLATE SELECT + PREVIEW
    # -------------------------
    def _selected_template_name(self) -> str:
        sel = self.tree.selection()
        return sel[0] if sel else ""

    def _on_template_selected(self):
        self._update_main_preview()
        self._load_selected_template_settings_into_ui()

    def _update_main_preview(self):
        name = self._selected_template_name()
        if not name:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Geen template geselecteerd")
            return

        try:
            path = resolve_template_path(name)
            img = Image.open(path)
            img.thumbnail((330, 330))  # FIX: moet 2 waarden zijn
            imgtk = ImageTk.PhotoImage(img)
            self.preview_cache["main"] = imgtk
            self.preview_label.configure(image=imgtk)
            self.preview_text.configure(text=name)
        except Exception:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Preview niet beschikbaar")
    # -------------------------
    # END: TEMPLATE SELECT + PREVIEW
    # -------------------------

    # -------------------------
    # START: SETTINGS UI ↔ JSON
    # -------------------------
    def _get_current_template_settings_from_ui(self) -> TemplateSettings:
        return TemplateSettings(
            method=str(self.method_var.get() or "ALL"),
            min_shape=float(self.minimum_shape_score.get()),
            min_color=float(self.minimum_color_score.get()),
        )

    def _load_selected_template_settings_into_ui(self):
        template_name = self._selected_template_name()
        if not template_name:
            return

        raw = self.template_metadata.get(template_name, {})
        settings = TemplateSettings.from_dict(raw)

        self.method_var.set(settings.method)
        self.minimum_shape_score.set(settings.min_shape)
        self.minimum_color_score.set(settings.min_color)

    def _save_current_template_settings(self):
        template_name = self._selected_template_name()
        if not template_name:
            return messagebox.showerror("Preset", "Selecteer eerst een template")

        settings = self._get_current_template_settings_from_ui()
        save_template_metadata(template_name, settings.to_dict())

        # opnieuw laden zodat UI altijd klopt
        self.template_metadata = load_all_metadata()
        messagebox.showinfo("✅ Preset opgeslagen", f"{template_name}\n→ {META_FILE}")

    # -------------------------
    # END: SETTINGS UI ↔ JSON
    # -------------------------

    # -------------------------
    # START: TOOLS (OVERLAY, CROP, RENAME)
    # -------------------------
    def _show_area_overlay(self):
        area = self.area_var.get()
        if area not in self.areas:
            return messagebox.showerror("Area", "Selecteer een geldige area")

        try:
            box = apply_offset(self.areas[area], int(self.bot_id.get()))
            x1, y1, x2, y2 = box

            overlay = tk.Toplevel(self)
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.25)
            overlay.configure(bg="black")

            canvas = tk.Canvas(overlay, bg="black")
            canvas.pack(fill="both", expand=True)
            canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3)
            canvas.create_text(x1 + 6, y1 - 14, text=f"{area} (bot {int(self.bot_id.get())})", anchor="nw", fill="red")
            canvas.bind("<Button-1>", lambda e: overlay.destroy())
        except Exception as e:
            messagebox.showerror("Overlay", str(e))

    def _crop_and_resize_template(self):
        self.withdraw()
        screen = pyautogui.screenshot()

        crop_window = tk.Toplevel(self)
        crop_window.attributes("-fullscreen", True)
        crop_window.attributes("-alpha", 0.30)
        crop_window.configure(bg="black")

        canvas = tk.Canvas(crop_window, cursor="cross")
        canvas.pack(fill="both", expand=True)

        coords = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}

        def on_mouse_down(e):
            coords["x1"], coords["y1"] = e.x, e.y

        def on_mouse_drag(e):
            coords["x2"], coords["y2"] = e.x, e.y
            canvas.delete("rect")
            canvas.create_rectangle(coords["x1"], coords["y1"], coords["x2"], coords["y2"], outline="red", width=2, tags="rect")

        def on_mouse_up(e):
            crop_window.destroy()
            self.deiconify()

            x1 = min(coords["x1"], coords["x2"])
            y1 = min(coords["y1"], coords["y2"])
            x2 = max(coords["x1"], coords["x2"])
            y2 = max(coords["y1"], coords["y2"])

            if (x2 - x1) < 5 or (y2 - y1) < 5:
                return

            region = screen.crop((x1, y1, x2, y2))

            new_name = simpledialog.askstring(
                "Bestandsnaam",
                "Naam voor template (zonder .png mag ook):",
                initialvalue=f"crop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                parent=self,
            )
            if not new_name:
                return

            if not new_name.lower().endswith(".png"):
                new_name += ".png"

            resize_choice = messagebox.askyesno("Resize", "Wil je deze crop resizen?")
            if resize_choice:
                width = simpledialog.askinteger("Resize", "Nieuwe breedte (px):", initialvalue=region.size[0], parent=self)
                height = simpledialog.askinteger("Resize", "Nieuwe hoogte (px):", initialvalue=region.size[1], parent=self)
                if width and height and width > 0 and height > 0:
                    region = region.resize((width, height), Image.Resampling.LANCZOS)

            out_path = Path(IMAGES_DIR) / new_name
            region.save(out_path)

            # Default settings opslaan als er nog niks is
            if new_name not in self.template_metadata:
                save_template_metadata(new_name, TemplateSettings().to_dict())

            self._refresh_all()
            if self.tree.exists(new_name):
                self.tree.selection_set(new_name)
                self.tree.see(new_name)

            messagebox.showinfo("✅ Opgeslagen", f"{new_name}\n{out_path}")

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

    def _rename_template(self):
        current = self._selected_template_name()
        if not current:
            return messagebox.showerror("Rename", "Geen template geselecteerd")

        new = simpledialog.askstring("Rename", f"Nieuwe naam voor:\n{current}", initialvalue=current, parent=self)
        if not new:
            return

        if not new.lower().endswith(".png"):
            new += ".png"

        old_path = resolve_template_path(current)
        new_path = resolve_template_path(new)
        if new_path.exists():
            return messagebox.showerror("Rename", "Bestand bestaat al")

        try:
            os.rename(old_path, new_path)

            # Metadata meeverhuizen
            old_meta = self.template_metadata.get(current)
            if old_meta:
                save_template_metadata(new, TemplateSettings.from_dict(old_meta).to_dict())

                # oude verwijderen bij single file
                if not USE_PER_TEMPLATE_FILES:
                    meta = _safe_read_json(META_FILE)
                    if current in meta:
                        meta.pop(current, None)
                        _safe_write_json(META_FILE, meta)
                else:
                    p = _template_meta_path(current)
                    if p.exists():
                        try:
                            p.unlink()
                        except Exception:
                            pass

            self._refresh_all()
            if self.tree.exists(new):
                self.tree.selection_set(new)
                self.tree.see(new)
        except Exception as e:
            messagebox.showerror("Rename", str(e))
    # -------------------------
    # END: TOOLS
    # -------------------------

    # -------------------------
    # START: TEMPLATE MATCHING (KERN)
    # -------------------------
    def _analyze(self):
        template_name = self._selected_template_name()
        if not template_name:
            return messagebox.showerror("Analyze", "Selecteer een template")

        area_name = self.area_var.get()
        if area_name not in self.areas:
            return messagebox.showerror("Analyze", "Selecteer een geldige area")

        try:
            minimum_shape = float(self.minimum_shape_score.get())
            minimum_color = float(self.minimum_color_score.get())
            max_hits = int(self.maximum_hits.get())
            nms_radius = int(self.nms_radius.get())
        except Exception:
            return messagebox.showerror("Analyze", "Ongeldige thresholds")

        template_path = resolve_template_path(template_name)
        try:
            template_rgb, template_gray = read_template_rgb_gray(template_path)
        except Exception as e:
            return messagebox.showerror("Template", str(e))

        box = apply_offset(self.areas[area_name], int(self.bot_id.get()))
        screenshot_rgb = grab_region_rgb(box)
        screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)

        template_height, template_width = template_gray.shape[:2]
        if screenshot_gray.shape[0] < template_height or screenshot_gray.shape[1] < template_width:
            return messagebox.showerror("Analyze", "Template is groter dan je area")

        selected_method = self.method_var.get()
        method_names = list(METHODS.keys()) if selected_method == "ALL" else [selected_method]

        minimum_score_0_1 = float(minimum_shape) / 100.0
        nms_radius_pixels = None if nms_radius == 0 else nms_radius

        self.results.delete(0, tk.END)
        self.method_previews.clear()
        gallery_cards = []

        for method_name in method_names:
            method = METHODS[method_name]

            match_result = cv2.matchTemplate(screenshot_gray, template_gray, method)
            scores_0_1 = scoremap_0_1(match_result, method_name)

            hits = find_all_matches_with_nms(
                scores_0_1=scores_0_1,
                template_width=template_width,
                template_height=template_height,
                minimum_score_0_1=minimum_score_0_1,
                maximum_hits=max_hits,
                nms_radius_pixels=nms_radius_pixels,
            )

            visual = screenshot_rgb.copy()
            ok_count = 0

            for x, y, score_0_1 in hits:
                shape_score = float(score_0_1 * 100.0)
                patch = screenshot_rgb[y:y + template_height, x:x + template_width]
                color_score = color_score_0_100(template_rgb, patch) if patch.shape[:2] == template_rgb.shape[:2] else 0.0

                is_ok = (shape_score >= minimum_shape) and (color_score >= minimum_color)
                if is_ok:
                    ok_count += 1

                rectangle_color = (0, 255, 0) if is_ok else (255, 0, 0)
                cv2.rectangle(visual, (x, y), (x + template_width, y + template_height), rectangle_color, 2)

            best_score = float(hits[0][2] * 100.0) if hits else 0.0
            self.results.insert(tk.END, f"{method_name}  hits={len(hits)}  ok={ok_count}  best_shape={best_score:.2f}%")

            prev = Image.fromarray(visual)
            prev.thumbnail((330, 220))
            self.method_previews[method_name] = ImageTk.PhotoImage(prev)
            gallery_cards.append((best_score, method_name))

        for w in self.gal_inner.winfo_children():
            w.destroy()

        gallery_cards.sort(reverse=True, key=lambda t: t[0])

        for _, method_name in gallery_cards:
            frame = ttk.Frame(self.gal_inner)
            ttk.Label(frame, text=method_name, font=("Arial", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 2))

            img = self.method_previews.get(method_name)
            label = ttk.Label(frame, image=img)
            label.image = img
            label.pack(padx=6, pady=(0, 6))
            frame.pack(side="left", padx=6, pady=6)

        self._resize_gallery()
    # -------------------------
    # END: TEMPLATE MATCHING (KERN)
    # -------------------------

# =========================
# END: GUI APP
# =========================


if __name__ == "__main__":
    app = ImageDebugger()
    app.mainloop()
