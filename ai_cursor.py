from pynput.mouse import Controller, Button
from PIL import ImageDraw, ImageGrab
import pyautogui
import time
import random
import numpy as np
import math
import json

#############################

from config import AREAS_LINK
from bot_offset import get_offset

try:
    with open(AREAS_LINK, 'r') as f:
        AREAS = json.load(f)
except Exception as e:
    print(f"❌ Fout bij laden areas: {e}")
    AREAS = {}

###########################################

mouse = Controller()

FAST_MODE = False  # Zet op False voor realistische (langzamere) beweging


###########################################

def ease_in_out_quad(t):
    return 2*t*t if t < 0.5 else -1 + (4 - 2*t)*t

def bezier(t, p0, p1, p2, p3):
    return (
        (1 - t)**3 * np.array(p0) +
        3 * (1 - t)**2 * t * np.array(p1) +
        3 * (1 - t) * t**2 * np.array(p2) +
        t**3 * np.array(p3)
    )

###########################################

def move_cursor(target_coords):
    from_x, from_y = mouse.position
    to_x, to_y = target_coords

    dist = np.linalg.norm(np.array((to_x, to_y)) - np.array((from_x, from_y)))
    duration = random.uniform(0.4, 1.1) if FAST_MODE else random.uniform(0.354, 1.52)

    def generate_smooth_bezier(start, end):
        sx, sy = start
        ex, ey = end
        dist = np.linalg.norm(np.array(end) - np.array(start))
        angle = math.atan2(ey - sy, ex - sx)
        offset = dist * random.uniform(0.2, 0.4)

        ctrl1 = (sx + offset * math.cos(angle + random.uniform(-0.3, 0.3)),
                 sy + offset * math.sin(angle + random.uniform(-0.3, 0.3)))
        ctrl2 = (ex - offset * math.cos(angle + random.uniform(-0.3, 0.3)),
                 ey - offset * math.sin(angle + random.uniform(-0.3, 0.3)))
        return (sx, sy), ctrl1, ctrl2, (ex, ey)

    p0, p1, p2, p3 = generate_smooth_bezier((from_x, from_y), (to_x, to_y))
    steps = max(int(duration * 120), 60)
    t_values = [ease_in_out_quad(t) for t in np.linspace(0, 1, steps)]

    for t in t_values:
        pos = bezier(t, p0, p1, p2, p3)
        mouse.position = (int(pos[0]), int(pos[1]))
        time.sleep(duration / steps)

    mouse.position = (int(to_x), int(to_y))


def click(right_click=False):
    time.sleep(human_pause(short=True))  # micro-pauze voor klik

    if right_click:
        pyautogui.mouseDown(button='right')
    else:
        pyautogui.mouseDown()

    time.sleep(human_hold_time())  # realistische hold met decimalen

    pyautogui.mouseUp(button='right' if right_click else 'left')
    time.sleep(human_pause(short=True))  # na-klik rust

def drop_click():
    mouse.press(Button.left)
    time.sleep(random.uniform(0.028, 0.09))
    mouse.release(Button.left)
    time.sleep(random.uniform(0.02, 0.08))

def drop_move(x, y):
    start = mouse.position
    x += random.uniform(-3, 3)
    y += random.uniform(-3, 3)

    end = (int(x), int(y))
    mid_x = (start[0] + end[0]) / 2 + random.uniform(-16, 16)
    mid_y = (start[1] + end[1]) / 2 + random.uniform(-18, 18)

    steps = random.randint(14, 22)
    for i in range(steps):
        t = i / (steps - 1)
        xt = (1 - t)**2 * start[0] + 2 * (1 - t) * t * mid_x + t**2 * end[0]
        yt = (1 - t)**2 * start[1] + 2 * (1 - t) * t * mid_y + t**2 * end[1]
        mouse.position = (int(xt), int(yt))
        time.sleep(0.012 + random.uniform(-0.004, 0.006))

