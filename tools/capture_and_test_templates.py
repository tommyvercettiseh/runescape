from __future__ import annotations

import sys
import time
import shutil
import signal
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import ImageGrab

# =========================
# BOOTSTRAP
# =========================
HERE = Path(__file__).resolve()

def find_project_root(start: Path) -> Path:
    p = start
    for _ in range(10):
        if (p / "core").exists() and (p / "assets").exists():
            return p
        p = p.parent
    return start.parents[1]

PROJECT_ROOT = find_project_root(HERE)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

# =========================
from core.paths import IMAGES_DIR
from vision.image_detection import detect_image

# =========================
# CONFIG
# =========================
FPS = 8
KEEP_MAX = 30
TEST_FRAMES = 120

# =========================
# UI: SETTINGS
# =========================
def choose_settings():
    win = tk.Tk()
    win.title("Capture settings")

    label_var = tk.StringVar(value="fire")
    area_var = tk.StringVar(value="Bot_Area_Center")
    mode_var = tk.StringVar(value="single")
    method_var = tk.StringVar(value="TM_CCOEFF_NORMED")

    ttk.Label(win, text="Label (mapnaam)").grid(row=0, column=0, sticky="w")
    ttk.Entry(win, textvariable=label_var).grid(row=0, column=1)

    ttk.Label(win, text="Area name").grid(row=1, column=0, sticky="w")
    ttk.Entry(win, textvariable=area_var).grid(row=1, column=1)

    ttk.Label(win, text="Detectie methode").grid(row=2, column=0, sticky="w")
    for i, m in enumerate(("TM_CCOEFF_NORMED", "TM_CCORR_NORMED", "TM_SQDIFF_NORMED")):
        ttk.Radiobutton(win, text=m, variable=method_var, value=m).grid(row=2+i, column=1, sticky="w")

    ttk.Label(win, text="Run type").grid(row=5, column=0, sticky="w")
    ttk.Radiobutton(win, text="Single screenshot test", variable=mode_var, value="single").grid(row=5, column=1, sticky="w")
    ttk.Radiobutton(win, text="Full capture + prune", variable=mode_var, value="full").grid(row=6, column=1, sticky="w")

    ttk.Button(win, text="Start", command=win.destroy).grid(row=7, column=0, columnspan=2, pady=10)

    win.mainloop()
    return (
        label_var.get().strip().lower(),
        area_var.get().strip(),
        mode_var.get(),
        method_var.get(),
    )

# =========================
# BBOX SELECTOR
# =========================
def select_bbox():
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-alpha", 0.25)
    root.configure(bg="black")
    root.bind("<Escape>", lambda e: root.destroy())

    canvas = tk.Canvas(root, bg="black")
    canvas.pack(fill="both", expand=True)

    start = [0, 0]
    rect = None
    bbox = {}

    def down(e):
        start[0], start[1] = e.x, e.y

    def drag(e):
        nonlocal rect
        if rect:
            canvas.delete(rect)
        rect = canvas.create_rectangle(start[0], start[1], e.x, e.y, outline="red", width=2)

    def up(e):
        bbox["x1"] = min(start[0], e.x)
        bbox["y1"] = min(start[1], e.y)
        bbox["x2"] = max(start[0], e.x)
        bbox["y2"] = max(start[1], e.y)
        root.destroy()

    canvas.bind("<ButtonPress-1>", down)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", up)

    root.mainloop()
    return bbox if bbox else None

# =========================
# CAPTURE
# =========================
def capture_images(bbox, raw_dir, label, seconds=15):
    frames = int(seconds * FPS)
    print(f"📸 Capturing {frames} frames")

    for i in range(frames):
        img = ImageGrab.grab(bbox=(bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]))
        img.save(raw_dir / f"{label}_{i:04d}.png")
        time.sleep(1 / FPS)

# =========================
# SINGLE TEST
# =========================
def single_test(bbox, raw_dir, label, area, method):
    img = ImageGrab.grab(bbox=(bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]))
    test_img = raw_dir / f"{label}_single_test.png"
    img.save(test_img)

    hit = detect_image(label, area, verbose=True)
    if hit:
        print(f"🟢 HIT | shape={hit['vorm']:.2f} color={hit['kleur']:.2f}")
    else:
        print("🔴 NO HIT")

# =========================
# TEST & SCORE
# =========================
def test_images(label, area):
    scores = {}
    print("🧪 Testing images")

    for _ in range(TEST_FRAMES):
        hit = detect_image(label, area, verbose=False)
        if hit:
            key = f"{round(hit['vorm'],1)}|{round(hit['kleur'],1)}"
            scores[key] = scores.get(key, 0) + 1
        time.sleep(1 / FPS)

    return scores

# =========================
# PRUNE
# =========================
def prune(raw_dir, active_dir, trash_dir, scores):
    if not scores:
        print("❌ No hits")
        return

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best = ranked[0][1]

    keep = []
    for k, v in ranked:
        if v < best * 0.5:
            break
        if len(keep) >= KEEP_MAX:
            break
        keep.append(k)

    print(f"✅ Keeping {len(keep)} images")

    for img in raw_dir.glob("*.png"):
        shutil.move(img, active_dir / img.name)

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    label, area_name, run_mode, method = choose_settings()

    BASE = Path(IMAGES_DIR) / label
    RAW = BASE / "raw"
    ACTIVE = BASE / "active"
    TRASH = BASE / "trash"

    for d in (RAW, ACTIVE, TRASH):
        d.mkdir(parents=True, exist_ok=True)

    bbox = select_bbox()
    if not bbox:
        sys.exit(0)

    if run_mode == "single":
        single_test(bbox, RAW, label, area_name, method)
        messagebox.showinfo("Done", "Single test klaar")
        sys.exit(0)

    capture_images(bbox, RAW, label)
    scores = test_images(label, area_name)
    prune(RAW, ACTIVE, TRASH, scores)

    messagebox.showinfo("Done", "Capture + test + prune klaar")
