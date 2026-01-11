from __future__ import annotations

import time
from typing import Tuple, Optional
import serial

Point = Tuple[int, int]


class ArduinoExecutor:
    """
    PC-side executor.
    Stuurt commando's naar Arduino via serial.

    Protocol (matcht jouw .ino):
      move:  "dx;dy\n"
      left:  "l\n"
      right: "r\n"

    Let op:
    Arduino weet geen absolute positie.
    Daarom rekenen we dx/dy op de PC door current cursor pos te lezen.
    """

    def __init__(self, port: str = "COM6", baud: int = 115200, timeout: float = 0.1, settle_s: float = 0.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.settle_s = settle_s

        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(1.2)  # Arduino reset vaak bij connect

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass

    def get_pos(self) -> Point:
        # Arduino weet dit niet, dus PC leest het
        import pyautogui
        x, y = pyautogui.position()
        return int(x), int(y)

    def _write_line(self, s: str) -> None:
        self.ser.write(s.encode("ascii", errors="ignore"))
        if self.settle_s:
            time.sleep(self.settle_s)

    def move_abs(self, x: int, y: int) -> None:
        cx, cy = self.get_pos()
        dx = int(x) - int(cx)
        dy = int(y) - int(cy)

        if dx == 0 and dy == 0:
            return

        # jouw Arduino sketch gebruikt "x;y"
        self._write_line(f"{dx};{dy}\n")

    def click(self, button: str = "left") -> None:
        if button == "right":
            self._write_line("r\n")
        else:
            self._write_line("l\n")
