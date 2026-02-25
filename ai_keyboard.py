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
PRESS_DELAY_RANGE = (0.015, 0.045)
HOLD_DELAY_RANGE = (0.18, 0.35)
TYPE_INTERVAL_RANGE = (0.025, 0.055)

def _rand_range(rng):
    return random.uniform(rng[0], rng[1])

# =========================
# === KEY RESOLVE ========
# =========================
def _resolve_key(key):

    if isinstance(key, Key):
        return key

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
    }

    return special.get(str(key).lower(), key)

# =========================
# === BASIC KEY ACTIONS ==
# =========================
def press_key(key, delay=None):
    k = _resolve_key(key)
    keyboard.press(k)
    time.sleep(float(delay) if delay else _rand_range(PRESS_DELAY_RANGE))
    keyboard.release(k)

def hold_key(key, hold_time=None):
    k = _resolve_key(key)
    keyboard.press(k)
    time.sleep(float(hold_time) if hold_time else _rand_range(HOLD_DELAY_RANGE))
    keyboard.release(k)

def hold_key_range(key, min_sec, max_sec):
    hold_key(key, random.uniform(min_sec, max_sec))

# =========================
# === HUMAN TYPE ENGINE ==
# =========================
_NEIGHBORS = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "ersfcx",
    "e": "wsdr", "f": "rtgdvc", "g": "tyfhvb", "h": "yugjbn",
    "i": "ujko", "j": "uikhmn", "k": "ijolm", "l": "kop",
    "m": "njk", "n": "bhjm", "o": "iklp", "p": "ol",
    "q": "wa", "r": "edft", "s": "wedxza", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc",
    "y": "tghu", "z": "asx",
}

def _sleep_human(base=0.08, jitter=0.05):
    time.sleep(max(0.0, base + random.uniform(-jitter, jitter)))

def _is_letter(ch):
    return len(ch) == 1 and ch.lower() in _NEIGHBORS and ch.isalpha()

def _mistake(ch):
    options = _NEIGHBORS.get(ch.lower(), ch.lower())
    wrong = random.choice(options)
    return wrong.upper() if ch.isupper() else wrong

def _type_human(text):
    for ch in text:

        _sleep_human()

        if random.random() < 0.08:
            time.sleep(random.uniform(0.15, 0.55))

        if ch == "\n":
            press_key("enter")
            continue

        if _is_letter(ch) and random.random() < 0.03:
            wrong = _mistake(ch)
            keyboard.type(wrong)
            _sleep_human(0.06, 0.04)

            if random.random() < 0.85:
                press_key("backspace")
                _sleep_human(0.07, 0.03)
                keyboard.type(ch)
            continue

        keyboard.type(ch)

# =========================
# === MAIN TYPE FUNCTION ==
# =========================
def type_text(
    *parts,
    human=True,
    enter=False,
    sep=" ",
    pick_random=True,
    join=False,
    force_lower=True,
):
    """
    Standaard:
        type_text("sup", "i'll hop")   -> kiest random één van deze
        type_text("yo")               -> typt "yo"

    Alles samen typen:
        type_text("sup", "i'll hop", join=True) -> "sup i'll hop"
    """

    if not parts:
        return False

    cleaned = [str(p) for p in parts if p is not None and str(p).strip() != ""]
    if not cleaned:
        return False

    if join:
        text = sep.join(cleaned)
    else:
        text = random.choice(cleaned) if (pick_random and len(cleaned) > 1) else cleaned[0]

    if force_lower:
        text = text.lower()

    if human:
        _type_human(text)
    else:
        for ch in text:
            keyboard.type(ch)
            time.sleep(_rand_range(TYPE_INTERVAL_RANGE))

    if enter:
        press_key("enter")

    return text

# =========================
# === RANDOM PHRASES =====
# =========================
PHASE_1 = [
    "sup", "what up", "yo", "you good", "all good?",
    "u there?", "hey", "hi", "still on?", "ready?"
]

PHASE_2 = [
    "yeah im good", "all smooth", "lol", "nice",
    "true", "no worries", "just grinding", "solid"
]

PHASE_1 = [p.lower() for p in PHASE_1]
PHASE_2 = [p.lower() for p in PHASE_2]

_LAST_PICK = {"phase1": None, "phase2": None}

def type_random_phrase(phase=1, human=True, enter=True, avoid_repeat=True):

    if phase == 1:
        lines = PHASE_1
        key = "phase1"
    elif phase == 2:
        lines = PHASE_2
        key = "phase2"
    else:
        raise ValueError("phase moet 1 of 2 zijn")

    chosen = random.choice(lines)

    if avoid_repeat and len(lines) > 1:
        last = _LAST_PICK.get(key)
        tries = 0
        while chosen == last and tries < 10:
            chosen = random.choice(lines)
            tries += 1

    type_text(chosen, human=human, enter=enter, pick_random=False, force_lower=True)
    _LAST_PICK[key] = chosen
    return chosen

# =========================
# === SELF TEST ==========
# =========================
if __name__ == "__main__":

    print("⌨️ TEST START")
    time.sleep(2)

    type_text("SUP", "I'LL HOP", enter=True)          # random 1 van de 2, altijd lower
    time.sleep(1)

    type_text("SUP", "I'LL HOP", join=True, enter=True)  # alles samen
    time.sleep(1)

    type_random_phrase(phase=1)
    time.sleep(1)
    type_random_phrase(phase=2)

    print("✅ klaar")
