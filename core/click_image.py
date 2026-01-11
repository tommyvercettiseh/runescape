from __future__ import annotations

import sys
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai_cursor import move_and_click
from vision.image_detection import detect_image, detect_images


def _normalize_png(name):
    name = (name or "").strip()
    if not name:
        return name
    return name if name.lower().endswith(".png") else name + ".png"


def _rand_point_in_hit(hit, padding):
    x = int(hit.x)
    y = int(hit.y)
    w = int(hit.width)
    h = int(hit.height)

    pad = max(0, int(padding))

    x1 = x + pad
    y1 = y + pad
    x2 = x + max(1, w) - pad
    y2 = y + max(1, h) - pad

    if x2 <= x1 or y2 <= y1:
        x1, y1, x2, y2 = x, y, x + max(1, w), y + max(1, h)

    cx = random.randint(x1, max(x1, x2 - 1))
    cy = random.randint(y1, max(y1, y2 - 1))
    return cx, cy


def click_image(image_name, area_name, bot_id=1, button="left", padding=2, verbose=True):
    img = _normalize_png(image_name)

    hit = detect_image(img, area_name, bot_id=bot_id, verbose=verbose)
    if not hit:
        return False

    cx, cy = _rand_point_in_hit(hit, padding)

    if verbose:
        print(
            f"🖱️ click_image {img} in {area_name} bot={bot_id} @ ({cx},{cy}) | "
            f"vorm={hit.vorm:.2f} kleur={hit.kleur:.2f}"
        )

    move_and_click((cx, cy), button=button)
    return True


