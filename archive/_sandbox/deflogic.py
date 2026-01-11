import pyautogui
import numpy as np
import cv2
import os
import time
import random
import keyboard
from pynput.keyboard import Key, Controller
from config import AREAS_LINK, IMAGES_LINK
from image_recognition import detect_image, find_and_click, move_to_image
from ai_cursor import random_mouse_movement, click, move_cursor, click_in_area, human_scroll
from ai_cursor import move_in_area
from ai_keyboard import arrow, arrow_sidemove, arrow_up
from PIL import ImageGrab
import json
import sys
import sys, os
from image_recognition import _IMAGE_CACHE
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

kb = Controller()

# Cache waarin je per afbeelding de laatst gevonden bbox opslaat


####################################################################################

# 📸 Images
IMAGES_DIR = IMAGES_LINK
IMAGES = {}
for file in os.listdir(IMAGES_DIR):
    if file.lower().endswith((".png", ".jpg", ".jpeg")):
        key = os.path.splitext(file)[0].lower()
        IMAGES[key] = os.path.join(IMAGES_DIR, file)

# 🆔 Bot ID & offsets
bot_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
BOT_OFFSETS = {1: (0,0), 2: (958,0), 3: (0,498), 4: (958,498)}
x_off, y_off = BOT_OFFSETS.get(bot_id, (0,0))

########################

# 📁 Laad gebieden
CONFIG_PATH = AREAS_LINK
with open(CONFIG_PATH, 'r') as f:
    areas = {k.lower(): v for k, v in json.load(f).items()}

####################################################################################

def get_area(area_name, bot_id=1):
    x_offset, y_offset = BOT_OFFSETS.get(bot_id, (0, 0))
    with open(CONFIG_PATH, 'r') as f:
        areas = json.load(f)
    x1, y1, x2, y2 = areas[area_name]
    return [x1 + x_offset, y1 + y_offset, x2 + x_offset, y2 + y_offset]

####################################################################################

import json
from pathlib import Path

# Vind de config map t.o.v. de modules map
config_path = Path(__file__).parent.parent / "config" / "colour_ranges.json"

if not config_path.exists():
    raise FileNotFoundError(f"Config bestand niet gevonden: {config_path}")

with open(config_path, "r", encoding="utf-8") as f:
    data = json.load(f)

COLOR_RANGES = {k.lower(): (tuple(v[0]), tuple(v[1])) for k, v in data["COLOR_RANGES"].items()}
COLOR_ALIASES = {k.lower(): v.lower() for k, v in data.get("COLOR_ALIASES", {}).items()}


####################################################################################

def offset_area(region):
    x1, y1, x2, y2 = region
    return (x1 + x_off, y1 + y_off, x2 + x_off, y2 + y_off)

# 🌈 HSV-bereiken voor kleurdetectie
COLOR_RANGES = {
    "groen": ([35, 50, 50], [85, 255, 255]),
    "felgroen": ([62, 240, 240], [65, 255, 255]),
    "rood":  ([0, 100, 100], [10, 255, 255]),
    "blauw": ([100, 50, 50], [130, 255, 255]),
    "cyaan": ([80, 50, 50], [100, 255, 255]),
    "geel":  ([20, 100, 100], [30, 255, 255]),
    "oranje": ([18, 180, 180], [22, 255, 255]),
    "paars": ([140, 50, 50], [170, 255, 255]),
    "cyaanblauw": ([0, 255, 255], [0, 255, 255]),
    "gracecolour": ([165, 140, 11], [165, 140, 11]),
    "hellcat": ([126, 17, 9], [126, 17, 9])

   
}

(126, 17, 9)
####################################################################################

def get_screen_region(region):
    x1, y1, x2, y2 = region  # offset is al toegepast door het aanroepende script
    return np.array(pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1)))


    # onder threshold → wél rood
    if top_pct < 5:
        return f"🔴"

    # anders kies je de dominante kleur
    if pct_groen > pct_rood:
        return f"🟢"
    else:
        return f"🔴"

##################################################################################

