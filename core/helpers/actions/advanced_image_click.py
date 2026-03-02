import time
from core.click_image import click_image


def advanced_image_click(
    image,
    bot_id=1,
    button="left",
    area="Inventory_Area",
    action=None,
    action_area="Bot_Area_Full",
    timeout=2,
):

    # 1️⃣ Eerste klik (left of right)
    ok = click_image(image, area, bot_id=bot_id, button=button, verbose=False)
    if not ok:
        return False

    # 2️⃣ Als er een action is → klik die ook
    if action:
        start = time.time()
        while time.time() - start < timeout:
            if click_image(action, action_area, bot_id=bot_id, button="left", verbose=False):
                return True
            time.sleep(0.05)
        return False

    return True


if __name__ == "__main__":
    result = advanced_image_click(
        "Item_Lobster.png",
        bot_id=1,
        button="right",
        action="Use.png"
    )
    print("Result:", result)


# python -m core.helpers.actions.advanced_image_click