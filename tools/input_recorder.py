from __future__ import annotations

import json
import sys
import time
import threading
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

from pynput import mouse, keyboard


# =========================
# PATHS
# =========================
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "recordings"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOCK_FILE = OUT_DIR / ".input_recorder.lock"

START_KEY = keyboard.Key.f7
STOP_KEY = keyboard.Key.f8


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _key_to_str(k) -> str:
    try:
        return k.char  # type: ignore[attr-defined]
    except Exception:
        return str(k).replace("Key.", "")


def _pick_python_exe() -> str:
    return sys.executable


def _acquire_lock(path: Path):
    try:
        import msvcrt
    except Exception:
        return None

    f = open(path, "a+", encoding="utf-8")
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        f.seek(0)
        f.truncate()
        f.write(str(Path(sys.argv[0]).resolve()))
        f.flush()
        return f
    except OSError:
        try:
            f.close()
        except Exception:
            pass
        return None


def _release_lock(f):
    if not f:
        return
    try:
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        pass
    try:
        f.close()
    except Exception:
        pass


# =========================
# EVENT MODEL
# =========================
@dataclass
class Event:
    t: float
    type: str
    x: int | None = None
    y: int | None = None

    # clicks
    button: str | None = None
    pressed: bool | None = None

    # keyboard
    key: str | None = None

    # scroll (vertical + horizontal)
    dx: int | None = None
    dy: int | None = None


class InputRecorder:
    def __init__(self) -> None:
        self.running = False
        self.t0 = 0.0
        self.events: list[Event] = []
        self._lock = threading.Lock()

        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._kb_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listeners_started = False

    def start_listeners(self) -> None:
        if self._listeners_started:
            return
        self._listeners_started = True
        self._mouse_listener.start()
        self._kb_listener.start()

    def stop_listeners(self) -> None:
        try:
            self._mouse_listener.stop()
        except Exception:
            pass
        try:
            self._kb_listener.stop()
        except Exception:
            pass

    def _t(self) -> float:
        return time.perf_counter() - self.t0

    def _push(self, e: Event) -> None:
        if not self.running:
            return
        with self._lock:
            self.events.append(e)

    # =========================
    # MOUSE
    # =========================
    def _on_move(self, x: int, y: int) -> None:
        self._push(Event(t=self._t(), type="mouse_move", x=int(x), y=int(y)))

    def _on_click(self, x: int, y: int, btn, pressed: bool) -> None:
        b = "right" if btn == mouse.Button.right else "left"
        self._push(
            Event(
                t=self._t(),
                type="mouse_click",
                x=int(x),
                y=int(y),
                button=b,
                pressed=bool(pressed),
            )
        )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        dx = int(dx)
        dy = int(dy)

        # skip ruis (dit zag je in je logs)
        if dx == 0 and dy == 0:
            return

        self._push(
            Event(
                t=self._t(),
                type="mouse_scroll",
                x=int(x),
                y=int(y),
                dx=dx,
                dy=dy,
            )
        )

    # =========================
    # KEYBOARD
    # =========================
    def _on_press(self, k) -> None:
        if k == START_KEY and not self.running:
            self.start()
            return
        if k == STOP_KEY and self.running:
            self.stop_and_save()
            return

        self._push(Event(t=self._t(), type="key", key=_key_to_str(k), pressed=True))

    def _on_release(self, k) -> None:
        self._push(Event(t=self._t(), type="key", key=_key_to_str(k), pressed=False))

    # =========================
    # CONTROL
    # =========================
    def start(self) -> None:
        self.running = True
        self.t0 = time.perf_counter()
        with self._lock:
            self.events.clear()

    def stop_and_save(self) -> Path | None:
        if not self.running:
            return None

        self.running = False
        with self._lock:
            duration = self.events[-1].t if self.events else 0.0
            events_copy = list(self.events)

        payload = {
            "meta": {
                "created": _now_stamp(),
                "duration_sec": round(duration, 6),
                "start_key": "F7",
                "stop_key": "F8",
                "events": len(events_copy),
            },
            "events": [asdict(e) for e in events_copy],
        }

        out = OUT_DIR / f"input_log_{payload['meta']['created']}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out

    def stats(self) -> tuple[bool, float, int]:
        with self._lock:
            n = len(self.events)
        elapsed = (time.perf_counter() - self.t0) if self.running else 0.0
        return self.running, elapsed, n


class RecorderUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Input Recorder")
        self.resizable(False, False)

        self.rec = InputRecorder()
        self.rec.start_listeners()

        pad = 12
        frm = ttk.Frame(self, padding=pad)
        frm.grid()

        self.status_var = tk.StringVar(value="🟡 Ready")
        self.time_var = tk.StringVar(value="0.00s")
        self.count_var = tk.StringVar(value="0")

        ttk.Label(frm, textvariable=self.status_var, font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w"
        )

        ttk.Label(frm, text="Time:").grid(row=1, column=0, sticky="e", padx=(0, 6))
        ttk.Label(frm, textvariable=self.time_var, width=10).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Events:").grid(row=1, column=2, sticky="e", padx=(12, 6))
        ttk.Label(frm, textvariable=self.count_var, width=10).grid(row=1, column=3, sticky="w")

        self.btn_start = ttk.Button(frm, text="⏺ Start (F7)", command=self.on_start, width=18)
        self.btn_stop = ttk.Button(frm, text="⏹ Stop + Save (F8)", command=self.on_stop, width=18)

        self.btn_start.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        self.btn_stop.grid(row=2, column=2, columnspan=2, pady=(10, 0), sticky="ew")

        self.btn_stop.state(["disabled"])

        ttk.Label(frm, text="Tip: F7 start • F8 stop+save • ESC = quit", foreground="#666").grid(
            row=3, column=0, columnspan=4, pady=(10, 0), sticky="w"
        )

        self.bind("<Escape>", lambda _e: self.on_quit())
        self.protocol("WM_DELETE_WINDOW", self.on_quit)

        self._tick()

    def on_start(self) -> None:
        if self.rec.running:
            return
        self.rec.start()
        self.status_var.set("🔴 Recording...")
        self.btn_start.state(["disabled"])
        self.btn_stop.state(["!disabled"])

    def on_stop(self) -> None:
        out = self.rec.stop_and_save()
        self.btn_start.state(["!disabled"])
        self.btn_stop.state(["disabled"])
        self.status_var.set("🟢 Saved" if out else "🟡 Ready")
        if out:
            messagebox.showinfo("Saved", f"🧾 Saved:\n{out}")

    def on_quit(self) -> None:
        try:
            self.rec.running = False
            self.rec.stop_listeners()
        finally:
            self.destroy()

    def _tick(self) -> None:
        running, elapsed, count = self.rec.stats()
        self.count_var.set(str(count))
        if running:
            self.time_var.set(f"{elapsed:.2f}s")
        else:
            self.time_var.set("0.00s")
        self.after(50, self._tick)


def start_child_and_exit():
    py = _pick_python_exe()
    script = str(Path(__file__).resolve())
    create_flag = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    subprocess.Popen([py, script, "child"], creationflags=create_flag, close_fds=True)
    raise SystemExit


def launcher_ui():
    root = tk.Tk()
    root.title("Recorder Launcher")
    root.resizable(False, False)

    ttk.Label(root, text="Start 1 recorder instance in een eigen console.").grid(
        row=0, column=0, padx=12, pady=(12, 6)
    )

    def go():
        root.destroy()
        start_child_and_exit()

    ttk.Button(root, text="Start Recorder", command=go).grid(
        row=1, column=0, padx=12, pady=(0, 12), sticky="ew"
    )
    root.mainloop()


if __name__ == "__main__":
    import signal

    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception:
        pass

    if len(sys.argv) == 1:
        launcher_ui()
        raise SystemExit

    if sys.argv[1] != "child":
        raise SystemExit("Onbekende args")

    lock_handle = _acquire_lock(LOCK_FILE)
    if lock_handle is None:
        try:
            messagebox.showwarning("Already running", "🟡 Input Recorder draait al.")
        except Exception:
            pass
        raise SystemExit

    try:
        ui = RecorderUI()
        ui.mainloop()
    finally:
        _release_lock(lock_handle)
