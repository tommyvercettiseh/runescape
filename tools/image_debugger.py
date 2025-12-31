# === BOOTSTRAP PATH START ===
import sys
from pathlib import Path

# Zorg dat project-root in sys.path staat
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# === BOOTSTRAP PATH END ===

# === IMPORTS START ===
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
# === IMPORTS END ===

# === METHODS CONFIG START ===
METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}
# === METHODS CONFIG END ===

# === FILE PATHS CONFIG START ===
META_FILE = Path(CONFIG_DIR) / "templates_presets.json"
# === FILE PATHS CONFIG END ===


# =========================
# Utilities
# =========================

# === UTILS: DATETIME FORMAT START ===
def human_datetime(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""
# === UTILS: DATETIME FORMAT END ===


# === UTILS: PATH RESOLVE START ===
def resolve_template_path(image_name_or_path: str) -> Path:
    path = Path(image_name_or_path)
    return path if path.is_absolute() else Path(IMAGES_DIR) / image_name_or_path
# === UTILS: PATH RESOLVE END ===


# === UTILS: TEMPLATE READ START ===
def read_template_rgb_gray(path: Path):
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"Template niet gevonden/leesbaar: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return rgb, gray
# === UTILS: TEMPLATE READ END ===


# === UTILS: COLOR SCORE START ===
def color_score_0_100(template_rgb: np.ndarray, patch_rgb: np.ndarray) -> float:
    """
    Simpele kleur-vergelijking op basis van mean absolute error.
    100 = exact gelijk, 0 = maximaal verschillend.
    """
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, patch_rgb)
    mae = float(np.mean(diff))
    return float(np.clip(100.0 - mae, 0.0, 100.0))
# === UTILS: COLOR SCORE END ===


# === UTILS: SCREENSHOT GRAB START ===
def grab_region_rgb(box_xyxy):
    x1, y1, x2, y2 = box_xyxy
    width, height = x2 - x1, y2 - y1
    img = pyautogui.screenshot(region=(x1, y1, width, height))
    return np.array(img)  # RGB
# === UTILS: SCREENSHOT GRAB END ===


# === UTILS: SCOREMAP NORMALIZE START ===
def scoremap_0_1(match_result: np.ndarray, method_name: str) -> np.ndarray:
    """
    Scoremap altijd 0..1 waarbij 1 = beste match.
    Dit voorkomt rare ranges bij non-normed methods.
    """
    normalized = cv2.normalize(match_result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        normalized = 1.0 - normalized
    return normalized
# === UTILS: SCOREMAP NORMALIZE END ===


# === UTILS: FIND MATCHES WITH NMS START ===
def find_all_matches_with_nms(
    scores_0_1: np.ndarray,
    template_width: int,
    template_height: int,
    minimum_score_0_1: float,
    maximum_hits: int = 50,
    nms_radius_pixels: int | None = None,
):
    """
    Vind alle matches boven minimum_score_0_1 en filter duplicaten weg met een simpele NMS radius.
    Return: list of (x, y, score_0_1) gesorteerd op score aflopend.
    """
    if nms_radius_pixels is None:
        nms_radius_pixels = max(5, int(min(template_width, template_height) * 0.50))

    ys, xs = np.where(scores_0_1 >= float(minimum_score_0_1))
    if len(xs) == 0:
        return []

    values = scores_0_1[ys, xs]
    order = np.argsort(values)[::-1]  # hoogste eerst

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
# === UTILS: FIND MATCHES WITH NMS END ===


# === UTILS: ENSURE DIRECTORIES START ===
def ensure_directories():
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
# === UTILS: ENSURE DIRECTORIES END ===


# === UTILS: JSON LOAD START ===
def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}
# === UTILS: JSON LOAD END ===


# === UTILS: JSON SAVE START ===
def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
# === UTILS: JSON SAVE END ===


# =========================
# Data models
# =========================

# === DATA MODEL: TEMPLATE ROW START ===
@dataclass
class TemplateRow:
    name: str
    path: str
    size_kb: int
    mtime: float
# === DATA MODEL: TEMPLATE ROW END ===