def random_mouse_movement(chance=0.6548):
    if random.random() > chance:
        return
    print("🌀 Random movement")

    width, height = pyautogui.size()
    x0, y0 = mouse.position

    rand = random.random()

    if rand < 0.03:
        # 🎯 Super swish (volledig random schermhoek)
        tx = random.randint(0, width)
        ty = random.randint(0, height)
        steps = random.randint(15, 30)
        print("⚡ Super swish")

    elif rand < 0.06:
        # 🌊 Golfbeweging
        print("🌊 Golfbeweging")
        amplitude = random.randint(20, 60)
        wavelength = random.randint(50, 120)
        direction = random.choice(["horizontal", "vertical"])
        steps = random.randint(30, 50)

        for i in range(steps):
            t = i / steps
            if direction == "horizontal":
                x = x0 + int(wavelength * t)
                y = y0 + int(amplitude * math.sin(t * 2 * math.pi))
            else:
                x = x0 + int(amplitude * math.sin(t * 2 * math.pi))
                y = y0 + int(wavelength * t)
            mouse.position = (x, y)
            time.sleep(random.uniform(0.005, 0.015))
        return

    elif rand < 0.36:
        # 🧭 Medium drift
        print("🧭 Medium drift")
        drift = random.randint(40, 120)
        angle = random.uniform(0, 2 * math.pi)
        tx = int(x0 + drift * math.cos(angle))
        ty = int(y0 + drift * math.sin(angle))
        steps = random.randint(10, 20)

    else:
        # 🔄 Kleine drift
        print("🔄 Kleine drift")
        drift = random.randint(20, 75)
        angle = random.uniform(0, 2 * math.pi)
        tx = int(x0 + drift * math.cos(angle))
        ty = int(y0 + drift * math.sin(angle))
        steps = random.randint(8, 15)

    # 💫 Beweging uitvoeren
    for i in range(steps):
        t = (i + 1) / steps
        x = int(x0 + (tx - x0) * math.sin(t * math.pi / 2))
        y = int(y0 + (ty - y0) * math.sin(t * math.pi / 2))
        mouse.position = (x, y)
        time.sleep(random.uniform(0.005, 0.02))

def move_in_area(area_name, bot_id=1, verbose=True):
    area_key = area_name.lower()  # Alles kleine letters
    if area_key not in [k.lower() for k in AREAS]:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden!")
        return False

    # Corrigeer key voor AREAS lookup
    true_key = next(k for k in AREAS if k.lower() == area_key)
    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = AREAS[true_key]
    x1 += ox
    y1 += oy
    x2 += ox
    y2 += oy

    rand_x = random.randint(x1, x2)
    rand_y = random.randint(y1, y2)

    if verbose:
        print(f"🖱️ Beweeg naar {true_key} bij ({rand_x}, {rand_y}) met offset ({ox}, {oy})")

    move_cursor((rand_x, rand_y))
    return True

def move_outside_area(area_name, bot_id=1, margin=20, verbose=True):
    area_key = area_name.lower()
    if area_key not in [k.lower() for k in AREAS]:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden!")
        return False

    true_key = next(k for k in AREAS if k.lower() == area_key)
    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = AREAS[true_key]
    x1 += ox
    y1 += oy
    x2 += ox
    y2 += oy

    # Kies willekeurig één van de vier kanten om buiten te gaan
    side = random.choice(["left", "right", "top", "bottom"])

    if side == "left":
        rand_x = random.randint(x1 - margin - 50, x1 - margin)  # iets links buiten
        rand_y = random.randint(y1, y2)
    elif side == "right":
        rand_x = random.randint(x2 + margin, x2 + margin + 50)  # iets rechts buiten
        rand_y = random.randint(y1, y2)
    elif side == "top":
        rand_x = random.randint(x1, x2)
        rand_y = random.randint(y1 - margin - 50, y1 - margin)  # iets boven buiten
    else:  # bottom
        rand_x = random.randint(x1, x2)
        rand_y = random.randint(y2 + margin, y2 + margin + 50)  # iets onder buiten

    if verbose:
        print(f"🖱️ Beweeg buiten {true_key} naar ({rand_x}, {rand_y}) met offset ({ox}, {oy})")

    move_cursor((rand_x, rand_y))
    return True

def lognorm_ms(mean, sigma):
    # mean in seconden; sigma = log-space std (0.25–0.45 werkt vaak goed)
    # return lognormaal sample met gegeven mean
    mu = math.log(mean) - 0.5 * sigma * sigma
    return math.exp(random.gauss(mu, sigma))

