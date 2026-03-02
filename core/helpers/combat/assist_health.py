from sensors.hp import low_HP
from core.helpers.actions.eat_food import eat_food

#===================================================================
def assist_health(bot_id=2, verbose=False):
    if not low_HP(bot_id=bot_id, verbose=verbose):
        if verbose:
            print("❤️ HP OK")
        return False

    if verbose:
        print("❤️ HP Low → eten")

    return eat_food(bot_id=bot_id, verbose=verbose)
#===================================================================
if __name__ == "__main__":
    eat_food(bot_id=1, verbose=True)
    print("🧪 Assist Health test")
    result = assist_health(bot_id=1, verbose=True)
    print("Result:", result)

#===================================================================
# cd C:\Users\Hesse\Desktop\Runescape
# python -m core.helpers.combat.assist_health