from __future__ import annotations

import os
import sys
import time
import json
import ctypes
import ctypes.wintypes
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox

import pyautogui
import numpy as np
import cv2


# =========================
# PATHS
# =========================
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]

ASSETS_DIR = PROJECT_ROOT / "assets"
SAMPLES_DIR = ASSETS_DIR / "samples"   # voor HSV derive
IMAGES_DIR = ASSETS_DIR / "images"     # als je liever hier opslaat

CONFIG_DIR = PROJECT_ROOT / "config"
STATE_FILE = CONFIG_DIR / "capture_simple_state.json"


def _safe_read_json(path: Path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _safe_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _next_index(folder: Path, label: str):
    folder.mkdir(parents=True, exist_ok=True)
    best = 0
    for p in folder.glob(f"{label}_*.png"):
        try:
            n = int(p.stem.split("_")[-1])
            best = max(best, n)
        except Exception:
            pass
    return best + 1


def _grab_fixed_crop_centered(cx: int, cy: int, w: int, h: int):
    x1 = int(cx - w // 2)
    y1 = int(cy - h // 2)
    img = pyautogui.screenshot(region=(x1, y1, int(w), int(h)))
    return img, (x1, y1, x1 + int(w), y1 + int(h))


def _match_scoremap_0_1(match_result, method_name: str):
    scores = cv2.normalize(match_result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name in ("TM_SQDIFF", "TM_SQDIFF_NORMED"):
        scores = 1.0 - scores
    return scores


METHODS = {
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}


class CaptureSimple(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📸 Capture Simple")
        self.geometry("520x260")
        self.resizable(False, False)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        st = _safe_read_json(STATE_FILE)
        self.label_var = tk.StringVar(value=str(st.get("label", "fire")))
        self.w_var = tk.IntVar(value=int(st.get("w", 60)))
        self.h_var = tk.IntVar(value=int(st.get("h", 70)))
        self.use_samples_var = tk.BooleanVar(value=bool(st.get("use_samples", True)))

        self.counter_var = tk.IntVar(value=1)

        self._build_ui()
        self._sync_counter()


        self._hotkey_stop = False
        self._hotkey_thread = None
        self._start_hotkeys()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)

        row1 = ttk.Frame(frm)
        row1.pack(fill="x", **pad)

        ttk.Label(row1, text="Label").pack(side="left")
        ttk.Entry(row1, textvariable=self.label_var, width=16).pack(side="left", padx=(8, 12))

        ttk.Label(row1, text="W").pack(side="left")
        ttk.Entry(row1, textvariable=self.w_var, width=6).pack(side="left", padx=(8, 12))

        ttk.Label(row1, text="H").pack(side="left")
        ttk.Entry(row1, textvariable=self.h_var, width=6).pack(side="left", padx=(8, 12))

        row2 = ttk.Frame(frm)
        row2.pack(fill="x", **pad)

        ttk.Checkbutton(row2, text="Opslaan in assets/samples (voor HSV derive)", variable=self.use_samples_var, command=self._sync_counter).pack(side="left")

        row3 = ttk.Frame(frm)
        row3.pack(fill="x", **pad)

        self.out_lbl = ttk.Label(row3, text="")
        self.out_lbl.pack(side="left")

        row4 = ttk.Frame(frm)
        row4.pack(fill="x", **pad)

        self.info_lbl = ttk.Label(row4, text="")
        self.info_lbl.pack(side="left")

        row5 = ttk.Frame(frm)
        row5.pack(fill="x", **pad)

        ttk.Button(row5, text="📸 Capture now (F7)", command=self.capture_now).pack(side="left", padx=(0, 8))
        ttk.Button(row5, text="🔄 Sync counter", command=self._sync_counter).pack(side="left", padx=(0, 8))
        ttk.Button(row5, text="🧪 Test templates op 1 ROI (F9)", command=self.test_templates_now).pack(side="left")

        row6 = ttk.Frame(frm)
        row6.pack(fill="x", padx=10, pady=(2, 0))
        ttk.Label(row6, text="Hotkeys: F7 capture, F9 test. Zet je muis boven je target.").pack(side="left")

        self._refresh_labels()

    def _base_dir(self):
        return SAMPLES_DIR if self.use_samples_var.get() else IMAGES_DIR

    def _label_dir(self):
        label = (self.label_var.get() or "fire").strip()
        if not label:
            label = "fire"
        return self._base_dir() / label

    def _sync_counter(self):
        label = (self.label_var.get() or "fire").strip() or "fire"
        folder = self._label_dir()
        self.counter_var.set(_next_index(folder, label))
        self._save_state()
        self._refresh_labels()

    def _refresh_labels(self):
        if not hasattr(self, "out_lbl") or not hasattr(self, "info_lbl"):
            return

        label = (self.label_var.get() or "fire").strip() or "fire"
        folder = self._label_dir()
        nxt = int(self.counter_var.get())
        self.out_lbl.configure(text=f"Output: {str(folder).replace('\\', '/')}")
        self.info_lbl.configure(text=f"Next file: {label}_{nxt:03d}.png | Default crop: {self.w_var.get()}x{self.h_var.get()}")


    def _save_state(self):
        _safe_write_json(STATE_FILE, {
            "label": (self.label_var.get() or "fire").strip() or "fire",
            "w": int(self.w_var.get()),
            "h": int(self.h_var.get()),
            "use_samples": bool(self.use_samples_var.get()),
        })

    def capture_now(self):
        try:
            label = (self.label_var.get() or "fire").strip() or "fire"
            w = int(self.w_var.get())
            h = int(self.h_var.get())
            if w < 10 or h < 10:
                return messagebox.showerror("Capture", "W/H te klein")

            cx, cy = pyautogui.position()
            img_pil, box = _grab_fixed_crop_centered(cx, cy, w, h)

            out_dir = self._label_dir()
            out_dir.mkdir(parents=True, exist_ok=True)

            idx = int(self.counter_var.get())
            out_path = out_dir / f"{label}_{idx:03d}.png"
            img_pil.save(out_path)

            self.counter_var.set(idx + 1)
            self._save_state()
            self._refresh_labels()

            # klein, snel feedback
            self.title(f"✅ Saved {out_path.name} @ {box}")

        except Exception as e:
            messagebox.showerror("Capture", str(e))

    def test_templates_now(self):
        """
        Pakt 1 ROI crop (fixed size) onder je cursor en test ALLE png in de label map
        met matchTemplate. Print top 10 in console + kopieert TSV naar clipboard.
        """
        try:
            label = (self.label_var.get() or "fire").strip() or "fire"
            w = int(self.w_var.get())
            h = int(self.h_var.get())

            cx, cy = pyautogui.position()
            img_pil, box = _grab_fixed_crop_centered(cx, cy, w, h)

            roi_rgb = np.array(img_pil)[:, :, ::-1]  # PIL RGB -> BGR
            roi_gray = cv2.cvtColor(roi_rgb, cv2.COLOR_BGR2GRAY)

            folder = self._label_dir()
            if not folder.exists():
                return messagebox.showerror("Test", f"Geen folder: {folder}")

            pngs = sorted(folder.glob("*.png"))
            if not pngs:
                return messagebox.showerror("Test", f"Geen png in: {folder}")

            results = []
            for p in pngs:
                tpl = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                if tpl is None:
                    continue
                th, tw = tpl.shape[:2]
                if th > roi_gray.shape[0] or tw > roi_gray.shape[1]:
                    continue

                method_name = "TM_CCOEFF_NORMED"
                method = METHODS[method_name]
                mr = cv2.matchTemplate(roi_gray, tpl, method)
                sm = _match_scoremap_0_1(mr, method_name)
                best = float(np.max(sm))
                results.append((p.name, best, tw, th))

            results.sort(key=lambda x: x[1], reverse=True)
            top = results[:10]

            lines = ["name\tscore\tw\th"]
            for name, sc, tw, th in top:
                lines.append(f"{name}\t{sc:.4f}\t{tw}\t{th}")
            text = "\n".join(lines)

            try:
                self.clipboard_clear()
                self.clipboard_append(text)
            except Exception:
                pass

            print("\n=== TEMPLATE TEST TOP 10 ===")
            print(f"ROI box: {box} | label={label} | folder={folder}")
            print(text)

            messagebox.showinfo("🧪 Test", "Top 10 staat in console + in clipboard (TSV) 🙂")

        except Exception as e:
            messagebox.showerror("Test", str(e))

    def _start_hotkeys(self):
        self._hotkey_thread = ctypes.windll.kernel32.CreateThread
        t = os.getpid()  # dummy to keep lint calm

        # we starten een echte python thread via threading, maar zonder extra imports hier:
        import threading
        self._hotkey_thread = threading.Thread(target=self._win_hotkey_loop, daemon=True)
        self._hotkey_thread.start()

    def _win_hotkey_loop(self):
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        WM_HOTKEY = 0x0312
        VK_F7 = 0x76
        VK_F9 = 0x78

        HOTKEY_F7 = 1
        HOTKEY_F9 = 2

        ok_f7 = bool(user32.RegisterHotKey(None, HOTKEY_F7, 0, VK_F7))
        ok_f9 = bool(user32.RegisterHotKey(None, HOTKEY_F9, 0, VK_F9))

        if not (ok_f7 or ok_f9):
            return

        try:
            msg = ctypes.wintypes.MSG()
            while not self._hotkey_stop:
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    if msg.message == WM_HOTKEY:
                        if msg.wParam == HOTKEY_F7:
                            self.after(0, self.capture_now)
                        elif msg.wParam == HOTKEY_F9:
                            self.after(0, self.test_templates_now)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                kernel32.Sleep(15)
        finally:
            if ok_f7:
                user32.UnregisterHotKey(None, HOTKEY_F7)
            if ok_f9:
                user32.UnregisterHotKey(None, HOTKEY_F9)

    def _on_close(self):
        self._hotkey_stop = True
        self._save_state()
        self.destroy()


if __name__ == "__main__":
    app = CaptureSimple()
    app.mainloop()
