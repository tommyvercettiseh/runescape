# === START BOOTSTRAP ===
# WAT: Timing helper voor scripts en flows.
# WAAROM: Variatie in wachttijden zonder retries/flow te verstoppen in core of wrappers.
# === END BOOTSTRAP ===


# === START IMPORTS ===
import time
import random
# === END IMPORTS ===


# === START CONSTANTS ===
# WAT: Defaults die je makkelijk kunt aanpassen.
# WAAROM: Geen magic values verspreid door scripts.
DEFAULT_SHORT_MID_CHANCE = 0.90
DEFAULT_SHORT_MID_RANGE = (0.18, 1.8)
DEFAULT_LONG_RANGE = (6.5, 9.0)
# === END CONSTANTS ===


# === START HELPERS ===
# WAT: Simpele sleep-functies voor scripts.
# WAAROM: Scripts blijven 1-regel simpel: random_sleep()

def random_sleep(
    short_mid_chance=DEFAULT_SHORT_MID_CHANCE,
    short_mid_range=DEFAULT_SHORT_MID_RANGE,
    long_range=DEFAULT_LONG_RANGE,
):
    """
    Slaapt een willekeurige tijd.

    Standaard gedrag:
    - 90% kans: korte/middelmatige sleep (0.18 – 1.8 sec)
    - 10% kans: lange sleep (6.5 – 9.0 sec)

    LET OP:
    - Geen retries, geen loops, geen extra logica.
    - Bedoeld voor scripts en flows (zoals assist_login).
    - Niet bedoeld om automatisch in core primitives te gebruiken.
    """
    # Veiligheid: zorg dat ranges kloppen (zonder ingewikkeld te doen)
    a, b = short_mid_range
    c, d = long_range

    if a > b:
        a, b = b, a
    if c > d:
        c, d = d, c

    if random.random() < short_mid_chance:
        time.sleep(random.uniform(a, b))
    else:
        time.sleep(random.uniform(c, d))


def sleep_custom(min_sec, max_sec):
    """Simpele custom sleep (handig voor scripts)."""
    lo, hi = (min_sec, max_sec) if min_sec <= max_sec else (max_sec, min_sec)
    time.sleep(random.uniform(lo, hi))
# === END HELPERS ===


# === START CLI TEST ===
# WAT: Veilige self-test.
# WAAROM: Snel checken of het werkt zonder andere modules.

if __name__ == "__main__":
    print("\n🧪 sleep_utils SELF TEST")
    print("▶ random_sleep() 5x")
    for i in range(5):
        print(f"  ▶ poging {i+1}/5")
        random_sleep()

    print("▶ sleep_custom(0.2, 0.4) 3x")
    for i in range(3):
        print(f"  ▶ poging {i+1}/3")
        sleep_custom(0.2, 0.4)

    print("✅ klaar\n")
# === END CLI TEST ===
