from __future__ import annotations

import json
import time
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import ctypes as ct
from ctypes import wintypes as wt

# =========================
# OUTPUT
# =========================
OUT_DIR = Path(__file__).resolve().parent / "recordings"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def now_ns() -> int:
    return time.perf_counter_ns()

# =========================
# wintypes fixes
# =========================
if not hasattr(wt, "HCURSOR"):
    wt.HCURSOR = wt.HANDLE
if not hasattr(wt, "HICON"):
    wt.HICON = wt.HANDLE
if not hasattr(wt, "HBRUSH"):
    wt.HBRUSH = wt.HANDLE
if not hasattr(wt, "HINSTANCE"):
    wt.HINSTANCE = wt.HANDLE
if not hasattr(wt, "HRAWINPUT"):
    wt.HRAWINPUT = wt.HANDLE

USER32 = ct.WinDLL("user32", use_last_error=True)
KERNEL32 = ct.WinDLL("kernel32", use_last_error=True)

WM_INPUT = 0x00FF
RIM_TYPEMOUSE = 0x00000000
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100

RI_MOUSE_WHEEL = 0x0400
RI_MOUSE_HWHEEL = 0x0800
MOUSE_MOVE_ABSOLUTE = 0x0001

class RAWINPUTDEVICE(ct.Structure):
    _fields_ = [
        ("usUsagePage", wt.USHORT),
        ("usUsage", wt.USHORT),
        ("dwFlags", wt.DWORD),
        ("hwndTarget", wt.HWND),
    ]

class RAWINPUTHEADER(ct.Structure):
    _fields_ = [
        ("dwType", wt.DWORD),
        ("dwSize", wt.DWORD),
        ("hDevice", wt.HANDLE),
        ("wParam", wt.WPARAM),
    ]

class RAWMOUSE(ct.Structure):
    _fields_ = [
        ("usFlags", wt.USHORT),
        ("usButtonFlags", wt.USHORT),
        ("usButtonData", wt.USHORT),
        ("ulRawButtons", wt.ULONG),
        ("lLastX", wt.LONG),
        ("lLastY", wt.LONG),
        ("ulExtraInformation", wt.ULONG),
    ]

class RAWINPUTDATA_UNION(ct.Union):
    _fields_ = [("mouse", RAWMOUSE)]

class RAWINPUT(ct.Structure):
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("data", RAWINPUTDATA_UNION),
    ]

class WNDCLASSEXW(ct.Structure):
    _fields_ = [
        ("cbSize", wt.UINT),
        ("style", wt.UINT),
        ("lpfnWndProc", wt.WPARAM),
        ("cbClsExtra", ct.c_int),
        ("cbWndExtra", ct.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HCURSOR),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
        ("hIconSm", wt.HICON),
    ]

class MSG(ct.Structure):
    _fields_ = [
        ("hwnd", wt.HWND),
        ("message", wt.UINT),
        ("wParam", wt.WPARAM),
        ("lParam", wt.LPARAM),
        ("time", wt.DWORD),
        ("pt", wt.POINT),
    ]

def wheel_value(usButtonFlags: int, usButtonData: int):
    if usButtonFlags & RI_MOUSE_WHEEL:
        return ct.c_short(usButtonData).value, "wheel"
    if usButtonFlags & RI_MOUSE_HWHEEL:
        return ct.c_short(usButtonData).value, "hwheel"
    return None, None

# =========================
# Recorder core
# =========================
@dataclass
class Meta:
    created: str
    t0_ns: int
    events_written: int = 0
    duration_sec: float = 0.0
    path: str = ""

