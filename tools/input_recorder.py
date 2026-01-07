from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

from pynput import mouse, keyboard


OUT_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

START_KEY = keyboard.Key.f7
STOP_KEY = keyboard.Key.f8


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _key_to_str(k) -> str:
    try:
        return k.char  # type: ignore[attr-defined]
    except Exception:
        return str(k).replace("Key.", "")


@dataclass
class Event:
    t: float
    type: str
    x: int | None = None
    y: int | None = None
    button: str | None = None
    pressed: bool | None = None
    key: str | None = None


class InputRecorder:
    def __init__(self) -> None:
        self.running = False
        self.t0 = 0.0
        self.events: list[Event] = []

        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._kb_listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )

    def _t(self) -> float:
        return time.perf_counter() - self.t0

    def _push(self, e: Event) -> None:
        if self.running:
            self.events.append(e)

    def _on_move(self, x: int, y: int) -> None:
        self._push(Event(t=self._t(), type="mouse_move", x=int(x), y=int(y)))

    def _on_click(self, x: int, y: int, btn, pressed: bool) -> None:
        b = "right" if btn == mouse.Button.right else "left"
        self._push(Event(t=self._t(), type="mouse_click", x=int(x), y=int(y), button=b, pressed=bool(pressed)))

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        # geen middle button gedoe, scroll is gewoon info
        self._push(Event(t=self._t(), type="mouse_scroll", x=int(x), y=int(y), button=f"dy={dy}", pressed=None))

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

    def start(self) -> None:
        self.running = True
        self.t0 = time.perf_counter()
        self.events.clear()
        print("⏺️ Recording START (F7) | Stop = F8")

    def stop_and_save(self) -> None:
        self.running = False
        duration = self.events[-1].t if self.events else 0.0

        payload = {
            "meta": {
                "created": _now_stamp(),
                "duration_sec": round(duration, 6),
                "start_key": "F7",
                "stop_key": "F8",
                "events": len(self.events),
            },
            "events": [asdict(e) for e in self.events],
        }

        out = OUT_DIR / f"input_log_{payload['meta']['created']}.json"
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"🧾 Saved: {out}")

    def run(self) -> None:
        print("🟡 Input recorder ready")
        print("F7 = start | F8 = stop+save | (global, werkt ook als window niet actief is)")
        self._mouse_listener.start()
        self._kb_listener.start()
        self._mouse_listener.join()
        self._kb_listener.join()


if __name__ == "__main__":
    InputRecorder().run()
