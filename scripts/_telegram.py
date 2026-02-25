import time
import io
import requests
import pyautogui

# =========================================
# VUL IN
# =========================================
BOT_TOKEN = "8031171388:AAF5_H7Rs7X_UspAJc70D8I75qvn7XLqsck"
CHAT_ID = 8253849447  # <-- jouw chat id (int)

# =========================================
# BOT AREA COORDINATEN
# =========================================
# Pas deze aan naar jouw Bot_Area
BOT_AREA = (0, 0, 765, 503)  
# (left, top, width, height)

def send_bot_area_once():
    print("📸 Bot_Area screenshot over 2 seconden...")
    time.sleep(2)

    img = pyautogui.screenshot(region=BOT_AREA)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("bot_area.png", buf, "image/png")}
    data = {"chat_id": CHAT_ID, "caption": "🎯 Bot_Area test"}

    r = requests.post(url, data=data, files=files)

    if r.ok:
        print("✅ Screenshot verzonden!")
    else:
        print("❌ Fout:", r.text)

if __name__ == "__main__":
    send_bot_area_once()