class RawMouseSink:
    def __init__(self, on_event):
        self.on_event = on_event
        self.hwnd = None
        self._running = False
        self._thread = None
        self.t0_ns = now_ns()

        self.WNDPROC = ct.WINFUNCTYPE(wt.LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)

        @self.WNDPROC
        def _wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_INPUT:
                dwSize = wt.UINT(0)
                USER32.GetRawInputData(wt.HRAWINPUT(lparam), RID_INPUT, None, ct.byref(dwSize), ct.sizeof(RAWINPUTHEADER))
                size = int(dwSize.value)
                if size <= 0:
                    return USER32.DefWindowProcW(hwnd, msg, wparam, lparam)

                buf = (ct.c_byte * size)()
                res = USER32.GetRawInputData(wt.HRAWINPUT(lparam), RID_INPUT, ct.byref(buf), ct.byref(dwSize), ct.sizeof(RAWINPUTHEADER))
                if res == 0xFFFFFFFF:
                    return USER32.DefWindowProcW(hwnd, msg, wparam, lparam)

                raw = ct.cast(buf, ct.POINTER(RAWINPUT)).contents
                if raw.header.dwType == RIM_TYPEMOUSE:
                    m = raw.data.mouse
                    t_ns = now_ns() - self.t0_ns

                    wheel, wheel_kind = wheel_value(int(m.usButtonFlags), int(m.usButtonData))
                    ev = {
                        "t_ns": int(t_ns),
                        "type": "raw_mouse",
                        "device": int(ct.cast(raw.header.hDevice, ct.c_void_p).value or 0),
                        "dx": int(m.lLastX),
                        "dy": int(m.lLastY),
                        "abs": bool(m.usFlags & MOUSE_MOVE_ABSOLUTE),
                        "flags": int(m.usFlags),
                        "btn_flags": int(m.usButtonFlags),
                        "wheel": wheel,
                        "wheel_kind": wheel_kind,
                        "extra": int(m.ulExtraInformation),
                    }
                    self.on_event(ev)
                    return 0
            return USER32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc = _wndproc

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self.hwnd:
            try:
                USER32.PostMessageW(self.hwnd, 0x0012, 0, 0)
            except Exception:
                pass

    def _run(self):
        hInstance = KERNEL32.GetModuleHandleW(None)
        class_name = "RawHoverRunnerHiddenWindow"

        wc = WNDCLASSEXW()
        wc.cbSize = ct.sizeof(WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = ct.cast(self._wndproc, wt.WPARAM)
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hInstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = class_name
        wc.hIconSm = None

        USER32.RegisterClassExW(ct.byref(wc))

        hwnd = USER32.CreateWindowExW(
            0, class_name, "RawHoverRunner",
            0, 0, 0, 0, 0,
            None, None, hInstance, None
        )
        self.hwnd = hwnd
        if not hwnd:
            return

        rid = RAWINPUTDEVICE()
        rid.usUsagePage = 0x01
        rid.usUsage = 0x02
        rid.dwFlags = RIDEV_INPUTSINK
        rid.hwndTarget = hwnd

        ok = USER32.RegisterRawInputDevices(ct.byref(rid), 1, ct.sizeof(RAWINPUTDEVICE))
        if not ok:
            return

        msg = MSG()
        while self._running:
            got = USER32.GetMessageW(ct.byref(msg), None, 0, 0)
            if got in (0, -1):
                break
            USER32.TranslateMessage(ct.byref(msg))
            USER32.DispatchMessageW(ct.byref(msg))

class Recorder:
    def __init__(self):
        self.state = "ready"  # ready, recording, paused
        self._lock = threading.Lock()
        self._count = 0
        self._meta: Meta | None = None
        self._file = None
        self._t0_ns = 0

        self.sink = RawMouseSink(self._on_raw_event)
        self.sink.start()

    def _on_raw_event(self, ev: dict):
        with self._lock:
            if self.state != "recording":
                return
            if not self._file:
                return
            self._file.write(json.dumps(ev, separators=(",", ":"), ensure_ascii=False) + "\n")
            self._file.flush()
            self._count += 1

    def start(self):
        with self._lock:
            if self.state == "recording":
                return
            stamp = now_stamp()
            out = OUT_DIR / f"hover_session_{stamp}"
            out.mkdir(parents=True, exist_ok=True)

            self._t0_ns = now_ns()
            self.sink.t0_ns = self._t0_ns
            self._count = 0

            log_path = out / "mouse_raw.jsonl"
            self._file = log_path.open("a", encoding="utf-8")

            self._meta = Meta(created=stamp, t0_ns=self._t0_ns, path=str(out))
            (out / "meta.json").write_text(json.dumps(asdict(self._meta), indent=2), encoding="utf-8")

            self.state = "recording"

    def pause(self):
        with self._lock:
            if self.state == "recording":
                self.state = "paused"

    def resume(self):
        with self._lock:
            if self.state == "paused":
                self.state = "recording"

    def stop_save(self):
        with self._lock:
            if self.state == "ready":
                return None
            dur = (now_ns() - self._t0_ns) / 1e9 if self._t0_ns else 0.0
            count = self._count
            path = self._meta.path if self._meta else None

            try:
                if self._file:
                    self._file.close()
            except Exception:
                pass
            self._file = None

            if path:
                meta_path = Path(path) / "meta.json"
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta["duration_sec"] = round(dur, 6)
                    meta["events_written"] = int(count)
                    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            self.state = "ready"
            return path

    def stats(self):
        with self._lock:
            st = self.state
            count = self._count
            dur = (now_ns() - self._t0_ns) / 1e9 if self._t0_ns else 0.0
        return st, dur, count

    def shutdown(self):
        try:
            self.sink.stop()
        except Exception:
            pass

# =========================
# UI
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RAW Hover Runner")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        self.rec = Recorder()

        pad = 10
        frm = ttk.Frame(self, padding=pad)
        frm.grid()

        self.status = tk.StringVar(value="🟡 Ready")
        self.timev = tk.StringVar(value="0.00s")
        self.countv = tk.StringVar(value="0")

        ttk.Label(frm, textvariable=self.status, font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        ttk.Label(frm, text="Time:").grid(row=1, column=0, sticky="e", padx=(0, 6))
        ttk.Label(frm, textvariable=self.timev, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(frm, text="Events:").grid(row=1, column=2, sticky="e", padx=(12, 6))
        ttk.Label(frm, textvariable=self.countv, width=10).grid(row=1, column=3, sticky="w")

        self.btn_play = ttk.Button(frm, text="▶ Play", command=self.on_play, width=12)
        self.btn_pause = ttk.Button(frm, text="⏸ Pause", command=self.on_pause, width=12)
        self.btn_stop = ttk.Button(frm, text="⏹ Stop+Save", command=self.on_stop, width=12)

        self.btn_play.grid(row=2, column=0, pady=(10, 0), sticky="ew")
        self.btn_pause.grid(row=2, column=1, pady=(10, 0), sticky="ew")
        self.btn_stop.grid(row=2, column=2, pady=(10, 0), sticky="ew")

        ttk.Label(frm, text="Tip: hover/click wat je wil, hij logt RAWINPUT.", foreground="#666").grid(
            row=3, column=0, columnspan=3, pady=(8, 0), sticky="w"
        )

        self.bind("<Escape>", lambda _e: self.on_quit())
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

        self._tick()

    def on_play(self):
        st, _, _ = self.rec.stats()
        if st == "paused":
            self.rec.resume()
        else:
            self.rec.start()

    def on_pause(self):
        self.rec.pause()

    def on_stop(self):
        path = self.rec.stop_save()
        if path:
            self.status.set(f"🟢 Saved: {Path(path).name}")

    def on_quit(self):
        try:
            self.rec.shutdown()
        finally:
            self.destroy()

    def _tick(self):
        st, dur, count = self.rec.stats()
        self.countv.set(str(count))
        if st == "recording":
            self.status.set("🔴 Recording...")
            self.timev.set(f"{dur:.2f}s")
        elif st == "paused":
            self.status.set("🟠 Paused")
            self.timev.set(f"{dur:.2f}s")
        else:
            if not self.status.get().startswith("🟢 Saved"):
                self.status.set("🟡 Ready")
            self.timev.set("0.00s")
        self.after(50, self._tick)

if __name__ == "__main__":
    App().mainloop()