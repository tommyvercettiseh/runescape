from __future__ import annotations

import sys
import time
import threading
from queue import Queue, Empty
from pathlib import Path

import tkinter as tk
from pynput import mouse, keyboard

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_cursor_movement import random_mouse_movements
from tools.ai_cursor_movement_experimental import experimental_random_mouse_movements


COLOR_PRESETS = {
    "red": "#ff2d2d",
    "green": "#29ff6a",
    "lime": "#b6ff3b",
    "cyan": "#2df0ff",
}


def _arg_value(argv: list[str], *keys: str, default=None):
    for i, a in enumerate(argv):
        if a in keys and i + 1 < len(argv):
            return argv[i + 1]
    return default


def _pick_color(argv: list[str]) -> str:
    raw = _arg_value(argv, "-c", "--color", default="green")
    return COLOR_PRESETS.get(str(raw).lower(), str(raw))


class MouseTraceUI(tk.Tk):
    def __init__(self, *, color: str) -> None:
        super().__init__()

        self.title("Mouse Movement Trace (ESC to quit)")
        self.attributes("-topmost", True)
        self.attributes("-fullscreen", True)
        self.configure(bg="black")
        self.attributes("-transparentcolor", "black")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.color = color
        self.queue: Queue[tuple[int, int] | None] = Queue()
        self._last_pt: tuple[int, int] | None = None
        self._last_draw_ts = 0.0

        self.bind("<Escape>", lambda _e: self._quit())
        self.protocol("WM_DELETE_WINDOW", self._quit)

        self._start_listeners()
        self.after(8, self._drain)

    def _start_listeners(self) -> None:
        self._mouse_listener = mouse.Listener(on_move=self._on_move)
        self._kb_listener = keyboard.Listener(on_press=self._on_key)
        self._mouse_listener.start()
        self._kb_listener.start()

    def _on_key(self, k) -> None:
        if k == keyboard.Key.esc:
            self.queue.put(None)

    def _on_move(self, x: int, y: int) -> None:
        self.queue.put((int(x), int(y)))

    def _drain(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                if item is None:
                    self._quit()
                    return
                self._draw_point(item)
        except Empty:
            pass
        self.after(8, self._drain)

    def _draw_point(self, pt: tuple[int, int]) -> None:
        now = time.perf_counter()
        if now - self._last_draw_ts < 0.006:
            return
        self._last_draw_ts = now

        if self._last_pt is None:
            self._last_pt = pt
            return

        x1, y1 = self._last_pt
        x2, y2 = pt
        self.canvas.create_line(x1, y1, x2, y2, fill=self.color, width=2)
        self._last_pt = pt

    def _quit(self) -> None:
        try:
            self._mouse_listener.stop()
        except Exception:
            pass
        try:
            self._kb_listener.stop()
        except Exception:
            pass
        self.destroy()


def _run_movement(*, area: str, bot_id: int, min_s: float, max_s: float, mode: str) -> None:
    try:
        if mode == "exp":
            experimental_random_mouse_movements(min_s, max_s, area, bot_id=bot_id, verbose=True)
        else:
            random_mouse_movements(min_s, max_s, area, bot_id=bot_id, verbose=True)
    except Exception as e:
        print(f"❌ movement error: {type(e).__name__}: {e}")


def main() -> None:
    argv = sys.argv[1:]
    color = _pick_color(argv)
    area = _arg_value(argv, "-a", "--area", default="Bot_Area_Full")
    bot_id = int(_arg_value(argv, "-b", "--bot", default="1"))
    min_s = float(_arg_value(argv, "--min", default="2.0"))
    max_s = float(_arg_value(argv, "--max", default="6.0"))
    mode = str(_arg_value(argv, "-m", "--mode", default="exp")).lower()

    print(f"[Trace] mode={mode} area={area} bot={bot_id} {min_s}-{max_s}s | ESC to quit")

    t = threading.Thread(
        target=_run_movement,
        kwargs={"area": area, "bot_id": bot_id, "min_s": min_s, "max_s": max_s, "mode": mode},
        daemon=True,
    )
    t.start()

    ui = MouseTraceUI(color=color)
    ui.mainloop()


if __name__ == "__main__":
    main()
