import io
import requests
import pyautogui

from core.bot_offsets import load_areas, apply_offset

BOT_TOKEN = "8031171388:AAF5_H7Rs7X_UspAJc70D8I75qvn7XLqsck"
CHAT_ID = 8253849447

def send_area_shot(area_name: str, caption: str, *, bot_id: int = 1, areas=None) -> bool:
    areas = areas or load_areas()

    if area_name not in areas:
        print(f"❌ Area niet gevonden: {area_name}")
        return False

    x1, y1, x2, y2 = map(int, apply_offset(areas[area_name], bot_id))
    w, h = x2 - x1, y2 - y1
    if w <= 2 or h <= 2:
        print(f"❌ Area heeft geen formaat: {area_name} -> {(x1,y1,x2,y2)}")
        return False

    img = pyautogui.screenshot(region=(x1, y1, w, h))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    files = {"photo": ("area.png", buf, "image/png")}
    data = {"chat_id": CHAT_ID, "caption": caption}

    r = requests.post(url, data=data, files=files, timeout=15)
    if not r.ok:
        print("❌ Telegram fout:", r.text)
        return False

    print("✅ Screenshot verzonden")
    return True

def main():
    from core.bot_offsets import load_areas

    print("🔍 AREAS laden...")
    areas = load_areas()

    print("Beschikbare areas:")
    for k in areas.keys():
        print(" -", k)

    # kies hier je area naam
    test_area = "Bot_Area"  # pas aan indien nodig
    bot_id = 1

    if test_area not in areas:
        print(f"❌ Area '{test_area}' bestaat niet.")
        return

    print(f"\n📸 Over 2 seconden screenshot van '{test_area}' (bot {bot_id})...")
    import time
    time.sleep(2)

    ok = send_area_shot(
        test_area,
        f"🧪 Test screenshot van {test_area}",
        bot_id=bot_id,
        areas=areas,
    )

    if ok:
        print("✅ Test succesvol")
    else:
        print("❌ Test mislukt")


if __name__ == "__main__":
    main()