# === DATA MODEL: TEMPLATE SETTINGS START ===
@dataclass
class TemplateSettings:
    method: str = "ALL"      # "ALL" of een specifieke methode
    min_shape: float = 85.0  # vorm threshold 0..100
    min_color: float = 60.0  # kleur threshold 0..100
    max_hits: int = 30       # hoeveel rectangles max
    nms_radius: int = 0      # 0 = auto

    @staticmethod
    def from_dict(d: dict):
        return TemplateSettings(
            method=str(d.get("method", "ALL")),
            min_shape=float(d.get("min_shape", 85.0)),
            min_color=float(d.get("min_color", 60.0)),
            max_hits=int(d.get("max_hits", 30)),
            nms_radius=int(d.get("nms_radius", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "min_shape": self.min_shape,
            "min_color": self.min_color,
            "max_hits": self.max_hits,
            "nms_radius": self.nms_radius,
        }
# === DATA MODEL: TEMPLATE SETTINGS END ===


# =========================
# GUI
# =========================

# === CLASS: IMAGE DEBUGGER APP START ===
class ImageDebugger(tk.Tk):
    # === INIT START ===
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
        self.maximum_hits = tk.IntVar(value=30)
        self.nms_radius = tk.IntVar(value=0)

        self.template_metadata = load_json(META_FILE)

        self._build_ui()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._load_selected_template_settings_into_ui()
    # === INIT END ===

    # === UI: BUILD LAYOUT START ===
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        top = ttk.Panedwindow(self, orient="horizontal")
        top.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        left = ttk.Frame(top)
        right = ttk.Frame(top)
        top.add(left, weight=3)
        top.add(right, weight=2)

        # === UI: LEFT PANEL START ===
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ttk.Label(left, text="Templates (assets/images)").grid(row=0, column=0, sticky="w")

        # === UI: TEMPLATE SEARCH START ===
        self.template_search = tk.StringVar()
        entry = ttk.Entry(left, textvariable=self.template_search)
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        entry.bind("<KeyRelease>", lambda e: self._refresh_template_tree())
        # === UI: TEMPLATE SEARCH END ===

        # === UI: TEMPLATE TREEVIEW START ===
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
        # === UI: TEMPLATE TREEVIEW END ===

        # === UI: LEFT BUTTONS START ===
        buttons = ttk.Frame(left)
        buttons.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(buttons, text="📸 Crop + Resize", command=self._crop_and_resize_template).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="💾 Save preset", command=self._save_current_template_settings).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="✏️ Rename", command=self._rename_template).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="🔁 Refresh", command=self._refresh_all).pack(side="left")
        # === UI: LEFT BUTTONS END ===
        # === UI: LEFT PANEL END ===

        # === UI: RIGHT PANEL START ===
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(6, weight=1)

        # === UI: MAIN PREVIEW START ===
        self.preview_label = tk.Label(right)
        self.preview_label.grid(row=0, column=0, sticky="n", pady=(0, 4))

        self.preview_text = ttk.Label(right, text="Geen template geselecteerd")
        self.preview_text.grid(row=1, column=0, sticky="n", pady=(0, 10))
        # === UI: MAIN PREVIEW END ===

        # === UI: CONTROLS GROUP START ===
        controls = ttk.LabelFrame(right, text="Test settings")
        controls.grid(row=2, column=0, sticky="ew", padx=4, pady=6)
        controls.grid_columnconfigure(1, weight=1)

        # === UI: BOT SELECTOR START ===
        botrow = ttk.Frame(controls)
        botrow.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(6, 4), padx=8)
        ttk.Label(botrow, text="Bot").pack(side="left")
        for i in (1, 2, 3, 4):
            ttk.Radiobutton(botrow, text=str(i), value=i, variable=self.bot_id).pack(side="left", padx=4)
        # === UI: BOT SELECTOR END ===

        # === UI: AREA DROPDOWN START ===
        ttk.Label(controls, text="Area").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.area_cb = ttk.Combobox(controls, textvariable=self.area_var, values=[], width=35)
        self.area_cb.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        # === UI: AREA DROPDOWN END ===

        # === UI: METHOD DROPDOWN START ===
        ttk.Label(controls, text="Methode").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        method_values = ["ALL"] + list(METHODS.keys())
        self.method_cb = ttk.Combobox(controls, textvariable=self.method_var, values=method_values, width=20)
        self.method_cb.grid(row=2, column=1, sticky="w", padx=8, pady=4)
        self.method_cb.set("ALL")
        # === UI: METHOD DROPDOWN END ===

        # === UI: THRESHOLDS START ===
        threshold_row = ttk.Frame(controls)
        threshold_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 2))
        ttk.Label(threshold_row, text="Min shape").pack(side="left")
        ttk.Entry(threshold_row, textvariable=self.minimum_shape_score, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(threshold_row, text="Min color").pack(side="left")
        ttk.Entry(threshold_row, textvariable=self.minimum_color_score, width=6).pack(side="left", padx=6)

        hits_row = ttk.Frame(controls)
        hits_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 8))
        ttk.Label(hits_row, text="Max hits").pack(side="left")
        ttk.Entry(hits_row, textvariable=self.maximum_hits, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(hits_row, text="NMS radius (0=auto)").pack(side="left")
        ttk.Entry(hits_row, textvariable=self.nms_radius, width=6).pack(side="left", padx=6)
        # === UI: THRESHOLDS END ===
        # === UI: CONTROLS GROUP END ===

        # === UI: ACTION BUTTONS START ===
        action = ttk.Frame(right)
        action.grid(row=3, column=0, sticky="ew", padx=4, pady=(2, 6))
        ttk.Button(action, text="🔲 Toon area", command=self._show_area_overlay).pack(side="left", padx=(0, 6))
        ttk.Button(action, text="🔍 Analyze", command=self._analyze).pack(side="left")
        # === UI: ACTION BUTTONS END ===

        # === UI: RESULTS LIST START ===
        ttk.Label(right, text="Resultaten (meerdere hits per methode)").grid(row=4, column=0, sticky="w", padx=6)
        self.results = tk.Listbox(right, height=8)
        self.results.grid(row=5, column=0, sticky="nsew", padx=6, pady=(2, 6))
        # === UI: RESULTS LIST END ===

        # === UI: GALLERY START ===
        ttk.Label(right, text="Preview per methode (alle gevonden rectangles)").grid(row=6, column=0, sticky="w", padx=6)
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
        # === UI: GALLERY END ===

        # === UI: RIGHT PANEL END ===
    # === UI: BUILD LAYOUT END ===

    # === UI: RESIZE GALLERY SCROLLREGION START ===
    def _resize_gallery(self):
        self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all"))
        self.gal_canvas.itemconfig(self.gal_win, height=self.gal_inner.winfo_reqheight())
    # === UI: RESIZE GALLERY SCROLLREGION END ===

    # === DATA: LOAD AREAS START ===
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
    # === DATA: LOAD AREAS END ===

    # === DATA: SCAN TEMPLATES START ===
    def _scan_templates(self):
        self.templates = []
        base = Path(IMAGES_DIR)
        base.mkdir(parents=True, exist_ok=True)

        for path in base.glob("*.png"):
            try:
                st = path.stat()
                size_kb = max(1, math.ceil(st.st_size / 1024))
                self.templates.append(
                    TemplateRow(
                        name=path.name,
                        path=str(path),
                        size_kb=size_kb,
                        mtime=st.st_mtime,
                    )
                )
            except Exception:
                pass

        self.templates.sort(key=lambda r: r.mtime, reverse=True)
    # === DATA: SCAN TEMPLATES END ===

    # === UI: REFRESH TEMPLATE TREE START ===
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
    # === UI: REFRESH TEMPLATE TREE END ===

    # === UI: REFRESH ALL START ===
    def _refresh_all(self):
        self.template_metadata = load_json(META_FILE)
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._update_main_preview()
        self._load_selected_template_settings_into_ui()
    # === UI: REFRESH ALL END ===

    # === UI: GET SELECTED TEMPLATE NAME START ===
    def _selected_template_name(self) -> str:
        sel = self.tree.selection()
        return sel[0] if sel else ""
    # === UI: GET SELECTED TEMPLATE NAME END ===

    # === UI: ON TEMPLATE SELECTED START ===
    def _on_template_selected(self):
        self._update_main_preview()
        self._load_selected_template_settings_into_ui()
    # === UI: ON TEMPLATE SELECTED END ===

    # === UI: MAIN PREVIEW UPDATE START ===
    def _update_main_preview(self):
        name = self._selected_template_name()
        if not name:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Geen template geselecteerd")
            return

        try:
            path = resolve_template_path(name)
            img = Image.open(path)

            # === MAIN PREVIEW THUMBNAIL SIZE START ===
            img.thumbnail((330, 220))  # <-- grootte main preview aanpassen
            # === MAIN PREVIEW THUMBNAIL SIZE END ===

            imgtk = ImageTk.PhotoImage(img)
            self.preview_cache["main"] = imgtk
            self.preview_label.configure(image=imgtk)
            self.preview_text.configure(text=name)
        except Exception:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Preview niet beschikbaar")
    # === UI: MAIN PREVIEW UPDATE END ===

    # === PRESETS: READ UI SETTINGS START ===
    def _get_current_template_settings_from_ui(self) -> TemplateSettings:
        return TemplateSettings(
            method=str(self.method_var.get() or "ALL"),
            min_shape=float(self.minimum_shape_score.get()),
            min_color=float(self.minimum_color_score.get()),
            max_hits=int(self.maximum_hits.get()),
            nms_radius=int(self.nms_radius.get()),
        )
    # === PRESETS: READ UI SETTINGS END ===

    # === PRESETS: LOAD SETTINGS TO UI START ===
    def _load_selected_template_settings_into_ui(self):
        # === PRESET LOAD START ===
        template_name = self._selected_template_name()
        if not template_name:
            return

        raw = self.template_metadata.get(template_name, {})

        # Verwacht preset-format:
        # { "method_name": "...", "vorm_drempel": 90, "kleur_drempel": 60 }
        if isinstance(raw, dict) and ("method_name" in raw or "vorm_drempel" in raw or "kleur_drempel" in raw):
            self.method_var.set(str(raw.get("method_name", "TM_CCOEFF_NORMED")))
            self.minimum_shape_score.set(float(raw.get("vorm_drempel", 90.0)))
            self.minimum_color_score.set(float(raw.get("kleur_drempel", 60.0)))
        else:
            # fallback defaults
            self.method_var.set("ALL")
            self.minimum_shape_score.set(85.0)
            self.minimum_color_score.set(60.0)

        # Deze bestaan nog in de UI maar worden niet meer persist opgeslagen
        self.maximum_hits.set(int(getattr(self.maximum_hits, "get", lambda: 30)()))
        self.nms_radius.set(int(getattr(self.nms_radius, "get", lambda: 0)()))
        # === PRESET LOAD END ===
    # === PRESETS: LOAD SETTINGS TO UI END ===

    # === PRESETS: SAVE SETTINGS START ===
    def _save_current_template_settings(self):
        # === PRESET SAVE START ===
        template_name = self._selected_template_name()
        if not template_name:
            return messagebox.showerror("Preset", "Selecteer eerst een template")

        # Alleen opslaan wat detect_image nodig heeft
        data = {
            "method_name": str(self.method_var.get() or "TM_CCOEFF_NORMED"),
            "vorm_drempel": float(self.minimum_shape_score.get()),
            "kleur_drempel": float(self.minimum_color_score.get()),
        }

        presets = load_json(META_FILE)
        presets[template_name] = data
        save_json(META_FILE, presets)

        messagebox.showinfo("✅ Preset opgeslagen", f"{template_name}
→ {META_FILE}")
        # === PRESET SAVE END ===
    # === PRESETS: SAVE SETTINGS END ===

    # === TOOL: SHOW AREA OVERLAY START ===
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
    # === TOOL: SHOW AREA OVERLAY END ===

    # === TOOL: CROP AND RESIZE START ===
    def _crop_and_resize_template(self):
        """
        Fullscreen crop → daarna optioneel resize → opslaan in IMAGES_DIR.
        """
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

            # default preset aanmaken (optioneel)
            if new_name not in self.template_metadata:
                self.template_metadata[new_name] = TemplateSettings().to_dict()
                save_json(META_FILE, self.template_metadata)

            self._refresh_all()
            if self.tree.exists(new_name):
                self.tree.selection_set(new_name)
                self.tree.see(new_name)

            messagebox.showinfo("✅ Opgeslagen", f"{new_name}\n{out_path}")

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
    # === TOOL: CROP AND RESIZE END ===

    # === TOOL: RENAME TEMPLATE START ===
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

            # metadata meeverhuizen
            if current in self.template_metadata:
                self.template_metadata[new] = self.template_metadata.pop(current)
                save_json(META_FILE, self.template_metadata)

            self._refresh_all()
            if self.tree.exists(new):
                self.tree.selection_set(new)
                self.tree.see(new)
        except Exception as e:
            messagebox.showerror("Rename", str(e))
    # === TOOL: RENAME TEMPLATE END ===

    # === ANALYSIS: MAIN ANALYZE START ===
    def _analyze(self):
        # === ANALYSIS: VALIDATION START ===
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
        # === ANALYSIS: VALIDATION END ===

        # === ANALYSIS: LOAD TEMPLATE START ===
        template_path = resolve_template_path(template_name)
        try:
            template_rgb, template_gray = read_template_rgb_gray(template_path)
        except Exception as e:
            return messagebox.showerror("Template", str(e))
        # === ANALYSIS: LOAD TEMPLATE END ===

        # === ANALYSIS: GRAB SCREENSHOT AREA START ===
        box = apply_offset(self.areas[area_name], int(self.bot_id.get()))
        screenshot_rgb = grab_region_rgb(box)
        screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
        # === ANALYSIS: GRAB SCREENSHOT AREA END ===

        # === ANALYSIS: SIZE CHECK START ===
        template_height, template_width = template_gray.shape[:2]
        if screenshot_gray.shape[0] < template_height or screenshot_gray.shape[1] < template_width:
            return messagebox.showerror("Analyze", "Template is groter dan je area")
        # === ANALYSIS: SIZE CHECK END ===

        # === ANALYSIS: METHOD LIST START ===
        selected_method = self.method_var.get()
        method_names = list(METHODS.keys()) if selected_method == "ALL" else [selected_method]
        # === ANALYSIS: METHOD LIST END ===

        # === ANALYSIS: THRESHOLDS PREP START ===
        minimum_score_0_1 = float(minimum_shape) / 100.0
        nms_radius_pixels = None if nms_radius == 0 else nms_radius
        # === ANALYSIS: THRESHOLDS PREP END ===

        # === ANALYSIS: CLEAR UI OUTPUT START ===
        self.results.delete(0, tk.END)
        self.method_previews.clear()
        # === ANALYSIS: CLEAR UI OUTPUT END ===

        # === ANALYSIS: GALLERY SORT LIST START ===
        gallery_cards = []
        # === ANALYSIS: GALLERY SORT LIST END ===

        # === ANALYSIS: LOOP METHODS START ===
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

            # === ANALYSIS: DRAW RECTANGLES START ===
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
            # === ANALYSIS: DRAW RECTANGLES END ===

            # === ANALYSIS: RESULTS ROW START ===
            best_score = float(hits[0][2] * 100.0) if hits else 0.0
            self.results.insert(
                tk.END,
                f"{method_name}  hits={len(hits)}  ok={ok_count}  best_shape={best_score:.2f}%"
            )
            # === ANALYSIS: RESULTS ROW END ===

            # === PREVIEW THUMBNAIL START ===
            prev = Image.fromarray(visual)
            prev.thumbnail((330, 220))  # <-- grootte previews aanpassen
            self.method_previews[method_name] = ImageTk.PhotoImage(prev)
            # === PREVIEW THUMBNAIL END ===

            gallery_cards.append((best_score, method_name))
        # === ANALYSIS: LOOP METHODS END ===

        # === GALLERY: CLEAR START ===
        for w in self.gal_inner.winfo_children():
            w.destroy()
        # === GALLERY: CLEAR END ===

        # === GALLERY: SORT START ===
        gallery_cards.sort(reverse=True, key=lambda t: t[0])
        # === GALLERY: SORT END ===

        # === GALLERY: BUILD CARDS START ===
        for _, method_name in gallery_cards:
            frame = ttk.Frame(self.gal_inner)
            ttk.Label(frame, text=method_name, font=("Arial", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 2))

            img = self.method_previews.get(method_name)
            label = ttk.Label(frame, image=img)
            label.image = img
            label.pack(padx=6, pady=(0, 6))

            frame.pack(side="left", padx=6, pady=6)
        # === GALLERY: BUILD CARDS END ===

        self._resize_gallery()
    # === ANALYSIS: MAIN ANALYZE END ===

# === CLASS: IMAGE DEBUGGER APP END ===


# === MAIN ENTRYPOINT START ===
if __name__ == "__main__":
    app = ImageDebugger()
    app.mainloop()
# === MAIN ENTRYPOINT END ===
