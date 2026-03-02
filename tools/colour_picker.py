# tools/colour_picker.py
# Area / Debug Square -> Screenshot -> Kleurpalette -> Klik tegel OF pipet op Original -> FILTER + MASK + HEX + HSV 🎨🧪
#
# Vereist: pyautogui, opencv-python, numpy, pillow, tkinter
# pip install pyautogui opencv-python numpy pillow

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageTk

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

def get_pixel_rgb_safe(rgb_img, x, y):
    h, w = rgb_img.shape[:2]
    x = clamp(int(x), 0, w - 1)
    y = clamp(int(y), 0, h - 1)
    r, g, b = rgb_img[y, x]
    return int(r), int(g), int(b)

def grab_area_rgb(area_name, bot_id, areas):
    if area_name not in areas:
        raise KeyError(f"Area niet gevonden: {area_name}")

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 2 or h <= 2:
        return None

    shot = np.array(pyautogui.screenshot(region=(x1, y1, w, h)))  # RGB
    return shot

def grab_screen_square_rgb(x, y, size, inner_pad):
    """
    Screenshot van vrij scherm, maar pakt alleen de binnenkant (inner_pad),
    zodat je nooit de felgroene rand sampled.
    """
    x = int(x)
    y = int(y)
    size = int(size)

    ix = x + inner_pad
    iy = y + inner_pad
    iw = size - inner_pad * 2
    ih = size - inner_pad * 2

    if iw <= 12 or ih <= 12:
        return None

    shot = np.array(pyautogui.screenshot(region=(ix, iy, iw, ih)))  # RGB
    return shot

def gray_out_non_mask(rgb_img, mask):
    bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray3 = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    out = gray3.copy()
    out[mask > 0] = bgr[mask > 0]

    # klein groen accent op matches
    out = out.astype(np.int16)
    out[:, :, 1] = np.clip(out[:, :, 1] + (mask > 0).astype(np.int16) * 70, 0, 255)
    return out.astype(np.uint8)

def palette_kmeans(rgb_img, k=18, sample_max=12000):
    small = rgb_img
    h, w = small.shape[:2]
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
    _compactness, labels, centers = cv2.kmeans(Z, k, None, criteria, 3, flags)

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
        m1 = cv2.inRange(hsv_img, (0, lo_s, lo_v), (hi_h, hi_s, hi_v))
        m2 = cv2.inRange(hsv_img, (179 + lo_h, lo_s, lo_v), (179, hi_s, hi_v))
        return cv2.bitwise_or(m1, m2)

    if hi_h > 179:
        m1 = cv2.inRange(hsv_img, (lo_h, lo_s, lo_v), (179, hi_s, hi_v))
        m2 = cv2.inRange(hsv_img, (0, lo_s, lo_v), (hi_h - 179, hi_s, hi_v))
        return cv2.bitwise_or(m1, m2)

    return cv2.inRange(hsv_img, (lo_h, lo_s, lo_v), (hi_h, hi_s, hi_v))

def img_to_tk(arr, max_w=320, max_h=220, mode="rgb"):
    """
    Return:
      (tk_img, disp_w, disp_h)
    """
    if mode == "bgr":
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    elif mode == "gray":
        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)

    img = Image.fromarray(arr)
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.BILINEAR)

    tkimg = ImageTk.PhotoImage(img)
    dw, dh = img.size
    return tkimg, dw, dh