def logged_in(bot_id):
    if detect_image("Globe.png", "Info Area", "TM_CCOEFF", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
        return True
    else:
        return False

def inventory(bot_id, verbose=True):
    if verbose:
        print(f"[inventory] bot_id={bot_id}")
        print("[inventory] start detect_image('InventorySelected.png')")

    if detect_image("InventorySelected.png", "Buttons","TM_CCORR_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
        if verbose:
            print("[inventory] detect_image: True")
        print("✅ Inventory found")
        return True
    else:
        if verbose:
            print("[inventory] detect_image: False → ESC")
        move_in_area("Focus Area", bot_id=bot_id, verbose=True)
        click()
        kb.press(Key.esc)
        time.sleep(random.uniform(0.0312, 0.15123))
        kb.release(Key.esc)
        print("❌ Inventory NOT found")
        return False

# 🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈🏳️‍🌈

# 🔎 Pixelkleur check (origineel)
def pixel_match(img, color, tolerance):
    return np.sum(np.all(np.abs(img - color) <= tolerance, axis=-1))

def click_color(kleur: str, area_name, bot_id=bot_id, threshold=0.1, jitter_range=6, min_size=15, verbose=True):
    kleur = COLOR_ALIASES.get(kleur.lower(), kleur.lower())
    if kleur not in COLOR_RANGES:
        if verbose:
            print(f"❌ Onbekende kleur: {kleur}")
        return False

    key = area_name.lower()
    if key not in areas:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden!")
        return False

    # area ophalen + bot offset toevoegen
    x1, y1, x2, y2 = areas[key]
    x_off, y_off = BOT_OFFSETS.get(bot_id, (0, 0))
    x1 += x_off
    y1 += y_off
    x2 += x_off
    y2 += y_off

    # check kleur aanwezig
    if not has_colour_in_area(kleur, (x1, y1, x2, y2), bot_id=bot_id, threshold_pct=threshold*100, verbose=verbose):
        return False

    # screenshot maken
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    np_img = np.array(img)
    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)
    lower, upper = map(np.array, COLOR_RANGES[kleur])
    mask = cv2.inRange(hsv, lower, upper)

    # contours zoeken
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        if verbose:
            print(f"🫥 Geen contour voor {kleur}")
        return False

    grote_contouren = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_size]
    if not grote_contouren:
        if verbose:
            print(f"🫥 Geen vlak ≥{min_size} pixels voor {kleur}")
        return False

    # grootste contour pakken
    grootste = max(grote_contouren, key=cv2.contourArea)
    M = cv2.moments(grootste)
    if M["m00"] == 0:
        return False

    cx = int(M["m10"] / M["m00"]) + x1
    cy = int(M["m01"] / M["m00"]) + y1

    # jitter toevoegen
    tx = cx + random.randint(-jitter_range, jitter_range)
    ty = cy + random.randint(-jitter_range, jitter_range)

    if verbose:
        print(f"🎯 Klik op {kleur} vlak ({cv2.contourArea(grootste):.0f}px) → ({tx}, {ty})")

    move_cursor((tx, ty))
    click()
    return True

def detect_color(kleur: str, area_name, bot_id=bot_id, threshold=0.1, verbose=True):
    kleur = COLOR_ALIASES.get(kleur.lower(), kleur.lower())
    if kleur not in COLOR_RANGES:
        if verbose:
            print(f"❌ Onbekende kleur: {kleur}")
        return False

    key = area_name.lower()
    if key not in areas:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden!")
        return False

    # area + bot offset
    x1, y1, x2, y2 = areas[key]
    x_off, y_off = BOT_OFFSETS.get(bot_id, (0, 0))
    x1 += x_off; y1 += y_off; x2 += x_off; y2 += y_off

    # simpele check via bestaande functie
    found = has_colour_in_area(
        kleur,
        (x1, y1, x2, y2),
        bot_id=bot_id,
        threshold_pct=threshold * 100,
        verbose=verbose
    )

    if verbose:
        print(f"🔎 {kleur} in '{area_name}': {found}")

    return bool(found)

#######################################################################

def click_color_cyaan(area=None, bot_id=bot_id):
    return click_color("cyaan", area=area, bot_id=bot_id)

