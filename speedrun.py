# ============================================================
# CURSOR SIMULATOR — MENSELIJK GEDRAG (SPEEDRUN)
# ============================================================
#
# WAT DOET DIT SCRIPT?
# --------------------
# Dit script beweegt de ECHTE muis op een mensachtige manier:
# - niet recht
# - niet constant
# - soms stoppen
# - soms mini terug
#
# Alles wordt opgeslagen in JSON met "menselijke tijd",
# terwijl het script zelf supersnel runt (speedrun).
#
# Doel:
# - 5 uur menselijk cursor-gedrag
# - gegenereerd in ±2–3 minuten
# - data blijft realistisch en herleidbaar
#
# ============================================================


# ------------------------------------------------------------
# BOOTSTRAP
# Zorgt dat imports vanuit project-root blijven werken
# ------------------------------------------------------------

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------
# IMPORTS
# Alleen wat echt nodig is
# ------------------------------------------------------------

import time
import random
import json
from datetime import datetime
from pynput.mouse import Controller
import pyautogui


# ------------------------------------------------------------
# RECORDER
# Houdt "menselijke tijd" bij, los van echte runtime
#
# Belangrijk:
# - time.sleep wordt gespeedrund
# - maar dt (menselijke tijd) blijft correct
# ------------------------------------------------------------

class CursorRecorder:
    def __init__(self):
        self.time = 0          # totale menselijke tijd in seconden
        self.moves = []        # alle cursorpunten

    def log(self, x, y, dt):
        # dt = hoeveel tijd dit menselijk zou duren
        self.time += dt
        self.moves.append({
            "t": round(self.time, 5),
            "x": x,
            "y": y
        })

    def save(self, speedrun):
        # automatisch bestand met datum + tijd
        name = datetime.now().strftime("cursor_log_%Y-%m-%d_%H-%M-%S.json")

        with open(name, "w") as f:
            json.dump({
                "meta": {
                    "hours_simulated": round(self.time / 3600, 2),
                    "speedrun_factor": speedrun,
                    "points": len(self.moves)
                },
                "moves": self.moves
            }, f, indent=2)

        print(f"\n💾 Log opgeslagen: {name}")
        print(f"📍 Punten: {len(self.moves):,}")


# ------------------------------------------------------------
# HULPFUNCTIES
# ------------------------------------------------------------

def ease(t):
    # Zorgt dat beweging langzaam start en eindigt
    if t < 0.5:
        return 2 * t * t
    return 1 - ((-2 * t + 2) ** 2) / 2


def bezier(ax, ay, bx, by, cx, cy, t):
    # Simpele Bézier-bocht (mens beweegt nooit recht)
    x = (1 - t)**2 * ax + 2*(1 - t)*t * bx + t*t * cx
    y = (1 - t)**2 * ay + 2*(1 - t)*t * by + t*t * cy
    return x, y


def countdown(seconds):
    # 1 regel countdown, geen spam
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    print(f"\r⏳ Bezig — resterend {h:02d}:{m:02d}:{s:02d}", end="")


# ------------------------------------------------------------
# MOVE CURSOR (HART VAN HET SCRIPT)
#
# Dit doet:
# - menselijk pad (bocht)
# - soms stoppen (trackpad swipe)
# - soms mini terug
# - LAATSTE 5% altijd exact eindpunt
# ------------------------------------------------------------

def move_cursor(to_x, to_y, recorder, speedrun):
    mouse = Controller()
    from_x, from_y = mouse.position

    # Hoe lang deze beweging menselijk duurt
    duration = random.uniform(0.35, 0.55)

    # Hoeveel kleine stapjes we maken
    steps = int(duration * 120)
    step_time = duration / steps

    # Middenpunt voor bocht
    mid_x = from_x + (to_x - from_x) * random.uniform(0.3, 0.7)
    mid_y = from_y + (to_y - from_y) * random.uniform(0.3, 0.7)

    stop_done = False
    back_done = False

    for i in range(steps):
        t = (i + 1) / steps

        # Laatste 5% = exact doel (belangrijk voor click_image!)
        if t > 0.95:
            x, y = to_x, to_y
        else:
            x, y = bezier(
                from_x, from_y,
                mid_x + random.randint(-60, 60),
                mid_y + random.randint(-60, 60),
                to_x, to_y,
                ease(t)
            )

            # kleine handtrilling
            x += random.uniform(-0.7, 0.7)
            y += random.uniform(-0.7, 0.7)

            # Soms even stoppen (laptop swipe)
            if not stop_done and random.random() < 0.15 and 0.25 < t < 0.7:
                pause = random.uniform(0.06, 0.18)
                time.sleep(pause / speedrun)
                recorder.time += pause
                stop_done = True

            # Soms mini terug en weer door
            if not back_done and random.random() < 0.10 and 0.35 < t < 0.75:
                mouse.position = (
                    int(x - random.randint(4, 8)),
                    int(y - random.randint(4, 8))
                )
                pause = random.uniform(0.02, 0.05)
                time.sleep(pause / speedrun)
                recorder.log(int(x), int(y), pause)
                back_done = True

        mouse.position = (int(x), int(y))

        # Menselijke tijd voor dit stapje
        human_dt = step_time * random.uniform(0.7, 1.4)

        # Speedrun slaap
        time.sleep(human_dt / speedrun)

        # Log menselijke tijd
        recorder.log(int(x), int(y), human_dt)

    # Eindpunt altijd exact
    mouse.position = (to_x, to_y)
    recorder.log(to_x, to_y, 0)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

if __name__ == "__main__":
    print("\n🚀 Cursor simulatie gestart")
    print("🧠 Menselijk gedrag • ⚡ Supersnel • 📊 Herleidbaar\n")

    SPEEDRUN = 120          # hoger = sneller runtime
    TARGET_SECONDS = 5 * 3600   # 5 uur menselijke tijd

    recorder = CursorRecorder()
    screen_w, screen_h = pyautogui.size()
    margin = 50

    try:
        while recorder.time < TARGET_SECONDS:
            x = random.randint(margin, screen_w - margin)
            y = random.randint(margin, screen_h - margin)
            move_cursor(x, y, recorder, SPEEDRUN)
            countdown(int(TARGET_SECONDS - recorder.time))

    finally:
        recorder.save(SPEEDRUN)
        print("\n\n✨ Klaar ✅")