def human_hold_time():
    # Doel: median ~0.09s, normaal 0.07–0.12s, af en toe langer
    t = lognorm_ms(0.09, 0.35)
    if random.random() < 0.01:  # 1% rare long press
        t *= random.uniform(2.0, 3.5)
    return round(min(max(t, 0.05), 1.0), 8)

def human_pause(short=True):
    if short:
        # Doel: median ~0.40 s met variatie
        t = lognorm_ms(0.45, 0.35)
        if random.random() < 0.05:   # 5% pre-click microstall
            t += random.uniform(0.08, 0.22)
    else:
        # Doel: median ~0.80–1.10 s met staart
        t = lognorm_ms(0.95, 0.40)
        if random.random() < 0.02:   # 2% langere afleiding
            t += random.uniform(1.2, 3.5)
    if random.random() < 0.01:       # zeldzaam bijna instant
        return round(random.uniform(0.02, 0.05), 8)
    return round(min(max(t, 0.07), 5.0), 8)


def human_hold_time():
    # Doel: median ~0.18–0.30 s, af en toe langer
    t = lognorm_ms(0.22, 0.38)  # typische hold iets langer dan jouw 0.11
    if random.random() < 0.007:   # 0.7% rare long press
        t *= random.uniform(2.0, 4.0)
    return round(min(max(t, 0.06), 1.2), 8)

def human_pause(short=True):
    if short:
        # Doel: median ~0.40 s met variatie
        t = lognorm_ms(0.45, 0.35)
        if random.random() < 0.05:   # 5% pre-click microstall
            t += random.uniform(0.08, 0.22)
    else:
        # Doel: median ~0.80–1.10 s met staart
        t = lognorm_ms(0.95, 0.40)
        if random.random() < 0.02:   # 2% langere afleiding
            t += random.uniform(1.2, 3.5)
    if random.random() < 0.01:       # zeldzaam bijna instant
        return round(random.uniform(0.02, 0.05), 8)
    return round(min(max(t, 0.07), 5.0), 8)

def human_scroll(reverse=False, scroll_ratio=(2, 4), verbose=True):
    """
    Menselijke OSRS-scroll:
    - Scrollt in batches (3-5 scrolls) tot max volgens scroll_ratio.
    - Tussen batches korte pauze.
    - Soms trage scroll alsof je zoekt.
    - Microbewegingen.
    """
    total_scrolls = random.randint(scroll_ratio[0], scroll_ratio[1])
    direction = 1 if reverse else -1
    dir_emoji = "⬆️" if direction > 0 else "⬇️"

    if verbose:
        print(f"\n🌀 Scroll start: {total_scrolls}x {dir_emoji}")

    scrolls_done = 0
    current_pos = mouse.position

    while scrolls_done < total_scrolls:
        batch_size = min(random.randint(3, 5), total_scrolls - scrolls_done)

        for _ in range(batch_size):
            if random.random() < 0.13:
                x, y = current_pos
                dx, dy = random.choice([-1, 0, 1]), random.choice([-1, 0, 1])
                current_pos = (x + dx, y + dy)
                mouse.position = current_pos
                if verbose:
                    print(f"↔️ {current_pos}")

            mouse.scroll(0, direction)
            scrolls_done += 1
            if verbose:
                print(f"{scrolls_done}/{total_scrolls} {dir_emoji}")

            if random.random() < 0.1:
                time.sleep(random.uniform(1, 2))
            else:
                time.sleep(random.uniform(0.021, 0.072))

        if scrolls_done < total_scrolls:
            time.sleep(random.uniform(0.3, 0.8))

    if verbose:
        print("✅ Klaar\n")

        
def click_in_area(area_name, bot_id=1, verbose=True):
    if area_name not in AREAS:
        if verbose:
            print(f"❌ Gebied '{area_name}' niet gevonden!")
        return False

    ox, oy = get_offset(bot_id)
    x1, y1, x2, y2 = AREAS[area_name]
    x1 += ox
    y1 += oy
    x2 += ox
    y2 += oy

    rand_x = random.randint(x1, x2)
    rand_y = random.randint(y1, y2)

    if verbose:
        print(f"🖱️ Klik in {area_name} bij ({rand_x}, {rand_y}) met offset ({ox}, {oy})")

    move_cursor((rand_x, rand_y))
    click()

    return True