def move_to_color(kleur: str, bbox=None, jitter_range=4):
    kleur = kleur.lower()

    if not has_colour_in_area(kleur, bbox, 0.05):
        print(f"🫥 Geen {kleur} zichtbaar.")
        return False

    img = ImageGrab.grab(bbox=bbox)
    np_img = np.array(img)
    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)
    lower, upper = map(np.array, COLOR_RANGES[kleur])
    mask = cv2.inRange(hsv, lower, upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print(f"🫥 Geen contour voor {kleur}.")
        return False

    grootste = max(contours, key=cv2.contourArea)
    M = cv2.moments(grootste)
    if M["m00"] == 0:
        print(f"❌ Ongeldige contour voor {kleur}")
        return False

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    jitter_x = random.randint(-jitter_range, jitter_range)
    jitter_y = random.randint(-jitter_range, jitter_range)
    abs_x = cx + jitter_x + (bbox[0] if bbox else 0)
    abs_y = cy + jitter_y + (bbox[1] if bbox else 0)

    move_cursor((abs_x, abs_y))
    print(f"🎯 Cursor geplaatst op {kleur} → ({abs_x}, {abs_y})")
    return (abs_x, abs_y)

################################################

def click_in(area_name, bot_id):
    if area_name.lower() not in areas:
        print(f"❌ Ongeldig gebied: {area_name}")
        return False

    x1, y1, x2, y2 = offset_area(areas[area_name.lower()])
    x = random.randint(x1, x2)
    y = random.randint(y1, y2)
    move_cursor((x, y))
    click()
    return True

def move_in(area_name, bot_id):
    if area_name.lower() not in areas:
        print(f"❌ Ongeldig gebied: {area_name}")
        return False

    x1, y1, x2, y2 = offset_area(areas[area_name.lower()], bot_id)
    x = random.randint(x1, x2)
    y = random.randint(y1, y2)
    move_cursor((x, y))
    return True

def antiban_arrow():
    if random.random() < 0.1:
        for _ in range(random.randint(1,2)):
            key = random.choice(['left','right'])
            duration = random.uniform(0.15,0.35)
            pyautogui.keyDown(key); time.sleep(duration); pyautogui.keyUp(key)
            time.sleep(random.uniform(0.1,0.2))

###########################################################
################### NEW NEW NEW NEW NEW ###################

# 💤💤💤💤💤💤💤💤💤💤💤💤💤💤💤💤💤💤

def sleep_short():
    time.sleep(random.uniform(0.18, 0.44))

def sleep_mid():
    time.sleep(random.uniform(0.7, 1.8))

def sleep_long():
    time.sleep(random.uniform(7.5, 8.9))

def sleep_custom(min_sec, max_sec):
    time.sleep(random.uniform(min_sec, max_sec))

def check_escape():
    if keyboard.is_pressed('esc'):
        print("🚪 Escape, stoppen.")
        sys.exit(0)

##############################################################

def afk(bot_id, verbose=True):
    if detect_image("groen.png", "Antiban", "TM_CCOEFF", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟢 Antiban-groen gevonden → Bot moet INGELOGD BLIJVEN (afk = False)")
        return True
    elif detect_image("rood.png", "Antiban", "TM_CCOEFF", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🔴 Antiban-rood gevonden → Bot mag uitloggen/afk (afk = True)")
        return False
    else:
        if verbose:
            print(f"[Bot {bot_id}] ⚪️ Geen groen of rood gevonden → Geen kleur gedetecteerd")
        return None

# 🏦🏦🏦🏦🏦🏦🏦🏦🏦🏦🏦🏦

def inventory_selected(bot_id, verbose=True):
    if detect_image("InventorySelected.png", "Buttons", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟢 Inventory geselecteerd")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🔴 Inventory is niet geselecteerd")
        find_and_click("InventoryUnselected.png", "Buttons", bot_id=bot_id)
        # Direct check opnieuw na klikken
        if detect_image("InventorySelected.png", "Buttons", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
            if verbose:
                print(f"[Bot {bot_id}] 📦 Na klikken nu wél ✅ geselecteerd")
            return True
        else:
            if verbose:
                print(f"[Bot {bot_id}] 📦 Na klikken nog steeds ❌ niet geselecteerd")
            return False


def logged(bot_id, verbose=True):
    if detect_image("Login - Exp Icon.png", "Info Area", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟢 Online ")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🔴 Offline")
        return False
    
def bank_open(bot_id, verbose=True):
    if detect_image("bank_deposit.png", "Object Area", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] Bank open 🔴")
            find_and_click("cross.png", "Object Area", method_name="TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id)
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🟢 Bank closed")
        return False

def wait_for_bank(bot_id, verbose=True, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        if detect_image("bank_deposit.png", "Object Area", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
            if verbose:
                print(f"🏦 Bank open voor bot {bot_id} ✅")
            return True
        else:
            if verbose:
                print(f"⏳ Wacht op bank open voor bot {bot_id}...")
        time.sleep(random.uniform(1.0, 2.0))
    if verbose:
        print(f"❌ Bank niet open binnen {timeout} seconden voor bot {bot_id}")
    return False

def screen_open(bot_id, verbose=True):
    max_attempts = 3
    for attempt in range(max_attempts):
        if find_and_click("Cross.png", "Object Area", "TM_CCOEFF",vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
            if verbose:
                print(f"[Bot {bot_id}] Screen open 🔴 (poging {attempt+1})")
            find_and_click("Cross.png", "Object Area", method_name="TM_CCOEFF_NORMED",vorm_drempel=95, kleur_drempel=90, bot_id=bot_id)
            # check of hij echt weg is
            if not detect_image("Cross.png", "Object Area", "TM_CCOEFF",vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
                if verbose:
                    print(f"[Bot {bot_id}] ✅ Screen gesloten")
                return True
        else:
            if verbose:
                print(f"[Bot {bot_id}] 🟢 Screens closed")
            return False
    if verbose:
        print(f"[Bot {bot_id}] ⚠️ Kon screen niet sluiten na {max_attempts} pogingen")
        kb.press(Key.esc)
        random.uniform(0.0312, 0.15123)
        kb.release(Key.esc)
    return False

def check_timeout(start_time, max_runtime=35, verbose=True):
    elapsed = time.time() - start_time
    if verbose:
        print(f"⏱️ Verstreken: {elapsed:.2f}s / {max_runtime}s")

    if elapsed > max_runtime:
        print(f"⏳ Tijdlimiet van {max_runtime} seconden bereikt, script stopt.")
        sys.exit(0)


# 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
# 🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦

def detect_cyaan(bot_id, verbose=True):
    if detect_image("cyaan.png", "Object Area", "TM_SQDIFF_NORMED",vorm_drempel=95, kleur_drempel=70, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟦🟦🟦🟦 Detected ")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🟦⚪️⚪️⚪️ Not detected")
        return False

def click_cyaan(bot_id, verbose=True):
    if find_and_click("cyaan.png", "Object Area", "TM_SQDIFF_NORMED",vorm_drempel=95, kleur_drempel=70, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟦🟦🟦🟦 Clicked")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🟦⚪️⚪️⚪️ Not clicked")
        return False


# 🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪
# 🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪🟪

def detect_purple(bot_id, verbose=True):
    if detect_image("Purple.png", "Object Area", "TM_SQDIFF_NORMED",vorm_drempel=95, kleur_drempel=40, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟪🟪🟪🟪 Detected")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🟪⚪️⚪️⚪️ Not detected")

        return False

def click_purple(bot_id, verbose=True):
    if find_and_click("Purple.png", "Object Area", "TM_SQDIFF_NORMED", vorm_drempel=95, kleur_drempel=40, bot_id=bot_id):
        if verbose:
            print(f"[Bot {bot_id}] 🟪🟪🟪🟪 Clicked")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🟪⚪️⚪️⚪️ Not clicked️️️")
        return False
    

# ⌚⌚⌚⌚⌚⌚⌚⌚⌚⌚⌚⌚

    
def skill_checker(skill_img, area, bot_id=bot_id):
    # Check of skills tab geselecteerd is, anders klik
    if detect_image("Skills.png", "Buttons", method_name="TM_CCOEFF_NORMED",vorm_drempel=90, kleur_drempel=90, bot_id=bot_id):
        if find_and_click("Skills.png", "Buttons", method_name="TM_CCOEFF_NORMED",vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
            time.sleep(random.uniform(0.22, 0.51))

    move_to_image(skill_img, area, method_name="TM_CCOEFF_NORMED",
                  vorm_drempel=90, kleur_drempel=90, bot_id=bot_id)

    random.choices([sleep_long, sleep_mid], weights=[70, 30])[0]()


    ######################################

def get_colour_pct(col: str, region, bot_id, use_hsv=True, verbose=True):
    key = col.lower()
    if key not in COLOR_RANGES:
        raise ValueError(f"Onbekende kleur: {col}")
    
    img = get_screen_region(region)
    img_hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV) if use_hsv else img
    lower, upper = map(np.array, COLOR_RANGES[key])
    mask = cv2.inRange(img_hsv, lower, upper)
    pct = mask.sum() / mask.size * 100

    if verbose:
        print(f"[Bot {bot_id}] {col} pct: {pct:.2f}%")

    return min(pct, 100.0)

def has_colour_in_area(col: str, region, bot_id=bot_id, threshold_pct=10.0, verbose=True):
    pct = get_colour_pct(col, region, bot_id=bot_id, verbose=False)  # get_colour_pct print al percentage

    if verbose:
        print(f"[Bot {bot_id}] {col} pct: {pct:.2f}% - Threshold: {threshold_pct:.0f}%")

    return pct >= threshold_pct

def detect_skilling(bot_id, verbose=True):
    region = get_area("Skilling Area", bot_id)
    if get_colour_pct("groen", region, bot_id=bot_id, verbose=verbose) >= 1.0:
        if verbose:
            print(f"[Bot {bot_id}] 🟢 Skilling")
        return True
    else:
        if verbose:
            print(f"[Bot {bot_id}] 🔴 Niet aan het skillen!")
        return False

def open_bank(bot_id, verbose=True):
    if click_cyaan(bot_id):
        if verbose:
            print("🔵")

        timeout = time.time() + 10
        while time.time() < timeout:
            if detect_image("bank_deposit.png", "Object Area", "TM_CCOEFF_NORMED",
                            vorm_drempel=95, kleur_drempel=92, bot_id=bot_id):
                if verbose:
                    print("🖼️  Bank deposit.")
                time.sleep(random.uniform(1.0, 1.6))
                return True

        if verbose:
            print("❌ Bank deposit niet gevonden binnen timeout.")
    return False

def close_bank(bot_id, verbose=True, max_attempts=5):
    attempts = 0

    while attempts < max_attempts:
        # Check of bank al dicht is
        if not detect_image("bank_deposit.png", "Object Area", "TM_CCOEFF_NORMED",
                            vorm_drempel=95, kleur_drempel=92, bot_id=bot_id):
            if verbose:
                print("✅ Bank is gesloten.")
            return True

        if verbose:
            print(f"⏳ Poging {attempts+1}/{max_attempts} om bank te sluiten...")

        # Kies random actie: True = ESC, False = muisklik
        use_esc = random.choice([True, False])

        if use_esc:
            if verbose:
                print("⌨️ Probeer bank te sluiten met ESC")
            kb.press(Key.esc)
            sleep_mid()
            kb.release(Key.esc)
        else:
            if verbose:
                print("🖱️ Probeer bank te sluiten met kruisje")
            find_and_click("cross.png", "Object Area", method_name="TM_CCOEFF_NORMED",
                          vorm_drempel=95, kleur_drempel=92, bot_id=bot_id)
            sleep_mid()

        # Check of bank nu dicht is
        if not detect_image("bank_deposit.png", "Object Area", "TM_CCOEFF_NORMED",
                            vorm_drempel=95, kleur_drempel=92, bot_id=bot_id):
            if verbose:
                via = "ESC" if use_esc else "muisklik"
                print(f"✅ Bank gesloten via {via}")
            return True

        attempts += 1

    if verbose:
        print("❌ Bank sluiten mislukt na max pogingen")
    return False

def click_south(bot_id, verbose=True):
    move_in_area("Kompas", bot_id=bot_id, verbose=True)
    click(right_click=True)
    sleep_short()
    if find_and_click("Look_South.png", "Info Area", "TM_CCOEFF_NORMED",
                            vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
            print("Clicking South on compass")
    sleep_short()

def click_compass(bot_id, verbose=True):
    move_in_area("Kompas", bot_id=bot_id, verbose=True)
    click(right_click=False)
    sleep_short()

def reset_camera(bot_id, verbose=True):
    click_compass(bot_id,verbose=True)
    sleep_short()
    arrow_up()

def open_bank(bot_id=bot_id, verbose=True):
    """Vereenvoudigde open_bank. Detecteert cyaan, clickt, doet anders human interacties."""
    try:
        if verbose:
            print("🔍 Start open_bank_simple()")
        # Stap 1: Detect cyaan
        if detect_cyaan(bot_id, verbose=verbose):
            if click_cyaan(bot_id, verbose=verbose):
                if verbose:
                    print("✅ Bank geopend via cyaan!")
                sleep_short()
                return True

        # Stap 2: Menselijke afleiding
        if random.random() < 0.5:
            if verbose:
                print("👁️ Klik random in Focus Area")
            click_in("Focus Area", bot_id)
        else:
            if verbose:
                print("💬 Klik random in Chat Area")
            click_in("Chat Area", bot_id)

        move_in_area("Object Area", bot_id=bot_id, verbose=verbose)
        sleep_short()

        # Stap 3: Opnieuw cyaan check
        if detect_cyaan(bot_id, verbose=verbose):
            if click_cyaan(bot_id, verbose=verbose):
                if verbose:
                    print("✅ Bank geopend bij tweede check!")
                sleep_short()
                return True

        # Stap 4: Max 2x arrow_sidemove
        for attempt in range(2):
            if verbose:
                print(f"↔️ Arrow sidemove poging {attempt+1}/2")
            arrow_sidemove(verbose=verbose)
            sleep_short()
            if detect_cyaan(bot_id, verbose=verbose):
                if click_cyaan(bot_id, verbose=verbose):
                    if verbose:
                        print("✅ Bank geopend na arrow sidemove!")
                    sleep_short()
                    return True

        if verbose:
            print("❌ Kon bank niet openen (geen cyaan gevonden na alle pogingen)")
        return False

    except Exception as e:
        print(f"🔴 Fout in open_bank_simple: {e}")
        return False


def reset(bot_id, verbose=True):
    if not detect_image("CompassOnSouth.png", "Info Area", "TM_CCOEFF_NORMED",vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
        move_in_area("Object Area", bot_id=bot_id, verbose=verbose)
        human_scroll(reverse=False, scroll_ratio=(5, 7), verbose=True)
        move_in_area("Kompas", bot_id=bot_id, verbose=True)
        click(right_click=True)
        sleep_mid()
        if not detect_image("CompassOnSouth.png", "Info Area", "TM_CCOEFF_NORMED",vorm_drempel=95, kleur_drempel=90, bot_id=bot_id):
            find_and_click("Look_South.png", "Info Area", "TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=90, bot_id=bot_id)
            sys.exit()
    else:
        move_in_area("Object Area", bot_id=bot_id, verbose=verbose)
        human_scroll(reverse=False, scroll_ratio=(5, 7), verbose=True)
        sys.exit()
    

# ============== RANDOM ==============

def right_click_random(bot_id, verbose=True):
    move_in_area("Object Area", bot_id=bot_id, verbose=verbose)
    click(right_click=True)
    sleep_short()

def random_buttons_click(bot_id):
    move_in_area("Buttons", bot_id=bot_id, verbose=True)
    click()
    kb.press(Key.esc)
    time.sleep(random.uniform(0.0312, 0.15123))
    kb.release(Key.esc)

def worldhop(bot_id, verbose=True):
    if verbose:
        print("World hopping")
    move_in_area("Chat Area", bot_id=bot_id)
    click()
    sleep_mid()
    kb.press('q')
    time.sleep(random.uniform(0.0312, 0.15123))
    kb.release('q')
    time.sleep(random.uniform(8.0312, 12.15123))

def message(bot_id, verbose=True):
    if find_and_click("Friends.png", "Buttons Lower", method_name="TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id):
        find_and_click("WorldMessage.png", "Inventory Area", method_name="TM_CCOEFF_NORMED", vorm_drempel=95, kleur_drempel=95, bot_id=bot_id)
        move_in_area("Chat Area", bot_id=bot_id)

def otherplayers (bot_id, verbose=True):
      if detect_image("OtherPlayers.png", "Info Area", "TM_CCOEFF_NORMED",vorm_drempel=95, kleur_drempel=93, bot_id=bot_id):
          print("Other player detected")

def quest(bot_id, verbose=True):
    print("Test")