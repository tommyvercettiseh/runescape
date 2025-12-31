from __future__ import annotations

# =========================
# === IMPORTS ============
# =========================
import random
import time
from pynput.keyboard import Controller, Key

keyboard = Controller()

# =========================
# === BASIC KEY ACTIONS ===
# =========================
def press_key(key, delay: float = 0.02):
    k = _resolve_key(key)
    keyboard.press(k)
    time.sleep(float(delay))
    keyboard.release(k)


def hold_key(key, hold_time: float = 0.2):
    k = _resolve_key(key)
    keyboard.press(k)
    time.sleep(float(hold_time))
    keyboard.release(k)


def type_text(text: str, interval: float = 0.03):
    for ch in text:
        keyboard.type(ch)
        time.sleep(float(interval))


# =========================
# === HUMAN TYPE TEXT =====
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
    text: str,
    *,
    base_interval: float = 0.08,
    jitter: float = 0.05,
    pause_chance: float = 0.08,
    pause_range: tuple[float, float] = (0.15, 0.55),
    mistake_chance: float = 0.03,
    correct_chance: float = 0.85,
    extra_char_chance: float = 0.01
):
    """
    Typt tekst menselijk:
    • variatie in timing
    • af en toe typefout (naburige toets)
    • vaak corrigeren met backspace
    • soms extra char en herstellen
    """
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
                press_key("backspace", delay=0.01)
                if random.random() < 0.35:
                    press_key("backspace", delay=0.01)
                _sleep_human(base_interval * 0.9, jitter)
                keyboard.type(ch)
            continue

        keyboard.type(ch)


# =========================
# === INTERNAL HELPERS ====
# =========================
def _sleep_human(base: float, jitter: float):
    t = max(0.0, float(base) + random.uniform(-float(jitter), float(jitter)))
    time.sleep(t)


def _is_typable_letter(ch: str) -> bool:
    return len(ch) == 1 and ch.lower() in _NEIGHBORS and ch.isalpha()


def _make_mistake(ch: str) -> str:
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
# === SELF TEST ===========
# =========================
if __name__ == "__main__":
    print("\n⌨️ ai_keyboard SELF TEST")
    print("Niet typen of klikken 🙂\n")
    time.sleep(2)

    print("▶ press_key: ESC")
    press_key("esc")
    time.sleep(0.5)

    print("▶ press_key: ENTER")
    press_key("enter")
    time.sleep(0.5)

    print("▶ type_text_human:")
    type_text_human("Dit is een menselijk typ testje 😄", mistake_chance=0.04, pause_chance=0.06)
    press_key("enter")

    print("\n✅ klaar\n")