def click_images(
    image_name,
    area_name,
    bot_id=1,

    # 🧪 Test & simulatie
    dry_run=True,           # True = geen echte clicks
    skip_chance=0.08,       # 8% kans om over te slaan
    seed=None,              # bv 123 voor vaste resultaten

    # ⚙️ Gedrag
    button="left",
    padding=2,
    verbose=True,
    max_clicks=28,
    pattern=None,
    row_band_px=18,
    exclude_slots=None,
):
    if seed is not None:
        random.seed(seed)

    img = _normalize_png(image_name)
    hits = detect_images(img, area_name, bot_id=bot_id, verbose=verbose, max_hits=max_clicks)

    if not hits:
        if verbose:
            print("⚠️ Geen hits gevonden")
        return []

    band = max(6, int(row_band_px))
    exclude = set(exclude_slots or [])

    def row_id(h):
        return int(h.y // band)

    # =========================
    # Patronen
    # =========================
    def pattern_row(lr=True):
        rows = {}
        for h in hits:
            rows.setdefault(row_id(h), []).append(h)

        ordered = []
        for rk in sorted(rows.keys()):
            row_hits = sorted(rows[rk], key=lambda h: int(h.x))
            if not lr:
                row_hits.reverse()
            ordered.extend(row_hits)
        return ordered

    def pattern_snake(start_lr=True):
        rows = {}
        for h in hits:
            rows.setdefault(row_id(h), []).append(h)

        ordered = []
        row_keys = sorted(rows.keys())
        for i, rk in enumerate(row_keys):
            row_hits = sorted(rows[rk], key=lambda h: int(h.x))
            flip = (i % 2 == 1)
            if not start_lr:
                flip = not flip
            if flip:
                row_hits.reverse()
            ordered.extend(row_hits)
        return ordered

    PATTERNS = {
        "row": lambda: pattern_row(lr=True),
        "row_rev": lambda: pattern_row(lr=False),
        "snake": lambda: pattern_snake(start_lr=True),
        "snake_rev": lambda: pattern_snake(start_lr=False),
    }

    # =========================
    # Kies patroon
    # =========================
    if pattern is None:
        pattern_name = random.choice(list(PATTERNS.keys()))
    else:
        if pattern not in PATTERNS:
            raise ValueError(f"Onbekend pattern: {pattern}")
        pattern_name = pattern

    ordered = PATTERNS[pattern_name]()

    if verbose:
        mode = "Dry run 🧪" if dry_run else "Live 🔥"
        print(f"🧩 Start | Pattern={pattern_name} | Hits={len(ordered)} | Mode={mode}")

    # =========================
    # Stats
    # =========================
    clicked = []
    skipped = 0
    excluded = 0

    # =========================
    # Klik loop
    # =========================
    for idx, hit in enumerate(ordered):
        if idx in exclude:
            excluded += 1
            if verbose:
                print(f"⏭️ Excluded | Index={idx}")
            continue

        # 🙈 Skip simulatie
        if random.random() < float(skip_chance):
            skipped += 1
            if verbose:
                print(f"🙈 Skipped | Index={idx}")
            continue

        x = int(hit.x)
        y = int(hit.y)
        w = int(hit.width)
        hgt = int(hit.height)

        pad = max(0, int(padding))
        x1 = x + pad
        y1 = y + pad
        x2 = x + max(1, w) - pad
        y2 = y + max(1, hgt) - pad

        if x2 <= x1 or y2 <= y1:
            x1, y1, x2, y2 = x, y, x + w, y + hgt

        cx = random.randint(x1, max(x1, x2 - 1))
        cy = random.randint(y1, max(y1, y2 - 1))

        if verbose:
            print(f"🖱️ Target | Index={idx} | Pos=({cx},{cy}) | Vorm={hit.vorm:.2f} | Kleur={hit.kleur:.2f}")

        if dry_run:
            if verbose:
                print("🧪 Dry run | Geen echte click uitgevoerd")
        else:
            move_and_click((cx, cy), button=button)

        clicked.append((cx, cy))

    # =========================
    # Rapport
    # =========================
    if verbose:
        print("📊 Rapport")
        print(f"   Totaal hits     : {len(ordered)}")
        print(f"   Geklikt         : {len(clicked)}")
        print(f"   Overgeslagen    : {skipped}")
        print(f"   Excluded        : {excluded}")
        print(f"   Skip percentage : {skip_chance * 100:.1f}%")

    return clicked

def click_random_image(
    image_name,
    area_name,
    bot_id=1,

    # 🧪 Test & simulatie
    dry_run=True,
    seed=None,

    # ⚙️ Gedrag
    button="left",
    padding=2,
    verbose=True,
    max_hits=60,
    exclude_slots=None,
    row_band_px=18,
):
    if seed is not None:
        random.seed(seed)

    img = _normalize_png(image_name)
    hits = detect_images(img, area_name, bot_id=bot_id, verbose=verbose, max_hits=max_hits)

    if not hits:
        if verbose:
            print("⚠️ Geen hits gevonden")
        return None

    band = max(6, int(row_band_px))
    exclude = set(exclude_slots or [])

    def row_id(h):
        return int(h.y // band)

    # Optioneel: exclude op index (zelfde idee als click_images)
    rows = {}
    for h in hits:
        rows.setdefault(row_id(h), []).append(h)

    ordered = []
    for rk in sorted(rows.keys()):
        row_hits = sorted(rows[rk], key=lambda h: int(h.x))
        ordered.extend(row_hits)

    available = [h for i, h in enumerate(ordered) if i not in exclude]

    if not available:
        if verbose:
            print("⚠️ Alles is excluded")
        return None

    hit = random.choice(available)
    cx, cy = _rand_point_in_hit(hit, padding)

    if verbose:
        mode = "Dry run 🧪" if dry_run else "Live 🔥"
        print(f"🎯 Random hit | {img} | Mode={mode} | Pos=({cx},{cy}) | Vorm={hit.vorm:.2f} | Kleur={hit.kleur:.2f}")

    if not dry_run:
        move_and_click((cx, cy), button=button)

    return (cx, cy)


if __name__ == "__main__":
    
    click_random_image(
    "Item_Willow_Logs",
    "Inventory_Area",
    bot_id=1,
    dry_run=False,
    seed=None,
    verbose=True)
    
    click_image("Close_Screen_X", "Bot_Area", bot_id=1, verbose=True)
    click_images("Item_Willow_Logs", "Inventory_Area", bot_id=1, verbose=True)

    click_images(
        "Item_Willow_Logs.png",
        "Inventory_Area",
        bot_id=1,
        verbose=True,
        dry_run=False,
        skip_chance=0.09,
        seed=None)

    # alles klikken in SNAKE patroon
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="snake", max_clicks=28)

    # row patroon (gewoon L->R elke rij)
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="row", max_clicks=28)

    # skip bv eerste slot
    # click_images("Smiley.png", "Inventory_Area_Pattern", bot_id=1, pattern="snake", exclude_slots={0})

