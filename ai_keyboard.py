from __future__ import annotations

# =========================
# === IMPORTS ============
# =========================
import random
import time
from pynput.keyboard import Controller, Key

keyboard = Controller()

# =========================
# === TIMING RANGES ======
# =========================
PRESS_DELAY_RANGE = (0.015, 0.045)     # korte tik
HOLD_DELAY_RANGE  = (0.18, 0.35)       # normale hold
TYPE_INTERVAL_RANGE = (0.025, 0.055)   # typen

def _rand_range(rng):
    return random.uniform(rng[0], rng[1])

# =========================
# === BASIC KEY ACTIONS ==
# =========================
def press_key(key, delay=None):
    k = _resolve_key(key)
    keyboard.press(k)

    if delay is None:
        time.sleep(_rand_range(PRESS_DELAY_RANGE))
    else:
        time.sleep(float(delay))

    keyboard.release(k)


def hold_key(key, hold_time=None):
    k = _resolve_key(key)
    keyboard.press(k)

    if hold_time is None:
        time.sleep(_rand_range(HOLD_DELAY_RANGE))
    else:
        time.sleep(float(hold_time))

    keyboard.release(k)


def hold_key_range(key, min_sec, max_sec):
    hold_key(key, random.uniform(min_sec, max_sec))


def type_text(text, interval=None):
    for ch in text:
        keyboard.type(ch)
        if interval is None:
            time.sleep(_rand_range(TYPE_INTERVAL_RANGE))
        else:
            time.sleep(float(interval))


# =========================
# === HUMAN TYPE TEXT ====
# =========================
_NEIGHBORS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "ersfcx", "e": "wsdr",
    "f": "rtgdvc", "g": "tyfhvb", "h": "yugjbn", "i": "ujko",
    "j": "uikhmn", "k": "ijolm", "l": "kop", "m": "njk",
    "n": "bhjm", "o": "iklp", "p": "ol", "q": "wa", "r": "edft",
    "s": "wedxza", "t": "rfgy", "u": "yhji", "v": "cfgb",
    "w": "qase", "x": "zsdc", "y": "tghu", "z": "asx",
}

def type_text_human(
    text,
    *,
    base_interval=0.08,
    jitter=0.05,
    pause_chance=0.08,
    pause_range=(0.15, 0.55),
    mistake_chance=0.03,
    correct_chance=0.85,
    extra_char_chance=0.01,
):
    for ch in text:
        _sleep_human(base_interval, jitter)

        if random.random() < pause_chance:
            time.sleep(random.uniform(*pause_range))

        if ch == "\n":
            press_key("enter")
            continue

        if _is_typable_letter(ch) and random.random() < mistake_chance:
            wrong = _make_mistake(ch)
            keyboard.type(wrong)
            _sleep_human(base_interval * 0.8, jitter)

            if random.random() < extra_char_chance:
                keyboard.type(_make_mistake(ch))
                _sleep_human(base_interval * 0.7, jitter)

            if random.random() < correct_chance:
                press_key("backspace")
                if random.random() < 0.35:
                    press_key("backspace")
                _sleep_human(base_interval * 0.9, jitter)
                keyboard.type(ch)
            continue

        keyboard.type(ch)


# =========================
# === INTERNAL HELPERS ===
# =========================
def _sleep_human(base, jitter):
    t = max(0.0, base + random.uniform(-jitter, jitter))
    time.sleep(t)


def _is_typable_letter(ch):
    return len(ch) == 1 and ch.lower() in _NEIGHBORS and ch.isalpha()


def _make_mistake(ch):
    lower = ch.lower()
    options = _NEIGHBORS.get(lower, lower)
    wrong = random.choice(options)
    return wrong.upper() if ch.isupper() else wrong


def _resolve_key(key):
    if isinstance(key, Key):
        return key

    k = str(key).lower()
    special = {
        "esc": Key.esc,
        "escape": Key.esc,
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
    }
    return special.get(k, key)


# =========================
# === SELF TEST ==========
# =========================
if __name__ == "__main__":
    print("\n⌨️ ai_keyboard SELF TEST")
    time.sleep(2)

    press_key("esc")
    press_key("enter")

    hold_key("space")
    hold_key_range("up", 0.2, 0.6)

    type_text("Test 123")
    press_key("enter")

    type_text_human("Menselijk typen voelt nu natuurlijk 😄")
    press_key("enter")

    print("\n✅ klaar\n")
