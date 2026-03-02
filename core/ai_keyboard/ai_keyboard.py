from __future__ import annotations

import random
import time
from typing import Optional

from .ai_keyboard_settings import get_keyboard_config
from .ai_keyboard_executor import KeyboardExecutor, resolve_key


_NEIGHBORS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "ersfcx",
    "e": "wsdr", "f": "rtgdvc", "g": "tyfhvb", "h": "yugjbn",
    "i": "ujko", "j": "uikhmn", "k": "ijolm", "l": "kop",
    "m": "njk", "n": "bhjm", "o": "iklp", "p": "ol",
    "q": "wa", "r": "edft", "s": "wedxza", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc",
    "y": "tghu", "z": "asx",
}

def _r(a: float, b: float) -> None:
    time.sleep(random.uniform(float(a), float(b)))

def press_key(key, *, executor: Optional[KeyboardExecutor] = None, scenario_label: Optional[str] = None) -> None:
    ex = executor or KeyboardExecutor()
    cfg = get_keyboard_config(scenario_label).behavior
    k = resolve_key(key)
    ex.press(k)
    _r(cfg.press_min_s, cfg.press_max_s)
    ex.release(k)

def hold_key(key, *, executor: Optional[KeyboardExecutor] = None, hold_s: Optional[float] = None, scenario_label: Optional[str] = None) -> None:
    ex = executor or KeyboardExecutor()
    cfg = get_keyboard_config(scenario_label).behavior
    k = resolve_key(key)
    ex.press(k)
    if hold_s is None:
        hold_s = random.uniform(cfg.hold_min_s, cfg.hold_max_s)
    time.sleep(float(hold_s))
    ex.release(k)

def combo(*keys, executor: Optional[KeyboardExecutor] = None, scenario_label: Optional[str] = None) -> None:
    """
    combo("ctrl","c") -> presses ctrl down, taps c, releases ctrl
    """
    ex = executor or KeyboardExecutor()
    cfg = get_keyboard_config(scenario_label).behavior

    resolved = [resolve_key(k) for k in keys]
    if not resolved:
        return

    # press modifiers first
    for k in resolved[:-1]:
        ex.press(k)
        _r(cfg.press_min_s * 0.6, cfg.press_max_s * 0.9)

    # tap last key
    last = resolved[-1]
    ex.press(last)
    _r(cfg.press_min_s, cfg.press_max_s)
    ex.release(last)

    # release modifiers reverse
    for k in reversed(resolved[:-1]):
        _r(cfg.press_min_s * 0.5, cfg.press_max_s * 0.8)
        ex.release(k)

def _mistake_char(ch: str) -> str:
    opts = _NEIGHBORS.get(ch.lower(), ch.lower())
    wrong = random.choice(list(opts)) if opts else ch.lower()
    return wrong.upper() if ch.isupper() else wrong

def type_text(
    *parts: str,
    executor: Optional[KeyboardExecutor] = None,
    human: bool = True,
    enter: bool = False,
    sep: str = " ",
    join: bool = False,
    pick_random: bool = True,
    force_lower: Optional[bool] = None,
    scenario_label: Optional[str] = None,
) -> Optional[str]:
    if not parts:
        return None

    ex = executor or KeyboardExecutor()
    cfg = get_keyboard_config(scenario_label).behavior

    cleaned = [str(p) for p in parts if p is not None and str(p).strip() != ""]
    if not cleaned:
        return None

    text = sep.join(cleaned) if join else (random.choice(cleaned) if (pick_random and len(cleaned) > 1) else cleaned[0])

    if force_lower is None:
        force_lower = bool(cfg.force_lower_default)
    if force_lower:
        text = text.lower()

    if not human:
        for ch in text:
            ex.type(ch)
            _r(cfg.type_interval_min_s, cfg.type_interval_max_s)
        if enter:
            press_key("enter", executor=ex, scenario_label=scenario_label)
        return text

    # human typing driven by profile
    for ch in text:
        _r(cfg.type_interval_min_s * 0.85, cfg.type_interval_max_s * 1.15)

        if random.random() < float(cfg.pause_chance):
            _r(cfg.pause_min_s, cfg.pause_max_s)

        if ch == "\n":
            press_key("enter", executor=ex, scenario_label=scenario_label)
            continue

        # optional typo model
        if len(ch) == 1 and ch.isalpha() and random.random() < float(cfg.mistake_chance):
            wrong = _mistake_char(ch)
            ex.type(wrong)
            _r(cfg.type_interval_min_s * 0.7, cfg.type_interval_max_s * 1.1)

            if random.random() < float(cfg.mistake_fix_chance):
                press_key("backspace", executor=ex, scenario_label=scenario_label)
                _r(cfg.type_interval_min_s * 0.7, cfg.type_interval_max_s * 1.1)
                ex.type(ch)
            continue

        ex.type(ch)

    if enter:
        press_key("enter", executor=ex, scenario_label=scenario_label)

    return text

if __name__ == "__main__":
    print("⌨️ ai_keyboard test in 2s...")
    time.sleep(2)
    type_text("yo", "ik test even", enter=True)
    combo("ctrl", "a")