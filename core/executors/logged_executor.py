from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Protocol, Tuple, Optional

Point = Tuple[int, int]

class MouseExecutor(Protocol):
    def get_pos(self) -> Point: ...
    def move_abs(self, x: int, y: int) -> None: ...
    def click(self, button: str) -> None: ...

@dataclass
class LogEvent:
    t: float
    src: str
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    dx: Optional[int] = None
    dy: Optional[int] = None
    button: Optional[str] = None

class LoggedExecutor:
    """
    Wrapper om elke executor heen.
    Logt ALLES wat jouw bot uitvoert.
    Output: jsonl (1 event per regel)
    """
    def __init__(self, base: MouseExecutor, out_file: str | Path, src: str = "bot"):
        self.base = base
        self.out_file = Path(out_file)
        self.src = src
        self.out_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(self, e: LogEvent) -> None:
        with self.out_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    def get_pos(self) -> Point:
        return self.base.get_pos()

    def move_abs(self, x: int, y: int) -> None:
        cx, cy = self.get_pos()
        self._log(LogEvent(
            t=time.perf_counter(),
            src=self.src,
            type="move",
            x=int(x), y=int(y),
            dx=int(x) - int(cx),
            dy=int(y) - int(cy),
        ))
        self.base.move_abs(int(x), int(y))

    def click(self, button: str) -> None:
        self._log(LogEvent(
            t=time.perf_counter(),
            src=self.src,
            type="click",
            button=button,
        ))
        self.base.click(button)
