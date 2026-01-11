from vision.image_recognition import detect_image, FOUND_LOG

m = detect_image("WindowsLogo.png", "FullScreen", bot_id=1, method_name="TM_CCOEFF_NORMED", debug=True)

if m:
    print("gevonden ✅", m)
else:
    print("niet gevonden ❌", FOUND_LOG.get(("WindowsLogo.png","FullScreen",1,"TM_CCOEFF_NORMED")))
