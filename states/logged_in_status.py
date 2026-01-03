from __future__ import annotations

from vision.image_detection import detect_image

def logged_in(*, bot_id: int = 1, area: str = "Info_Area", image: str = "xp.png") -> bool:
    return detect_image(image, area, bot_id=bot_id, verbose="off") is not None

