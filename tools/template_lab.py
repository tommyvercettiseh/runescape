from __future__ import annotations

import sys
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import ImageGrab, Image, ImageTk


# =========================
# BOOTSTRAP (project root vinden)
# =========================
HERE = Path(__file__).resolve()

def find_project_root(start: Path) -> Path:
    p = start
    for _ in range(15):
        if (p / "core").exists() and (p / "assets").exists():
            return p
        p = p.parent
    return start.parents[1]

PROJECT_ROOT = find_project_root(HERE)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from core.paths import IMAGES_DIR
except Exception:
    IMAGES_DIR = str(PROJECT_ROOT / "assets" / "images")


# =========================
# BBOX SELECTOR overlay
# ESC = cancel
# =========================
def select_bbox_overlay(parent) -> tuple[int, int, int, int] | None:
    bbox: dict[str, int] = {}
    state = {"x0": 0, "y0": 0, "x1": 0, "y1": 0, "x2": 0, "y2": 0, "rect": None}

    win = tk.Toplevel(parent)
    win.attributes("-fullscreen", True)
    win.attributes("-alpha", 0.25)
    win.configure(bg="black")
    win.title("Select BBox  Enter=OK  ESC=Cancel")
    win.focus_force()
    win.grab_set()

    canvas = tk.Canvas(win, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    def redraw():
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            state["x1"], state["y1"], state["x2"], state["y2"],
            outline="red", width=2
        )

    def down(e):
        state["x0"], state["y0"] = e.x, e.y
        state["x1"], state["y1"] = e.x, e.y
        state["x2"], state["y2"] = e.x, e.y
        redraw()

    def drag(e):
        state["x1"] = min(state["x0"], e.x)
        state["y1"] = min(state["y0"], e.y)
        state["x2"] = max(state["x0"], e.x)
        state["y2"] = max(state["y0"], e.y)
        redraw()

    def commit(_=None):
        x1, y1, x2, y2 = int(state["x1"]), int(state["y1"]), int(state["x2"]), int(state["y2"])
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            return
        bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"] = x1, y1, x2, y2
        win.destroy()

    def cancel(_=None):
        win.destroy()

    canvas.bind("<ButtonPress-1>", down)
    canvas.bind("<B1-Motion>", drag)

    win.bind("<Return>", commit)
    win.bind("<Escape>", cancel)

    parent.wait_window(win)

    if not bbox:
        return None
    return bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]


    def on_key(e):
        if e.keysym == "Escape":
            state["cancel"] = True
            root.destroy()

    def down(e):
        state["x0"], state["y0"] = e.x, e.y

    def drag(e):
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(state["x0"], state["y0"], e.x, e.y, outline="red", width=2)

    def up(e):
        x1 = min(state["x0"], e.x)
        y1 = min(state["y0"], e.y)
        x2 = max(state["x0"], e.x)
        y2 = max(state["y0"], e.y)
        bbox["xyxy"] = (int(x1), int(y1), int(x2), int(y2))
        root.destroy()

    root.bind("<Key>", on_key)
    canvas.bind("<ButtonPress-1>", down)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", up)

    root.mainloop()

    if state["cancel"]:
        return None
    return bbox.get("xyxy")


