from vision.image_recognition import detect_image

m = detect_image(
    image_path="WindowsLogo.png",
    area_name="FullScreen",
    bot_id=1,
    method_name="TM_CCOEFF_NORMED",
    vorm_drempel=80,
    kleur_drempel=50,
)

print(m)
