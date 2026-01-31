import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ============================================================
# IMPORTS 📥
# ============================================================
from core.move_to_area import move_in_area
from core.ai_cursor import click
from core.click_image import click_image
from helpers.random_sleep import sleep_custom

# ============================================================
# COMPASS CONFIG 🧭
# ============================================================
DIRECTIONS = {
    "north": "Compass_North.png",
    "south": "Compass_South.png",
    "west":  "Compass_West.png",
    "east":  "Compass_East.png",
}

# ============================================================
# ASSIST CLICK COMPASS 🧭
# ============================================================
def assist_click_compass(direction, bot_id=1, verbose=True):
    raw = str(direction).strip()
    d = raw.lower()
    d_label = d.capitalize()   # 👈 voor nette prints
    img = DIRECTIONS.get(d)

    if not img:
        verbose and print(f"❌  🧭  Onbekende richting   | {raw}")
        return False

    verbose and print(f"⏳  🧭  Richting instellen  | {d_label}")

    # Cursor naar kompasgebied
    move_in_area("Compass_Area", bot_id=bot_id, verbose=False, padding=3)

    # Contextmenu openen
    click(button="right")
    sleep_custom(0.12, 0.25)

    # Richting aanklikken
    ok = click_image(img, "Bot_Area_Full", bot_id, verbose=False)

    if ok:
        verbose and print(f"✅  🧭  Richting gezet      | {d_label}")
    else:
        verbose and print(f"❌  🧭  Richting mislukt    | {d_label}")

    return ok


# ============================================================
# TEST 🧪
# ============================================================
if __name__ == "__main__":
    print("🧪  Test assist_click_compass\n")

    assist_click_compass("north", bot_id=1, verbose=True)
    assist_click_compass("west", bot_id=1, verbose=True)
    assist_click_compass("east", bot_id=1, verbose=True)
    assist_click_compass("south", bot_id=1, verbose=True)