# =========================
# UI: preview + zoom + start knop
# =========================
class CaptureUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Batch Capture (bbox)  ESC = stop")
        self.geometry("980x640")

        self.stop_flag = False
        self.bind("<Escape>", lambda e: self._stop())

        self.bbox: tuple[int, int, int, int] | None = None
        self._imgtk_preview = None
        self._imgtk_zoom = None

        self.var_label = tk.StringVar(value="fire")
        self.var_seconds = tk.StringVar(value="10")
        self.var_fps = tk.StringVar(value="8")
        self.var_zoom = tk.StringVar(value="6")     # zoom factor
        self.var_zoom_box = tk.StringVar(value="120")  # px around center

        self._build()

    def _build(self):
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        top = ttk.LabelFrame(root, text="Instellingen")
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="Label (mapnaam):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_label, width=18).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(top, text="Seconds:").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_seconds, width=10).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(top, text="FPS:").grid(row=0, column=4, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_fps, width=10).grid(row=0, column=5, sticky="w", padx=8, pady=6)

        ttk.Label(top, text="Zoom x:").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_zoom, width=10).grid(row=1, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(top, text="Zoom box (px):").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(top, textvariable=self.var_zoom_box, width=10).grid(row=1, column=3, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(top)
        btns.grid(row=1, column=4, columnspan=2, sticky="e", padx=8, pady=6)

        ttk.Button(btns, text="Select BBox", command=self._select_bbox).pack(side="left", padx=6)
        ttk.Button(btns, text="Preview refresh", command=self._refresh_preview).pack(side="left", padx=6)
        ttk.Button(btns, text="START capture", command=self._start_capture).pack(side="left", padx=6)
        ttk.Button(btns, text="STOP (ESC)", command=self._stop).pack(side="left", padx=6)

        mid = ttk.Frame(root)
        mid.pack(fill="both", expand=True)

        left = ttk.LabelFrame(mid, text="Preview (jouw bbox)")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.lbl_preview = ttk.Label(left)
        self.lbl_preview.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_preview_info = ttk.Label(left, text="Nog geen bbox geselecteerd.", anchor="w")
        self.lbl_preview_info.pack(fill="x", padx=10, pady=(0, 10))

        right = ttk.LabelFrame(mid, text="Zoom op centrum (handig om fire-center te checken)")
        right.pack(side="left", fill="both", expand=True)

        self.lbl_zoom = ttk.Label(right)
        self.lbl_zoom.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_zoom_info = ttk.Label(right, text="Selecteer bbox, dan zie je zoom.", anchor="w")
        self.lbl_zoom_info.pack(fill="x", padx=10, pady=(0, 10))

        self.txt = tk.Text(root, height=10)
        self.txt.pack(fill="x", pady=(10, 0))

    def log(self, s: str):
        self.txt.insert("end", s + "\n")
        self.txt.see("end")
        self.update_idletasks()

    def _stop(self):
        self.stop_flag = True
        self.log("STOP gezet.")

    def _select_bbox(self):
        self.stop_flag = False
        bb = select_bbox_overlay(self)
        if not bb:
            self.log("bbox geannuleerd.")
            return

        x1, y1, x2, y2 = bb
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            self.log("bbox te klein, pak een grotere selectie.")
            return

        self.bbox = bb
        self.log(f"bbox gezet: {bb}")
        time.sleep(0.35)  # overlay weg, dan pas grabben
        self._refresh_preview()

    def _refresh_preview(self):
        if not self.bbox:
            self.log("Geen bbox, eerst selecteren.")
            return

        x1, y1, x2, y2 = self.bbox
        try:
            img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        except Exception as e:
            self.log(f"Grab failed: {e}")
            return

        # Preview (scaled)
        p = img.copy()
        p.thumbnail((440, 440))
        self._imgtk_preview = ImageTk.PhotoImage(p)
        self.lbl_preview.configure(image=self._imgtk_preview)

        w = x2 - x1
        h = y2 - y1
        cx = x1 + w // 2
        cy = y1 + h // 2
        self.lbl_preview_info.configure(text=f"bbox={self.bbox}  size={w}x{h}  center=({cx},{cy})")

        # Zoom center crop
        try:
            zoom_factor = max(2, int(float(self.var_zoom.get())))
        except Exception:
            zoom_factor = 6

        try:
            zoom_box = max(40, int(float(self.var_zoom_box.get())))
        except Exception:
            zoom_box = 120

        zx1 = max(x1, cx - zoom_box // 2)
        zy1 = max(y1, cy - zoom_box // 2)
        zx2 = min(x2, cx + zoom_box // 2)
        zy2 = min(y2, cy + zoom_box // 2)

        crop = img.crop((zx1 - x1, zy1 - y1, zx2 - x1, zy2 - y1))
        zoomed = crop.resize((crop.width * zoom_factor, crop.height * zoom_factor))

        # crosshair in center
        z = zoomed.copy()
        # simpele crosshair via PIL pixels is gedoe; we laten tekst info
        self._imgtk_zoom = ImageTk.PhotoImage(z)
        self.lbl_zoom.configure(image=self._imgtk_zoom)
        self.lbl_zoom_info.configure(text=f"zoom crop box={zoom_box}px  zoom x{zoom_factor}")

        self.log("Preview refreshed.")

    def _start_capture(self):
        self.stop_flag = False

        if not self.bbox:
            messagebox.showerror("Geen bbox", "Selecteer eerst een bbox.")
            return

        label = (self.var_label.get() or "").strip().lower()
        if not label:
            messagebox.showerror("Geen label", "Vul een label in, bv fire.")
            return

        try:
            seconds = float(self.var_seconds.get())
        except Exception:
            seconds = 10.0
        try:
            fps = float(self.var_fps.get())
        except Exception:
            fps = 8.0

        seconds = max(1.0, seconds)
        fps = max(1.0, fps)

        out_dir = Path(IMAGES_DIR) / label / "templates"
        out_dir.mkdir(parents=True, exist_ok=True)

        x1, y1, x2, y2 = self.bbox
        shots = max(1, int(seconds * fps))
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self.log(f"IMAGES_DIR = {IMAGES_DIR}")
        self.log(f"Save folder = {out_dir}")
        self.log(f"Capture start  label={label} seconds={seconds} fps={fps} shots={shots}")

        # Wachtmoment + testfile (bewijs)
        time.sleep(0.35)
        try:
            test_path = out_dir / f"{label}_{stamp}_TEST.png"
            img0 = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            img0.save(test_path)
            self.log(f"TEST saved: {test_path}")
        except Exception as e:
            self.log(f"TEST save failed: {e}")
            messagebox.showerror("Capture error", f"Test save failed:\n{e}")
            return

        # Countdown zodat jij voelt dat je start
        for t in (3, 2, 1):
            if self.stop_flag:
                self.log("Gestopt vóór start.")
                return
            self.log(f"Start in {t}...")
            self.update_idletasks()
            time.sleep(1)

        saved = 0
        t0 = time.time()

        for i in range(1, shots + 1):
            if self.stop_flag:
                self.log("Capture gestopt.")
                break

            try:
                img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                name = f"{label}_{stamp}_{i:04d}.png"
                img.save(out_dir / name)
                saved += 1

                if i <= 10 or i % 10 == 0 or i == shots:
                    self.log(f"saved {i}/{shots}  {name}")

                self.update_idletasks()
                time.sleep(1.0 / max(1e-6, fps))
            except Exception as e:
                self.log(f"Frame {i} failed: {e}")
                break

        dt = time.time() - t0
        self.log(f"Capture klaar. saved={saved}/{shots}  time={dt:.1f}s")
        messagebox.showinfo("Done", f"Saved {saved}/{shots}\nFolder:\n{out_dir}")


if __name__ == "__main__":
    app = CaptureUI()
    app.mainloop()
