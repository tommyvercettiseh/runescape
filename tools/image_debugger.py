from __future__ import annotations

# ============================================================
# BOOTSTRAP
# WAT: Zorgt dat imports werken vanuit je project-root.
# WAAROM: Je wil dit script kunnen runnen vanaf elke map.
# ============================================================
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]  # Runescape/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# IMPORTS
# WAT: UI, screenshots, OpenCV en Windows global hotkeys.
# WAAROM: F8 = Screenshot tool en F9 = Analyze, ook zonder focus.
# ============================================================
import os
import math
import json
import threading
import ctypes
import ctypes.wintypes
from dataclasses import dataclass
from datetime import datetime

import cv2
import numpy as np
import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk

from core.paths import CONFIG_DIR, IMAGES_DIR, AREAS_FILE
from core.bot_offsets import apply_offset, load_areas

# ============================================================
# OPENCV METHODS
# ============================================================
METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

META_FILE = Path(CONFIG_DIR) / "templates_meta.json"
DEBUG_META_FILE = Path(CONFIG_DIR) / "templates_meta_debugger.json"

# ============================================================
# FILES / STORAGE
# ============================================================
def ensure_directories():
    Path(IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)


def ensure_debug_meta_exists():
    """
    Debug meta wordt automatisch gemaakt als kopie van templates_meta.json.
    Dit houdt risico laag: je main file blijft exact zoals je scripts verwachten.
    """
    if DEBUG_META_FILE.exists():
        return
    if META_FILE.exists():
        _safe_write_json(DEBUG_META_FILE, _safe_read_json(META_FILE))
    else:
        _safe_write_json(DEBUG_META_FILE, {})


