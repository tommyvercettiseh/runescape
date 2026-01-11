import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui

OUT_DIR = Path("assets/images") 
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW_NAME = "Crop Tool (drag met muis, ENTER=save, R=reset, ESC=quit)"

def main():
    time.sleep(0.4)  # klein momentje zodat je je scherm goed hebt
    shot = pyautogui.screenshot()
    img_rgb = np.array(shot)
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    while True:
        roi = cv2.selectROI(WINDOW_NAME, img_bgr, showCrosshair=True, fromCenter=False)
        x, y, w, h = roi

        if w == 0 or h == 0:
            cv2.destroyAllWindows()
            print("Geen selectie gemaakt. Afgebroken.")
            return

        crop = img_bgr[y:y+h, x:x+w]

        ts = time.strftime("%Y%m%d_%H%M%S")
        out_path = OUT_DIR / f"crop_{ts}.png"
        cv2.imwrite(str(out_path), crop)
        cv2.destroyAllWindows()

        print("Saved:", out_path.resolve())
        print("ROI:", {"x": int(x), "y": int(y), "w": int(w), "h": int(h)})
        return

if __name__ == "__main__":
    main()
