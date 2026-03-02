from __future__ import annotations

from typing import Optional
from pynput.keyboard import Controller, Key

class KeyboardExecutor:
    def __init__(self, controller: Optional[Controller] = None):
        self.kb = controller or Controller()

    def press(self, key):
        self.kb.press(key)

    def release(self, key):
        self.kb.release(key)

    def type(self, text: str):
        self.kb.type(text)

def resolve_key(key):
    if isinstance(key, Key):
        return key

    k = str(key).strip().lower()
    special = {
        "esc": Key.esc,
        "enter": Key.enter,
        "tab": Key.tab,
        "space": Key.space,
        "shift": Key.shift,
        "ctrl": Key.ctrl,
        "alt": Key.alt,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "home": Key.home,
        "end": Key.end,
        "page_up": Key.page_up,
        "page_down": Key.page_down,
        "insert": Key.insert,
    }
    return special.get(k, k)