def human_datetime(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def resolve_template_path(image_name_or_path):
    p = Path(image_name_or_path)
    return p if p.is_absolute() else Path(IMAGES_DIR) / image_name_or_path


def _safe_read_json(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _safe_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_all_metadata():
    """
    Debugger gebruikt altijd de debugger-meta (met area).
    Bestaat die nog niet, dan valt hij terug op META_FILE.
    """
    if DEBUG_META_FILE.exists():
        return _safe_read_json(DEBUG_META_FILE)
    return _safe_read_json(META_FILE)


def save_template_metadata(template_name, settings_dict):
    """
    Dual save:
    META_FILE: alleen thresholds/method (GEEN area)
    DEBUG_META_FILE: thresholds/method + area
    """
    main_dict = dict(settings_dict)
    main_dict.pop("area", None)

    meta_main = _safe_read_json(META_FILE)
    meta_main[template_name] = main_dict
    _safe_write_json(META_FILE, meta_main)

    meta_dbg = _safe_read_json(DEBUG_META_FILE)
    meta_dbg[template_name] = settings_dict
    _safe_write_json(DEBUG_META_FILE, meta_dbg)


def delete_template_metadata(template_name):
    meta_main = _safe_read_json(META_FILE)
    if template_name in meta_main:
        meta_main.pop(template_name, None)
        _safe_write_json(META_FILE, meta_main)

    meta_dbg = _safe_read_json(DEBUG_META_FILE)
    if template_name in meta_dbg:
        meta_dbg.pop(template_name, None)
        _safe_write_json(DEBUG_META_FILE, meta_dbg)

# ============================================================
# IMAGE HELPERS
# ============================================================
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
    return np.array(img)  # RGB


def color_score_0_100(template_rgb, patch_rgb):
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(patch_rgb, (template_rgb.shape[1], template_rgb.shape[0]))
    diff = cv2.absdiff(template_rgb, patch_rgb)
    mae = float(np.mean(diff))
    return float(np.clip(100.0 - mae, 0.0, 100.0))


def scoremap_0_1(match_result, method_name):
    normalized = cv2.normalize(match_result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        normalized = 1.0 - normalized
    return normalized


def find_all_matches_with_nms(
    scores_0_1,
    template_width,
    template_height,
    minimum_score_0_1,
    maximum_hits=50,
    nms_radius_pixels=None,
):
    if nms_radius_pixels is None:
        nms_radius_pixels = max(5, int(min(template_width, template_height) * 0.50))

    ys, xs = np.where(scores_0_1 >= float(minimum_score_0_1))
    if len(xs) == 0:
        return []

    values = scores_0_1[ys, xs]
    order = np.argsort(values)[::-1]

    picked = []
    for idx in order:
        x = int(xs[idx])
        y = int(ys[idx])
        score = float(values[idx])

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


def _crop_rgb(img_rgb, x1, y1, x2, y2):
    h, w = img_rgb.shape[:2]
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return img_rgb
    return img_rgb[y1:y2, x1:x2]

# ============================================================
# MODELS
# ============================================================
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
    area: str = ""

    @staticmethod
    def from_dict(d):
        return TemplateSettings(
            method=str(d.get("method", "ALL")),
            min_shape=float(d.get("min_shape", 85.0)),
            min_color=float(d.get("min_color", 60.0)),
            area=str(d.get("area", "")) if d.get("area") is not None else "",
        )

    def to_dict(self):
        out = {"method": self.method, "min_shape": self.min_shape, "min_color": self.min_color}
        if self.area:
            out["area"] = self.area
        return out

# ============================================================
# APP
# ============================================================
class ImageDebugger(tk.Tk):
    def __init__(self, verbose=False):
        super().__init__()
        ensure_directories()
        ensure_debug_meta_exists()

        self.verbose = verbose

        self.title("🧪 Image Debugger")
        self.geometry("1280x760")
        self.minsize(1100, 680)

        if self.verbose:
            print("ℹ️ IMAGES_DIR:", str(IMAGES_DIR))
            print("ℹ️ AREAS_FILE:", str(AREAS_FILE))
            print("ℹ️ META_FILE:", str(META_FILE))
            print("ℹ️ DEBUG_META_FILE:", str(DEBUG_META_FILE))

        self.areas = {}
        self.templates = []
        self.template_metadata = load_all_metadata()

        self.bot_id = tk.IntVar(value=1)
        self.area_var = tk.StringVar(value="")
        self.method_var = tk.StringVar(value="ALL")

        self.minimum_shape_score = tk.DoubleVar(value=85.0)
        self.minimum_color_score = tk.DoubleVar(value=60.0)

        self.maximum_hits = tk.IntVar(value=30)
        self.nms_radius = tk.IntVar(value=0)

        self.auto_analyze_on_select = tk.BooleanVar(value=True)

        self.lens_enabled = tk.BooleanVar(value=True)
        self.lens_zoom = tk.IntVar(value=8)

        self._last_analysis = {}
        self._thumb_cache = {}
        self._template_preview_cache = {}

        self._screenshot_open = False

        self._build_ui()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._update_template_preview()
        self._load_selected_template_settings_into_ui()
        self._update_code_snippets()

        self._hotkey_stop = threading.Event()
        self._hotkey_thread = threading.Thread(target=self._win_hotkey_loop, daemon=True)
        self._hotkey_thread.start()

        self.area_cb.bind("<<ComboboxSelected>>", lambda e: self._update_code_snippets())
        self.bot_id.trace_add("write", lambda *_: self._update_code_snippets())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _win_hotkey_loop(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        WM_HOTKEY = 0x0312
        VK_F8 = 0x77
        VK_F9 = 0x78

        HOTKEY_F8 = 1
        HOTKEY_F9 = 2

        ok_f8 = bool(user32.RegisterHotKey(None, HOTKEY_F8, 0, VK_F8))
        ok_f9 = bool(user32.RegisterHotKey(None, HOTKEY_F9, 0, VK_F9))

        if self.verbose:
            print("✅ F8 Screenshot" if ok_f8 else "❌ F8 failed (run as admin bij admin vensters)")
            print("✅ F9 Analyze" if ok_f9 else "❌ F9 failed (run as admin bij admin vensters)")

        if not (ok_f8 or ok_f9):
            return

        try:
            msg = ctypes.wintypes.MSG()
            while not self._hotkey_stop.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == WM_HOTKEY:
                        if msg.wParam == HOTKEY_F8:
                            self.after(0, self._open_screenshot_tool_safe)
                        elif msg.wParam == HOTKEY_F9:
                            self.after(0, self._analyze)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                kernel32.Sleep(15)
        finally:
            if ok_f8:
                user32.UnregisterHotKey(None, HOTKEY_F8)
            if ok_f9:
                user32.UnregisterHotKey(None, HOTKEY_F9)

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        top = ttk.Panedwindow(self, orient="horizontal")
        top.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 6))

        left = ttk.Frame(top)
        right = ttk.Frame(top)
        top.add(left, weight=3)
        top.add(right, weight=2)

        bottom = ttk.LabelFrame(self, text="Methode previews (alles in 1 oogopslag)")
        bottom.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        bottom.grid_columnconfigure(0, weight=1)

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        ttk.Label(left, text=f"Templates ({IMAGES_DIR})").grid(row=0, column=0, sticky="w")

        self.template_search = tk.StringVar()
        entry = ttk.Entry(left, textvariable=self.template_search)
        entry.grid(row=1, column=0, sticky="ew", pady=(4, 6))
        entry.bind("<KeyRelease>", lambda e: self._refresh_template_tree())

        self.tree = ttk.Treeview(
            left,
            columns=("name", "preset", "kb", "modified"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Bestandsnaam")
        self.tree.heading("preset", text="Preset")
        self.tree.heading("kb", text="KB")
        self.tree.heading("modified", text="Gewijzigd")

        self.tree.column("name", width=440, anchor="w")
        self.tree.column("preset", width=70, anchor="center")
        self.tree.column("kb", width=70, anchor="e")
        self.tree.column("modified", width=140, anchor="center")

        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_template_selected())

        scroll_y = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        scroll_y.grid(row=2, column=1, sticky="ns")

        btns = ttk.Frame(left)
        btns.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        ttk.Button(btns, text="📸 Screenshot (F8)", command=self._open_screenshot_tool_safe).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="🗑️ Delete", command=self._delete_template).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="✏️ Rename", command=self._rename_template).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="💾 Save preset", command=self._save_current_template_settings).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="🔁 Refresh", command=self._refresh_all).pack(side="left")

        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(3, weight=1)

        prev_box = ttk.LabelFrame(right, text="Template preview")
        prev_box.grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        prev_box.grid_columnconfigure(0, weight=1)

        self.preview_label = tk.Label(prev_box)
        self.preview_label.grid(row=0, column=0, sticky="n", pady=(6, 2))
        self.preview_text = ttk.Label(prev_box, text="Geen template geselecteerd")
        self.preview_text.grid(row=1, column=0, sticky="n", pady=(0, 6))

        controls = ttk.LabelFrame(right, text="Test settings")
        controls.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 6))
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

        thr = ttk.Frame(controls)
        thr.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 8))
        ttk.Label(thr, text="Min shape").pack(side="left")
        ttk.Entry(thr, textvariable=self.minimum_shape_score, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(thr, text="Min colour").pack(side="left")
        ttk.Entry(thr, textvariable=self.minimum_color_score, width=6).pack(side="left", padx=6)

        hr = ttk.Frame(controls)
        hr.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 10))
        ttk.Label(hr, text="Max hits").pack(side="left")
        ttk.Entry(hr, textvariable=self.maximum_hits, width=6).pack(side="left", padx=(6, 14))
        ttk.Label(hr, text="NMS radius (0=auto)").pack(side="left")
        ttk.Entry(hr, textvariable=self.nms_radius, width=6).pack(side="left", padx=6)

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 6))
        ttk.Button(actions, text="🔲 Toon area", command=self._show_area_overlay).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="🔍 Analyze (F9)", command=self._analyze).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="📋 Copy table", command=self._copy_results_table).pack(side="left")
        ttk.Checkbutton(actions, text="Auto analyze", variable=self.auto_analyze_on_select).pack(side="left", padx=(10, 0))

        res_box = ttk.LabelFrame(right, text="Resultaten (dubbelklik = methode selecteren)")
        res_box.grid(row=3, column=0, sticky="nsew", padx=4, pady=(0, 6))
        res_box.grid_columnconfigure(0, weight=1)
        res_box.grid_rowconfigure(0, weight=1)

        cols = ("method", "hit", "shape", "colour", "hits", "ok")
        self.res_tree = ttk.Treeview(res_box, columns=cols, show="headings", height=8)
        self.res_tree.heading("method", text="Methode")
        self.res_tree.heading("hit", text="Hit")
        self.res_tree.heading("shape", text="Shape %")
        self.res_tree.heading("colour", text="Colour %")
        self.res_tree.heading("hits", text="Hits")
        self.res_tree.heading("ok", text="Ok")

        self.res_tree.column("method", width=160, anchor="w")
        self.res_tree.column("hit", width=60, anchor="center")
        self.res_tree.column("shape", width=80, anchor="e")
        self.res_tree.column("colour", width=80, anchor="e")
        self.res_tree.column("hits", width=60, anchor="e")
        self.res_tree.column("ok", width=60, anchor="e")
        self.res_tree.grid(row=0, column=0, sticky="nsew")

        res_scroll = ttk.Scrollbar(res_box, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscrollcommand=res_scroll.set)
        res_scroll.grid(row=0, column=1, sticky="ns")

        self.res_tree.bind("<Double-1>", self._on_results_double_click)

        code_box = ttk.LabelFrame(right, text="Code snippets (dubbelklik = kopiëren)")
        code_box.grid(row=4, column=0, sticky="ew", padx=4, pady=(0, 6))
        code_box.grid_columnconfigure(0, weight=1)

        def make_snip(parent, title):
            frame = ttk.Frame(parent)
            frame.pack(fill="x", padx=8, pady=6)

            ttk.Label(frame, text=title).pack(anchor="w")

            txt = tk.Text(frame, height=2, wrap="none")
            txt.pack(fill="x", pady=(4, 0))
            txt.configure(state="disabled", cursor="hand2")

            def on_double(_e=None):
                val = txt.get("1.0", "end").strip()
                if val and "Selecteer template" not in val:
                    self._copy_text(val)

            txt.bind("<Double-Button-1>", on_double)
            return txt

        self.snip_detect = make_snip(code_box, "detect_image")
        self.snip_click_right = make_snip(code_box, "click_image right")
        self.snip_click_left = make_snip(code_box, "click_image left")

        gal = ttk.Frame(bottom)
        gal.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        gal.grid_columnconfigure(0, weight=1)

        self.gal_canvas = tk.Canvas(gal, highlightthickness=0)
        self.gal_canvas.grid(row=0, column=0, sticky="ew")

        gal_scroll = ttk.Scrollbar(gal, orient="horizontal", command=self.gal_canvas.xview)
        gal_scroll.grid(row=1, column=0, sticky="ew")
        self.gal_canvas.configure(xscrollcommand=gal_scroll.set)

        self.gal_inner = ttk.Frame(self.gal_canvas)
        self._gal_win = self.gal_canvas.create_window((0, 0), window=self.gal_inner, anchor="nw")
        self.gal_inner.bind("<Configure>", lambda e: self._resize_gallery())

    def _resize_gallery(self):
        self.gal_canvas.configure(scrollregion=self.gal_canvas.bbox("all"))
        self.gal_canvas.itemconfig(self._gal_win, height=self.gal_inner.winfo_reqheight())
        self.gal_canvas.configure(height=min(230, max(160, self.gal_inner.winfo_reqheight() + 10)))

    def _copy_text(self, text: str):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass

    def _set_snippet_box(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _update_code_snippets(self):
        t = self._selected_template_name()
        area = self.area_var.get()
        bot = int(self.bot_id.get())

        if not t or not area:
            msg = "Selecteer template + area 🙂"
            self._set_snippet_box(self.snip_detect, msg)
            self._set_snippet_box(self.snip_click_right, msg)
            self._set_snippet_box(self.snip_click_left, msg)
            return

        name_png = t if t.lower().endswith(".png") else f"{t}.png"
        name_noext = Path(t).stem

        s1 = f'detect_image("{name_png}", "{area}", bot_id={bot}, verbose=True)'
        s2 = f'click_image("{name_noext}", "{area}", {bot}, button="right", verbose=True)'
        s3 = f'click_image("{name_noext}", "{area}", {bot}, verbose=True)  # links (default)'

        self._set_snippet_box(self.snip_detect, s1)
        self._set_snippet_box(self.snip_click_right, s2)
        self._set_snippet_box(self.snip_click_left, s3)

    def _load_areas(self):
        try:
            self.areas = load_areas(verbose=False)
            names = sorted(self.areas.keys())
            self.area_cb["values"] = names
            if names and self.area_var.get() not in names:
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
        tokens = [t for t in query.split() if t]

        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = self.templates
        if tokens:
            rows = [r for r in rows if all(t in r.name.lower() for t in tokens)]

        meta = self.template_metadata or {}

        for r in rows:
            preset_txt = "✅" if r.name in meta else ""
            self.tree.insert("", "end", iid=r.name, values=(r.name, preset_txt, r.size_kb, human_datetime(r.mtime)))

        if rows and not self.tree.selection():
            self.tree.selection_set(rows[0].name)
            self.tree.see(rows[0].name)

    def _refresh_all(self):
        self.template_metadata = load_all_metadata()
        self._load_areas()
        self._scan_templates()
        self._refresh_template_tree()
        self._update_template_preview()
        self._load_selected_template_settings_into_ui()
        self._update_code_snippets()

    def _selected_template_name(self):
        sel = self.tree.selection()
        return sel[0] if sel else ""

    def _on_template_selected(self):
        self._update_template_preview()
        self._load_selected_template_settings_into_ui()
        self._update_code_snippets()

        if not self.auto_analyze_on_select.get():
            return
        self.after(80, self._analyze)

    def _update_template_preview(self):
        name = self._selected_template_name()
        if not name:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Geen template geselecteerd")
            return
        try:
            path = resolve_template_path(name)
            img = Image.open(path)
            img.thumbnail((260, 260))
            imgtk = ImageTk.PhotoImage(img)
            self._template_preview_cache["main"] = imgtk
            self.preview_label.configure(image=imgtk)
            self.preview_text.configure(text=name)
        except Exception:
            self.preview_label.configure(image="")
            self.preview_text.configure(text="Preview niet beschikbaar")

    def _get_ui_settings(self):
        return TemplateSettings(
            method=str(self.method_var.get() or "ALL"),
            min_shape=float(self.minimum_shape_score.get()),
            min_color=float(self.minimum_color_score.get()),
            area=str(self.area_var.get() or ""),
        )

    def _load_selected_template_settings_into_ui(self):
        t = self._selected_template_name()
        if not t:
            return

        raw = (self.template_metadata or {}).get(t, {})
        s = TemplateSettings.from_dict(raw)

        self.method_var.set(s.method)
        self.minimum_shape_score.set(s.min_shape)
        self.minimum_color_score.set(s.min_color)

        if s.area and s.area in (self.areas or {}):
            self.area_var.set(s.area)

    def _save_current_template_settings(self):
        t = self._selected_template_name()
        if not t:
            return messagebox.showerror("Preset", "Selecteer eerst een template")
        s = self._get_ui_settings()
        save_template_metadata(t, s.to_dict())
        self.template_metadata = load_all_metadata()
        self._refresh_template_tree()
        messagebox.showinfo("✅ Saved", f"{t}\n→ {META_FILE.name} + {DEBUG_META_FILE.name}")

    def _on_results_double_click(self, _event=None):
        sel = self.res_tree.selection()
        if not sel:
            return
        vals = self.res_tree.item(sel[0], "values")
        if not vals:
            return

        method = str(vals[0]).strip()
        if method not in METHODS:
            return

        self.method_var.set(method)
        self.after(50, self._analyze)

    def _delete_template(self):
        current = self._selected_template_name()
        if not current:
            return messagebox.showerror("Delete", "Geen template geselecteerd")
        if not messagebox.askyesno("Delete", f"Verwijderen?\n\n{current}"):
            return
        try:
            p = resolve_template_path(current)
            if p.exists():
                p.unlink()
            delete_template_metadata(current)
            self._refresh_all()
        except Exception as e:
            messagebox.showerror("Delete", str(e))

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

            main_meta = _safe_read_json(META_FILE)
            dbg_meta = _safe_read_json(DEBUG_META_FILE)

            if current in main_meta:
                main_meta[new] = main_meta.pop(current)
                _safe_write_json(META_FILE, main_meta)

            if current in dbg_meta:
                dbg_meta[new] = dbg_meta.pop(current)
                _safe_write_json(DEBUG_META_FILE, dbg_meta)

            self._refresh_all()
            if self.tree.exists(new):
                self.tree.selection_set(new)
                self.tree.see(new)
        except Exception as e:
            messagebox.showerror("Rename", str(e))

    def _show_area_overlay(self):
        area = self.area_var.get()
        if area not in self.areas:
            return messagebox.showerror("Area", "Selecteer een geldige area")

        try:
            box = apply_offset(self.areas[area], self.bot_id.get())
            x1, y1, x2, y2 = box

            overlay = tk.Toplevel(self)
            overlay.attributes("-fullscreen", True)
            overlay.attributes("-alpha", 0.25)
            overlay.configure(bg="black")

            canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=3)
            canvas.create_text(x1 + 6, y1 - 14, text=f"{area} (bot {self.bot_id.get()})", anchor="nw", fill="red")
            canvas.bind("<Button-1>", lambda e: overlay.destroy())
            overlay.bind("<Escape>", lambda e: overlay.destroy())
        except Exception as e:
            messagebox.showerror("Overlay", str(e))

    def _clear_results_table(self):
        for iid in self.res_tree.get_children():
            self.res_tree.delete(iid)

    def _add_result_row(self, method, hit, shape, colour, hits, ok):
        self.res_tree.insert(
            "",
            "end",
            values=(
                method,
                "✅" if hit else "❌",
                f"{shape:.2f}",
                f"{colour:.2f}",
                str(hits),
                str(ok),
            ),
        )

    def _copy_results_table(self):
        rows = []
        header = ["Method", "Hit", "Shape %", "Colour %", "Hits", "Ok"]
        rows.append("\t".join(header))
        for iid in self.res_tree.get_children():
            vals = self.res_tree.item(iid, "values")
            rows.append("\t".join(map(str, vals)))
        text = "\n".join(rows).strip()
        if not text:
            return
        self._copy_text(text)
        messagebox.showinfo("📋 Copied", "Tabel staat in je clipboard 🙂")

    def _analyze(self):
        template_name = self._selected_template_name()
        if not template_name:
            return

        area_name = self.area_var.get()
        if not area_name or area_name not in self.areas:
            return

        try:
            min_shape = float(self.minimum_shape_score.get())
            min_colour = float(self.minimum_color_score.get())
            max_hits = self.maximum_hits.get()
            nms_radius = self.nms_radius.get()
        except Exception:
            return messagebox.showerror("Analyze", "Ongeldige thresholds")

        template_path = resolve_template_path(template_name)
        try:
            template_rgb, template_gray = read_template_rgb_gray(template_path)
        except Exception as e:
            return messagebox.showerror("Template", str(e))

        box_abs = apply_offset(self.areas[area_name], self.bot_id.get())
        screenshot_rgb = grab_region_rgb(box_abs)
        screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)

        th, tw = template_gray.shape[:2]
        if screenshot_gray.shape[0] < th or screenshot_gray.shape[1] < tw:
            return messagebox.showerror("Analyze", "Template is groter dan je area")

        selected_method = str(self.method_var.get() or "ALL").strip()
        method_names = list(METHODS.keys()) if selected_method == "ALL" else [selected_method]

        minimum_score_0_1 = float(min_shape) / 100.0
        nms_radius_pixels = None if nms_radius == 0 else nms_radius

        self._last_analysis.clear()
        self._thumb_cache.clear()
        self._clear_results_table()

        for w in self.gal_inner.winfo_children():
            w.destroy()

        thumb_w, thumb_h = 230, 140

        for method_name in method_names:
            if method_name not in METHODS:
                continue

            method = METHODS[method_name]
            match_result = cv2.matchTemplate(screenshot_gray, template_gray, method)
            scores_0_1 = scoremap_0_1(match_result, method_name)

            hits = find_all_matches_with_nms(
                scores_0_1=scores_0_1,
                template_width=tw,
                template_height=th,
                minimum_score_0_1=minimum_score_0_1,
                maximum_hits=max_hits,
                nms_radius_pixels=nms_radius_pixels,
            )

            visual = screenshot_rgb.copy()
            ok_count = 0

            best_shape_local = 0.0
            best_colour_local = 0.0
            best_xy = None

            for x, y, score_0_1 in hits:
                shape = float(score_0_1 * 100.0)
                patch = screenshot_rgb[y:y + th, x:x + tw]
                colour = color_score_0_100(template_rgb, patch) if patch.shape[:2] == template_rgb.shape[:2] else 0.0

                is_ok = (shape >= min_shape) and (colour >= min_colour)
                if is_ok:
                    ok_count += 1

                rect_color = (0, 255, 0) if is_ok else (255, 0, 0)
                cv2.rectangle(visual, (x, y), (x + tw, y + th), rect_color, 2)

                if shape > best_shape_local:
                    best_shape_local = shape
                    best_colour_local = colour
                    best_xy = (x, y)

            hit_bool = len(hits) > 0
            self._add_result_row(method_name, hit_bool, best_shape_local, best_colour_local, len(hits), ok_count)

            self._last_analysis[method_name] = {
                "visual_rgb": visual,
                "template_wh": (tw, th),
                "box_abs": box_abs,
                "hits": hits,
                "best_xy": best_xy,
                "best_shape": best_shape_local,
                "best_colour": best_colour_local,
                "ok": ok_count,
            }

            pil = Image.fromarray(visual).resize((thumb_w, thumb_h), Image.Resampling.NEAREST)
            imgtk = ImageTk.PhotoImage(pil)
            self._thumb_cache[method_name] = imgtk

            card = ttk.Frame(self.gal_inner)
            title = f"{method_name} | Shape {best_shape_local:.1f}% | Colour {best_colour_local:.1f}% | {len(hits)} hits"
            ttk.Label(card, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=(6, 2))

            lbl = ttk.Label(card, image=imgtk)
            lbl.image = imgtk
            lbl.pack(padx=6, pady=(0, 6))
            lbl.bind("<Button-1>", lambda e, m=method_name: self._open_method_popup(m))

            card.pack(side="left", padx=6, pady=6)

        self._resize_gallery()

    def _open_method_popup(self, method_name):
        info = self._last_analysis.get(method_name)
        if not info:
            return

        visual = info["visual_rgb"]
        w = tk.Toplevel(self)
        w.title(f"🖼️ {method_name}")
        w.attributes("-topmost", True)

        pil = Image.fromarray(visual)
        pil.thumbnail((1200, 800))

        canvas = tk.Canvas(w, highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        imgtk = ImageTk.PhotoImage(pil)
        canvas.create_image(0, 0, image=imgtk, anchor="nw")
        canvas.image = imgtk

        w.geometry(f"{pil.size[0]}x{pil.size[1]}+80+80")

    def _open_screenshot_tool_safe(self):
        if self._screenshot_open:
            return
        self._screenshot_open = True
        try:
            self._screenshot_tool()
        finally:
            self._screenshot_open = False

    def _screenshot_tool(self):
        self.withdraw()

        screen_pil = pyautogui.screenshot()
        screen_rgb = np.array(screen_pil)
        base_w, base_h = screen_pil.size

        win = tk.Toplevel(self)
        win.attributes("-fullscreen", True)
        win.configure(bg="black")

        state = {
            "scale": 2.0,
            "min_scale": 1.0,
            "max_scale": 10.0,
            "panning": False,
            "pan_start": (0, 0),
            "selecting": False,
            "sel_start_canvas": (0, 0),
            "active_rect": None,
            "last_selection_img": None,
            "space_down": False,
        }

        canvas = tk.Canvas(win, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        hint = tk.Label(
            win,
            text="📸 Screenshot | Wheel=zoom | Space+drag=pan | Drag=select | Enter=save | Esc=cancel",
            bg="black",
            fg="white",
            padx=12,
            pady=8,
        )
        hint.place(x=12, y=12)

        lens = tk.Toplevel(win)
        lens.overrideredirect(True)
        lens.attributes("-topmost", True)
        lens_label = tk.Label(lens, bd=2, relief="solid")
        lens_label.pack()
        lens.withdraw()

        def render_image():
            scale = float(state["scale"])
            disp_w = int(base_w * scale)
            disp_h = int(base_h * scale)
            disp = screen_pil.resize((disp_w, disp_h), Image.Resampling.NEAREST)
            img_tk = ImageTk.PhotoImage(disp)

            canvas.delete("bg")
            canvas.create_image(0, 0, image=img_tk, anchor="nw", tags=("bg",))
            canvas.image = img_tk
            canvas.configure(scrollregion=(0, 0, disp_w, disp_h))
            canvas.tag_raise("rect")

        def canvas_to_image_coords(cx, cy):
            x = canvas.canvasx(cx)
            y = canvas.canvasy(cy)
            scale = float(state["scale"])
            ix = int(np.clip(x / scale, 0, base_w - 1))
            iy = int(np.clip(y / scale, 0, base_h - 1))
            return ix, iy

        def update_lens(event):
            if not self.lens_enabled.get():
                lens.withdraw()
                return

            try:
                zoom = max(2, int(self.lens_zoom.get()))
            except Exception:
                zoom = 8

            ix, iy = canvas_to_image_coords(event.x, event.y)

            pad = 18
            x1, y1 = ix - pad, iy - pad
            x2, y2 = ix + pad, iy + pad
            patch = _crop_rgb(screen_rgb, x1, y1, x2, y2)

            pil = Image.fromarray(patch).resize(
                (patch.shape[1] * zoom, patch.shape[0] * zoom),
                Image.Resampling.NEAREST,
            )

            imgtk = ImageTk.PhotoImage(pil)
            lens_label.configure(image=imgtk)
            lens_label.image = imgtk

            lens.deiconify()
            lens.geometry(f"+{event.x_root + 20}+{event.y_root + 20}")

        def clear_rect():
            rid = state["active_rect"]
            if rid:
                try:
                    canvas.delete(rid)
                except Exception:
                    pass
            state["active_rect"] = None

        def on_key_down(e):
            if e.keysym == "space":
                state["space_down"] = True
                canvas.configure(cursor="fleur")

            if e.keysym == "Return":
                if not state["last_selection_img"]:
                    return

                lens.withdraw()
                win.destroy()
                self.deiconify()

                x1, y1, x2, y2 = state["last_selection_img"]
                if (x2 - x1) < 5 or (y2 - y1) < 5:
                    return

                region = screen_pil.crop((x1, y1, x2, y2))

                new_name = simpledialog.askstring(
                    "Bestandsnaam",
                    "Naam voor template (zonder .png mag ook):",
                    initialvalue=f"Screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    parent=self,
                )
                if not new_name:
                    return
                if not new_name.lower().endswith(".png"):
                    new_name += ".png"

                out_path = Path(IMAGES_DIR) / new_name
                region.save(out_path)

                if new_name not in (self.template_metadata or {}):
                    area_now = str(self.area_var.get() or "")
                    s = TemplateSettings(area=area_now)
                    save_template_metadata(new_name, s.to_dict())

                self._refresh_all()
                if self.tree.exists(new_name):
                    self.tree.selection_set(new_name)
                    self.tree.see(new_name)

                messagebox.showinfo("✅ Opgeslagen", f"{new_name}\n{out_path}")

            if e.keysym == "Escape":
                lens.withdraw()
                win.destroy()
                self.deiconify()

        def on_key_up(e):
            if e.keysym == "space":
                state["space_down"] = False
                canvas.configure(cursor="cross")

        def on_wheel(e):
            old = float(state["scale"])
            delta = 1.15 if e.delta > 0 else (1 / 1.15)
            new = float(np.clip(old * delta, state["min_scale"], state["max_scale"]))
            if abs(new - old) < 1e-6:
                return

            mx = canvas.canvasx(e.x)
            my = canvas.canvasy(e.y)
            relx = mx / (base_w * old)
            rely = my / (base_h * old)

            state["scale"] = new
            render_image()

            canvas.xview_moveto(np.clip(relx - (e.x / max(1, canvas.winfo_width())), 0, 1))
            canvas.yview_moveto(np.clip(rely - (e.y / max(1, canvas.winfo_height())), 0, 1))

        def on_mouse_down(e):
            update_lens(e)

            if state["space_down"]:
                state["panning"] = True
                state["pan_start"] = (e.x, e.y)
                return

            state["selecting"] = True
            sx = canvas.canvasx(e.x)
            sy = canvas.canvasy(e.y)
            state["sel_start_canvas"] = (sx, sy)

            clear_rect()
            rid = canvas.create_rectangle(sx, sy, sx, sy, outline="red", width=2, tags=("rect",))
            state["active_rect"] = rid

        def on_mouse_drag(e):
            update_lens(e)

            if state["panning"]:
                dx = state["pan_start"][0] - e.x
                dy = state["pan_start"][1] - e.y
                canvas.xview_scroll(dx, "units")
                canvas.yview_scroll(dy, "units")
                state["pan_start"] = (e.x, e.y)
                return

            if not state["selecting"] or not state["active_rect"]:
                return

            sx0, sy0 = state["sel_start_canvas"]
            sx1 = canvas.canvasx(e.x)
            sy1 = canvas.canvasy(e.y)
            canvas.coords(state["active_rect"], sx0, sy0, sx1, sy1)

        def on_mouse_up(e):
            update_lens(e)

            if state["panning"]:
                state["panning"] = False
                return

            if not state["selecting"] or not state["active_rect"]:
                state["selecting"] = False
                return

            state["selecting"] = False

            x0, y0, x1, y1 = canvas.coords(state["active_rect"])
            ix0 = int(np.clip(min(x0, x1) / state["scale"], 0, base_w))
            iy0 = int(np.clip(min(y0, y1) / state["scale"], 0, base_h))
            ix1 = int(np.clip(max(x0, x1) / state["scale"], 0, base_w))
            iy1 = int(np.clip(max(y0, y1) / state["scale"], 0, base_h))

            state["last_selection_img"] = (ix0, iy0, ix1, iy1)
            canvas.itemconfig(state["active_rect"], outline="lime", width=2)

        sbx = ttk.Scrollbar(win, orient="horizontal", command=canvas.xview)
        sby = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(xscrollcommand=sbx.set, yscrollcommand=sby.set)
        sbx.pack(side="bottom", fill="x")
        sby.pack(side="right", fill="y")

        win.bind("<KeyPress>", on_key_down)
        win.bind("<KeyRelease>", on_key_up)
        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)
        canvas.bind("<Motion>", update_lens)
        canvas.bind("<MouseWheel>", on_wheel)

        canvas.configure(cursor="cross")
        win.focus_force()
        render_image()

    def _on_close(self):
        try:
            self._hotkey_stop.set()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = ImageDebugger(verbose=False)
    app.mainloop()
