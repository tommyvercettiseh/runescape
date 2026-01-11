from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from pynput import mouse

@dataclass
class HWEvent:
    t: float
    src: str
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None
    pressed: Optional[bool] = None

class HardwareRecorder:
    def __init__(self, out_file: str | Path, src: str = "hw", log_moves: bool = True):
        self.out_file = Path(out_file)
        self.src = src
        self.log_moves = log_moves
        self.out_file.parent.mkdir(parents=True, exist_ok=True)
        self.listener: mouse.Listener | None = None

    def _log(self, e: HWEvent) -> None:
        with self.out_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    def start(self) -> "HardwareRecorder":
        def on_move(x, y):
            if self.log_moves:
                self._log(HWEvent(t=time.perf_counter(), src=self.src, type="move", x=int(x), y=int(y)))

        def on_click(x, y, button, pressed):
            self._log(HWEvent(
                t=time.perf_counter(),
                src=self.src,
                type="click",
                x=int(x), y=int(y),
                button=str(button).replace("Button.", ""),
                pressed=bool(pressed),
            ))

        self.listener = mouse.Listener(on_move=on_move, on_click=on_click)
        self.listener.start()
        return self

    def stop(self) -> None:
        if self.listener:
            self.listener.stop()
            self.listener = None