# ============================================================
# Debug Square Overlay
# ============================================================
class DebugSquare:
    """
    Zwevend topmost venster met felgroene rand.
    Drag om te verplaatsen, resize via handle rechtsonder.
    Screenshot pakt binnenkant met inner_pad zodat border nooit mee sampled.
    """
    def __init__(self, parent, size=240, border=5, inner_pad=14):
        self.parent = parent
        self.size = int(size)
        self.border = int(border)
        self.inner_pad = int(max(inner_pad, border + 6))  # extra safe

        self.win = tk.Toplevel(parent)
        self.win.title("Debug Square 🎯")
        self.win.attributes("-topmost", True)
        self.win.resizable(False, False)

        # borderless overlay
        self.win.overrideredirect(True)

        # Windows Tk fix: bg="" kan niet
        self.canvas = tk.Canvas(
            self.win,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg="#0f1115"
        )
        self.canvas.pack(fill="both", expand=True)

        self._drag_start = None
        self._resize_start = None

        self._draw()

        # drag in midden
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<ButtonRelease-1>", self._stop_drag)

        # resize handle
        self.canvas.tag_bind("handle", "<Button-1>", self._start_resize)
        self.canvas.tag_bind("handle", "<B1-Motion>", self._do_resize)
        self.canvas.tag_bind("handle", "<ButtonRelease-1>", self._stop_resize)

        # ESC = hide
        self.win.bind("<Escape>", lambda _e=None: self.hide())

        # start positie
        self.win.geometry(f"{self.size}x{self.size}+120+120")

    def _draw(self):
        self.canvas.delete("all")
        s = self.size
        b = self.border

        self.canvas.create_rectangle(
            b, b, s - b, s - b,
            outline="#00FF3B",
            width=b
        )

        self.canvas.create_text(
            s // 2, 16,
            text="Drag  Resize corner  ESC hide",
            fill="#00FF3B",
            font=("Segoe UI", 9)
        )

        hs = 18
        x1, y1 = s - hs - 6, s - hs - 6
        x2, y2 = s - 6, s - 6
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="#00FF3B",
            outline="#00FF3B",
            tags=("handle",)
        )

    def show(self):
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        try:
            self.win.withdraw()
        except Exception:
            pass

    def is_visible(self):
        try:
            return str(self.win.state()) != "withdrawn"
        except Exception:
            return False

    def get_capture_region(self):
        self.win.update_idletasks()
        x = self.win.winfo_rootx()
        y = self.win.winfo_rooty()
        return x, y, self.size, self.inner_pad

    def _start_drag(self, e):
        current = self.canvas.find_withtag("current")
        if current and "handle" in self.canvas.gettags(current[0]):
            return
        self._drag_start = (e.x_root, e.y_root, self.win.winfo_x(), self.win.winfo_y())

    def _do_drag(self, e):
        if not self._drag_start:
            return
        sx, sy, wx, wy = self._drag_start
        dx = e.x_root - sx
        dy = e.y_root - sy
        self.win.geometry(f"{self.size}x{self.size}+{wx + dx}+{wy + dy}")

    def _stop_drag(self, _e=None):
        self._drag_start = None

    def _start_resize(self, e):
        self._resize_start = (e.x_root, e.y_root, self.size)

    def _do_resize(self, e):
        if not self._resize_start:
            return
        sx, sy, start_size = self._resize_start
        dx = e.x_root - sx
        dy = e.y_root - sy
        new_size = int(max(120, min(780, start_size + max(dx, dy))))
        if new_size != self.size:
            self.size = new_size
            self.win.geometry(f"{self.size}x{self.size}+{self.win.winfo_x()}+{self.win.winfo_y()}")
            self.canvas.config(width=self.size, height=self.size)
            self._draw()

    def _stop_resize(self, _e=None):
        self._resize_start = None


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

        # keep refs alive
        self.preview_original = None
        self.preview_filter = None
        self.preview_mask = None

        # for pipet mapping
        self._orig_disp_w = 1
        self._orig_disp_h = 1
        self._orig_src_w = 1
        self._orig_src_h = 1

        self.root = tk.Tk()
        self.root.title("Colour Picker 🎨")
        self.root.geometry("1030x700")
        self.root.minsize(980, 640)

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#0f1115")
        style.configure("TLabel", background="#0f1115", foreground="#e7e7e7")
        style.configure("TLabelframe", background="#0f1115", foreground="#e7e7e7")
        style.configure("TLabelframe.Label", background="#0f1115", foreground="#e7e7e7")
        style.configure("TButton", padding=6)
        style.configure("TScale", background="#0f1115")

        self.area_var = tk.StringVar(value=self.area_names[0] if self.area_names else "Bot_Area")
        self.bot_id_var = tk.IntVar(value=1)

        self.k_var = tk.IntVar(value=18)
        self.tol_h = tk.IntVar(value=8)
        self.tol_s = tk.IntVar(value=60)
        self.tol_v = tk.IntVar(value=60)

        self.use_square_var = tk.BooleanVar(value=False)

        self.hex_var = tk.StringVar(value="HEX: ")
        self.hsv_var = tk.StringVar(value="HSV: ")
        self.info_var = tk.StringVar(value="Tip: klik op Original preview als pipet 🎯")

        self.square = DebugSquare(self.root, size=240, border=5, inner_pad=14)
        self.square.hide()

        self.build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")

        ttk.Label(header, text="Area").pack(side="left")
        if self.area_names:
            cmb = ttk.Combobox(header, textvariable=self.area_var, values=self.area_names, width=26, state="readonly")
            cmb.pack(side="left", padx=8)
        else:
            ttk.Entry(header, textvariable=self.area_var, width=28).pack(side="left", padx=8)

        ttk.Label(header, text="bot_id").pack(side="left")
        ttk.Spinbox(header, from_=1, to=8, textvariable=self.bot_id_var, width=5).pack(side="left", padx=8)

        ttk.Checkbutton(header, text="🎯 Debug Square", variable=self.use_square_var, command=self.on_toggle_square)\
            .pack(side="left", padx=10)

        ttk.Button(header, text="📸 Screenshot", command=self.on_screenshot).pack(side="left", padx=8)

        ttk.Label(header, text="K").pack(side="left", padx=(10, 0))
        ttk.Spinbox(header, from_=6, to=60, textvariable=self.k_var, width=5).pack(side="left", padx=6)
        ttk.Button(header, text="🎛️ Rebuild", command=self.rebuild_palette).pack(side="left")

        ttk.Button(header, text="🧹 Clear", command=self.clear_previews).pack(side="right")

        previews = ttk.Frame(outer)
        previews.pack(fill="x", pady=(12, 8))

        def make_preview(title, hint=""):
            lf = ttk.Labelframe(previews, text=title, padding=8)
            lf.pack(side="left", fill="both", expand=True, padx=6)
            lbl = ttk.Label(lf, text=hint or "(leeg)", anchor="center")
            lbl.pack(fill="both", expand=True)
            return lbl

        self.lbl_original = make_preview("Original", hint="(Screenshot maken)")
        self.lbl_filter = make_preview("Filter", hint="(klik tegel of pipet)")
        self.lbl_mask = make_preview("Mask", hint="(klik tegel of pipet)")

        # pipet click op original preview
        self.lbl_original.bind("<Button-1>", self.on_pick_from_original)

        mid = ttk.Frame(outer)
        mid.pack(fill="x", pady=(8, 6))

        def slider_row(label, var, fr, to):
            row = ttk.Frame(mid)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=10).pack(side="left")
            s = ttk.Scale(row, from_=fr, to=to, orient="horizontal", command=lambda _=None: self.apply_filter())
            s.pack(side="left", fill="x", expand=True, padx=8)
            s.set(var.get())

            def on_release(_):
                var.set(int(float(s.get())))
                self.apply_filter()

            s.bind("<ButtonRelease-1>", on_release)
            return s

        slider_row("tol_h", self.tol_h, 1, 30)
        slider_row("tol_s", self.tol_s, 0, 180)
        slider_row("tol_v", self.tol_v, 0, 180)

        meta = ttk.Frame(outer)
        meta.pack(fill="x", pady=(6, 6))
        ttk.Label(meta, textvariable=self.hex_var, font=("Consolas", 12)).pack(anchor="w")
        ttk.Label(meta, textvariable=self.hsv_var, font=("Consolas", 12)).pack(anchor="w")

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="📋 Copy HEX", command=self.copy_hex).pack(side="left")
        ttk.Button(btns, text="📋 Copy HSV", command=self.copy_hsv).pack(side="left", padx=8)

        status = ttk.Label(outer, textvariable=self.info_var)
        status.pack(anchor="w", pady=(0, 8))

        self.palette_frame = ttk.Labelframe(outer, text="Palette (optioneel)  Klik tegel", padding=8)
        self.palette_frame.pack(fill="both", expand=True)

        self.palette_canvas = tk.Canvas(self.palette_frame, highlightthickness=0, bg="#0f1115")
        self.palette_canvas.pack(fill="both", expand=True)

    def on_toggle_square(self):
        if self.use_square_var.get():
            self.square.show()
            self.info_var.set("Debug Square aan 🎯 sleep hem, resize hoek, ESC = hide")
        else:
            self.square.hide()
            self.info_var.set("Debug Square uit 🙂")

    def clear_previews(self):
        self.preview_original = None
        self.preview_filter = None
        self.preview_mask = None
        self.lbl_original.configure(image="", text="(Screenshot maken)")
        self.lbl_filter.configure(image="", text="(klik tegel of pipet)")
        self.lbl_mask.configure(image="", text="(klik tegel of pipet)")
        self.info_var.set("Previews gewist 🧹")

    def set_original_preview(self, rgb_img):
        tkimg, dw, dh = img_to_tk(rgb_img, mode="rgb")
        self.preview_original = tkimg
        self.lbl_original.configure(image=tkimg, text="")

        self._orig_disp_w = int(dw)
        self._orig_disp_h = int(dh)
        self._orig_src_w = int(rgb_img.shape[1])
        self._orig_src_h = int(rgb_img.shape[0])

    def set_filter_preview(self, bgr_img):
        tkimg, _dw, _dh = img_to_tk(bgr_img, mode="bgr")
        self.preview_filter = tkimg
        self.lbl_filter.configure(image=tkimg, text="")

    def set_mask_preview(self, mask_gray):
        tkimg, _dw, _dh = img_to_tk(mask_gray, mode="gray")
        self.preview_mask = tkimg
        self.lbl_mask.configure(image=tkimg, text="")

    def on_screenshot(self):
        # bron kiezen
        if self.use_square_var.get() and self.square.is_visible():
            x, y, size, inner_pad = self.square.get_capture_region()
            shot = grab_screen_square_rgb(x, y, size, inner_pad)
            if shot is None:
                self.info_var.set("Square te klein / pad te groot 😅 resize even")
                return
            self.info_var.set(f"Screenshot via Debug Square ✅ inner_pad={inner_pad}px")
        else:
            area = self.area_var.get().strip()
            bot_id = int(self.bot_id_var.get())
            shot = grab_area_rgb(area, bot_id, self.areas)
            if shot is None:
                self.info_var.set("Screenshot faalde 😅 check area coords")
                return
            self.info_var.set("Screenshot via vaste area ✅")

        self.shot_rgb = shot
        self.selected_center = None
        self.hex_var.set("HEX: ")
        self.hsv_var.set("HSV: ")

        self.set_original_preview(self.shot_rgb)
        self.lbl_filter.configure(image="", text="(klik tegel of pipet)")
        self.lbl_mask.configure(image="", text="(klik tegel of pipet)")

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
        self.info_var.set("Tip: klik op Original preview als pipet 🎯")

    def render_palette_tiles(self):
        self.palette_canvas.delete("all")
        if self.palette_centers is None:
            return

        tiles_per_row = 8
        tile = 70
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

            rect = self.palette_canvas.create_rectangle(x1, y1, x2, y2, fill=hx, outline="#222", width=2)
            txt = self.palette_canvas.create_text(x1 + 6, y2 - 10, text=f"{i+1}", anchor="w", fill="white")

            def make_cb(idx):
                return lambda _e=None: self.on_pick_tile(idx)

            self.palette_canvas.tag_bind(rect, "<Button-1>", make_cb(i))
            self.palette_canvas.tag_bind(txt, "<Button-1>", make_cb(i))

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

    def on_pick_from_original(self, e):
        """
        Pipet: klik op Original preview en pak exact die pixel uit self.shot_rgb.
        Houd rekening met "centered image" in ttk.Label.
        """
        if self.shot_rgb is None:
            self.info_var.set("Eerst Screenshot 🙂")
            return

        # label size (kan groter zijn dan image)
        lw = max(1, int(self.lbl_original.winfo_width()))
        lh = max(1, int(self.lbl_original.winfo_height()))

        dw = int(self._orig_disp_w)
        dh = int(self._orig_disp_h)

        # image is centered -> offsets
        ox = max(0, (lw - dw) // 2)
        oy = max(0, (lh - dh) // 2)

        x_disp = int(e.x) - ox
        y_disp = int(e.y) - oy

        # buiten image? clamp toch, scheelt gezeik
        x_disp = clamp(x_disp, 0, dw - 1)
        y_disp = clamp(y_disp, 0, dh - 1)

        # map naar originele resolutie
        sx = self._orig_src_w / float(dw)
        sy = self._orig_src_h / float(dh)
        x = int(x_disp * sx)
        y = int(y_disp * sy)

        rgb = get_pixel_rgb_safe(self.shot_rgb, x, y)
        self.selected_center = rgb

        hx = rgb_to_hex(rgb)
        hsv = rgb_to_hsv(rgb)
        self.hex_var.set(f"HEX: {hx}")
        self.hsv_var.set(f"HSV: {hsv}")

        self.apply_filter()
        self.info_var.set(f"🎯 Pipet: {hx} @ ({x},{y}) ✅")

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

        filt_bgr = gray_out_non_mask(self.shot_rgb, mask)
        nonzero = int(cv2.countNonZero(mask))

        self.set_filter_preview(filt_bgr)
        self.set_mask_preview(mask)

        self.info_var.set(f"Match pixels: {nonzero}  tweak tol_h tol_s tol_v ✅")

    def copy_hex(self):
        val = self.hex_var.get().replace("HEX: ", "").strip()
        if not val:
            self.info_var.set("Geen HEX 😅 kies kleur")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.root.update()
        self.info_var.set(f"HEX gekopieerd ✅ {val}")

    def copy_hsv(self):
        val = self.hsv_var.get().replace("HSV: ", "").strip()
        if not val:
            self.info_var.set("Geen HSV 😅 kies kleur")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(val)
        self.root.update()
        self.info_var.set(f"HSV gekopieerd ✅ {val}")

    def on_close(self):
        try:
            self.square.hide()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()