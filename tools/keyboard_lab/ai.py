from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

# Key classes: compact maar krachtig
KEY_CLASS_ALPHA = "alpha"
KEY_CLASS_DIGIT = "digit"
KEY_CLASS_PUNCT = "punct"
KEY_CLASS_SPACE = "space"
KEY_CLASS_EDIT  = "edit"
KEY_CLASS_NAV   = "nav"
KEY_CLASS_ENTER = "enter"
KEY_CLASS_MOD   = "mod"
KEY_CLASS_FUNC  = "func"
KEY_CLASS_OTHER = "other"

# We normaliseren keys naar strings die stabiel loggen
SPECIAL_MAP = {
    "Key.esc": "esc",
    "Key.enter": "enter",
    "Key.tab": "tab",
    "Key.space": "space",
    "Key.shift": "shift",
    "Key.shift_l": "shift",
    "Key.shift_r": "shift",
    "Key.ctrl": "ctrl",
    "Key.ctrl_l": "ctrl",
    "Key.ctrl_r": "ctrl",
    "Key.alt": "alt",
    "Key.alt_l": "alt",
    "Key.alt_r": "alt",
    "Key.cmd": "cmd",
    "Key.cmd_l": "cmd",
    "Key.cmd_r": "cmd",
    "Key.backspace": "backspace",
    "Key.delete": "delete",
    "Key.up": "up",
    "Key.down": "down",
    "Key.left": "left",
    "Key.right": "right",
    "Key.home": "home",
    "Key.end": "end",
    "Key.page_up": "page_up",
    "Key.page_down": "page_down",
    "Key.insert": "insert",
}

MODIFIERS = {"shift", "ctrl", "alt", "cmd"}
EDIT_KEYS = {"backspace", "delete"}
NAV_KEYS = {"up", "down", "left", "right", "home", "end", "page_up", "page_down"}
ENTER_KEYS = {"enter"}
SPACE_KEYS = {"space"}
FUNC_PREFIX = "f"  # f1..f24

PUNCT = set(r"""`~!@#$%^&*()-_=+[{]}\|;:'",<.>/?""")

def normalize_key(key) -> str:
    """
    pynput key -> stable string
    """
    try:
        s = str(key)
    except Exception:
        return "unknown"

    if s in SPECIAL_MAP:
        return SPECIAL_MAP[s]

    # KeyCode('a') style
    # str(key) kan "'a'" zijn
    if len(s) >= 3 and s[0] == "'" and s[-1] == "'":
        ch = s[1:-1]
        return ch

    # fallback
    return s.replace("Key.", "").strip().lower()

def key_class(key_str: str) -> str:
    k = (key_str or "").lower()

    if k in MODIFIERS:
        return KEY_CLASS_MOD
    if k in EDIT_KEYS:
        return KEY_CLASS_EDIT
    if k in NAV_KEYS:
        return KEY_CLASS_NAV
    if k in ENTER_KEYS:
        return KEY_CLASS_ENTER
    if k in SPACE_KEYS:
        return KEY_CLASS_SPACE

    if len(k) == 1 and k.isalpha():
        return KEY_CLASS_ALPHA
    if len(k) == 1 and k.isdigit():
        return KEY_CLASS_DIGIT
    if len(k) == 1 and k in PUNCT:
        return KEY_CLASS_PUNCT

    # f1..f24
    if k.startswith(FUNC_PREFIX) and k[1:].isdigit():
        return KEY_CLASS_FUNC

    return KEY_CLASS_OTHER