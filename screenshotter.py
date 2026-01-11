import time
import threading
import pyautogui
from pynput import keyboard

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

# =========================
# INSTELLINGEN
# =========================
TRIGGER_KEY = keyboard.Key.f6
HOLD_TIME = 0.35

pressed_at = None
triggered = False
running = True
stop_event = threading.Event()


# =========================
# HOTKEY LISTENER
# =========================
def on_press(key):
    global pressed_at, triggered
    if not running:
        return

    if key == TRIGGER_KEY and pressed_at is None:
        pressed_at = time.time()
        triggered = False


def on_release(key):
    global pressed_at, triggered
    if key == TRIGGER_KEY:
        pressed_at = None
        triggered = False


def monitor_loop():
    global pressed_at, triggered
    while not stop_event.is_set():
        if running and pressed_at and not triggered:
            held_time = time.time() - pressed_at
            if held_time >= HOLD_TIME:
                print("📸 Screenshot trigger!")
                pyautogui.hotkey("win", "shift", "s")
                triggered = True

        time.sleep(0.05)


# =========================
# TRAY UI
# =========================
def make_icon():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 14, 56, 50), radius=8, outline="white", width=4)
    d.rectangle((24, 24, 40, 40), outline="white", width=4)
    return img


def update_title(icon):
    icon.title = f"Easy Screenshotter ({'ON' if running else 'OFF'})"


def toggle_running(icon, _):
    global running
    running = not running
    update_title(icon)


def quit_app(icon, _):
    stop_event.set()
    icon.stop()


def run_tray():
    icon = pystray.Icon(
        "EasyScreenshotter",
        make_icon(),
        "Easy Screenshotter (ON)",
        menu=pystray.Menu(
            item("Status zichtbaar in titel", None, enabled=False),
            item("Toggle ON/OFF", toggle_running),
            item("Exit", quit_app),
        ),
    )
    update_title(icon)
    icon.run()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("🚀 Easy Screenshotter tray gestart")
    print("👉 Houd F6 ingedrukt om Win+Shift+S te starten")

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

    run_tray()
