from vision.image_detection import detect_one

m = detect_one(
    image_path="SettingsHouse.png",
    area_name="FullScreen",
    bot_id=1,
    method_name="TM_CCOEFF_NORMED",
    vorm_drempel=80,
)

print(m)
