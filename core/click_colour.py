import sys
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageGrab

try:
    import pyautogui                       # optioneel: muispositie voor "nearest" picking
except Exception:
    pyautogui = None

try:
    from pynput.mouse import Controller as _MouseController  # fallback muispositie als pyautogui faalt
except Exception:
    _MouseController = None

# ============================================================
# BOOTSTRAP
# Zorgt dat imports werken vanaf elke plek (Runescape/ als root)
# ============================================================
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[1]             # Runescape/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ============================================================
# IMPORTS (project)
# ============================================================
from core.ai_cursor import move_and_click  # jouw "menselijke" cursor + click (speed_pct support)
from config.areas import load_coords       # haalt area coords uit areas.json (x1,y1,x2,y2)
from core.bot_offsets import apply_offset  # past offsets toe voor bot 1..4
from helpers.log import log                # centrale logging (jouw policy: fail altijd, ok alleen debug)
from helpers.trace import trace as _trace  # optioneel: laat zien welke .py/def/line dit aanroept
from vision.colours import normalize_colour, compile_ranges_np  # centrale HSV bron + alias mapping

# ============================================================
# LOGGING HELPERS
# Let op: _table logt altijd (log(True,...)) omdat het debug-output is
# Policy in click_colour:
#   fail  -> verbose=True => log tonen
#   ok    -> alleen tonen als debug=True
# ============================================================
def _title(msg):
    log(True, f"\n{'=' * 52}\n{msg}\n{'=' * 52}")            # "header" blok voor tabel output

def _table(rows, icon="🧾", title="Details"):
    if not rows:
        _title(f"{icon} {title}")
        log(True, "(leeg)")
        return

    left_w = max(len(str(k)) for k, _ in rows)              # uitlijnen op langste key
    _title(f"{icon} {title}")
    for k, v in rows:
        kk = str(k).strip().title()
        log(True, f"{kk:<{left_w}} | {v}")                  # nette kolommen

def _done(verbose, trace, msg="click uitgevoerd"):
    log(verbose, f"✅ Done  {msg}", trace)                   # korte "done" regel, optioneel met trace

# ============================================================
# HSV RANGES (centrale bron)
# compile_ranges_np() komt uit vision/colours.py
# Dit geeft: { "cyaan": [(np_lo,np_hi),...], "rood":[...], ... }
# ============================================================
COLOR_RANGES_NP = compile_ranges_np()

# Extra kleuren die (nog) niet in colours.py staan
_EXTRA_RANGES = {
    "wit":   [((0, 0, 200), (179, 45, 255))],               # HSV range voor wit (lage S, hoge V)
    "zwart": [((0, 0, 0), (179, 255, 45))],                 # HSV range voor zwart (lage V)
    "roze":  [((160, 60, 60), (179, 255, 255))],            # HSV range voor roze (rode hoek)
}

# Voeg extra ranges toe aan centrale dict (zonder bestaande ranges te overschrijven)
for k, ranges in _EXTRA_RANGES.items():
    if k not in COLOR_RANGES_NP:
        COLOR_RANGES_NP[k] = [(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)) for lo, hi in ranges]

# ============================================================
# HELPERS (laag niveau)
# ============================================================
def _area_bbox(area_name, bot_id):
    coords = list(load_coords(area_name))                   # coords kan tuple zijn -> list voor apply_offset
    x1, y1, x2, y2 = apply_offset(coords, bot_id)           # apply_offset verwacht [x1,y1,x2,y2]
    return x1, y1, x2, y2                                   # absolute screen coords

def _colour_mask_in_bbox(kleur, bbox):
    x1, y1, x2, y2 = bbox
    img = ImageGrab.grab(bbox=(x1, y1, x2, y2))             # screenshot van exact die area
    np_img = np.array(img)

    if np_img.shape[-1] == 4:                               # soms RGBA -> RGB
        np_img = np_img[:, :, :3]

    hsv = cv2.cvtColor(np_img, cv2.COLOR_RGB2HSV)           # RGB -> HSV (kleur detectie werkt beter)

    ranges = COLOR_RANGES_NP.get(kleur)                     # lijst van (lo,hi) arrays
    if not ranges:
        return None

    mask = None
    for lo, hi in ranges:
        m = cv2.inRange(hsv, lo, hi)                        # binaire mask (0/255) binnen range
        mask = m if mask is None else cv2.bitwise_or(mask, m)

    return mask

def _mask_pct(mask):
    return (mask > 0).mean() * 100.0                        # percentage pixels dat "aan" staat in mask

def _rand_from_mask(mask, x1, y1):
    ys, xs = np.where(mask > 0)                             # alle pixels die matchen
    if len(xs) == 0:
        return None
    i = random.randrange(len(xs))                           # random index -> random pixel
    return int(xs[i]) + x1, int(ys[i]) + y1                 # translate naar screen coords

def _get_mouse_pos():
    if pyautogui is not None:
        p = pyautogui.position()                            # pyautogui positie
        return int(p.x), int(p.y)
    if _MouseController is not None:
        p = _MouseController().position                     # pynput fallback
        return int(p[0]), int(p[1])
    return 0, 0

def _nearest_from_mask(mask, x1, y1, mouse_xy, k_nearest=200, weighted=True):
    # Kies een pixel die relatief dicht bij muis ligt (menselijker bij menu’s)
    ys, xs = np.where(mask > 0)
    n = len(xs)
    if n == 0:
        return None

    mx, my = mouse_xy

    gx = xs.astype(np.int32) + int(x1)                      # mask coords -> screen coords
    gy = ys.astype(np.int32) + int(y1)

    dx = gx - int(mx)
    dy = gy - int(my)
    dist2 = dx * dx + dy * dy                               # afstand^2 (sneller dan sqrt)

    k = max(1, min(int(k_nearest), n))
    if k == n:
        idxs = np.arange(n, dtype=np.int32)
    else:
        idxs = np.argpartition(dist2, k - 1)[:k]            # pak K kleinste afstanden

    if not weighted:
        j = int(random.choice(list(idxs)))                  # random uit nearest set
        return int(gx[j]), int(gy[j])

    d = dist2[idxs].astype(np.float64)
    w = 1.0 / (d + 1.0)                                     # dichterbij => hogere kans
    pick = random.choices(list(idxs), weights=list(w), k=1)[0]
    j = int(pick)
    return int(gx[j]), int(gy[j])

def _component_stats_at(mask, local_xy):
    # Geeft info over de connected component waar de gekozen pixel in zit
    lx, ly = int(local_xy[0]), int(local_xy[1])
    h, w = mask.shape[:2]

    if lx < 0 or ly < 0 or lx >= w or ly >= h:
        return None
    if mask[ly, lx] == 0:
        return None

    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8),
        connectivity=8
    )

    lab = int(labels[ly, lx])
    if lab <= 0 or lab >= num:
        return None

    x, y, ww, hh, area = stats[lab].tolist()
    return {
        "area_px": int(area),                               # grootte component in pixels
        "bbox_x": int(x),                                   # local bbox x
        "bbox_y": int(y),                                   # local bbox y
        "bbox_w": int(ww),                                  # local bbox w
        "bbox_h": int(hh),                                  # local bbox h
        "num_components": int(num - 1),                     # hoeveel blobs totaal gevonden
    }

def _filter_mask_by_min_component_area(mask, min_area):
    # Filter ruis: houd alleen blobs met area >= min_area
    if not min_area or min_area <= 0:
        return mask, None

    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        (mask > 0).astype(np.uint8),
        connectivity=8
    )

    keep = np.zeros(num, dtype=np.uint8)
    kept = 0

    for lab in range(1, num):                               # label 0 is background
        area = stats[lab, cv2.CC_STAT_AREA]
        if area >= min_area:
            keep[lab] = 1
            kept += 1

    filtered = (keep[labels] * 255).astype(np.uint8)
    return filtered, kept

# ============================================================
# QUICK CHECK
# Simpel: "zit er genoeg kleur in het gebied?"
# ============================================================
def has_colour_in_area(kleur, area_name, bot_id, threshold_pct=10.0):
    kleur = normalize_colour(kleur)                         # alias mapping (bv 'cyan' -> 'cyaan')
    bbox = _area_bbox(area_name, bot_id)
    mask = _colour_mask_in_bbox(kleur, bbox)
    if mask is None:
        return False
    return _mask_pct(mask) >= threshold_pct

# ============================================================
# CLICK COLOUR
# Pipeline:
#   1) bbox -> screenshot -> HSV -> mask
#   2) (optioneel) dilate         -> mask wat "dikker" maken
#   3) component filter min_size  -> kleine ruis weg
#   4) mode bepaalt target pick:
#        mask_random  = random pixel uit mask
#        deep_random  = eerst erode (krimpen) en dan random pixel (veiligste)
#        center       = contour centroid
#
# Print policy:
#   fail  -> verbose
#   ok    -> verbose alleen als debug
# ============================================================
def click_colour(
    kleur,
    area_name,
    bot_id=1,
    button="left",
    speed_pct=100.0,
    mode="deep_random",                                      # 'mask_random' | 'deep_random' | 'center'
    threshold=0.005,                                         # alleen warning: min coverage (0.005=0.5%)
    jitter_range=0,                                          # random offset rondom target pixel (menselijk)
    min_size=15,                                             # min blob size (px) om ruis weg te filteren
    dilate_px=2,                                             # mask vergroten (kan ruis ook opblazen)
    deep_erode_px=5,                                         # alleen deep_random: mask krimpen -> kern raken
    deep_tries=12,                                           # deep_random: hoe vaak proberen in deep mask
    pick_strategy="random",                                  # 'random' | 'nearest'
    nearest_k=200,                                           # nearest: pak random uit K dichtstbijzijnde pixels
    nearest_weighted=True,                                   # nearest: dichterbij = meer kans
    prefer_center=True,                                      # center mode: liever dichtbij area center
    center_bias=0.3,                                         # center mode: groter object wint iets vaker
    verbose=True,
    trace=False,                                             # toont caller (file/def/line)
    debug=False,                                             # toont succes tabellen + done
):
    kleur = normalize_colour(kleur)

    if kleur not in COLOR_RANGES_NP:
        if verbose:
            rows = [("Status", "Failed"), ("Reason", "Unknown colour"), ("Colour", kleur)]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="❌", title="Click Colour")
        return False

    bbox = _area_bbox(area_name, bot_id)
    x1, y1, x2, y2 = bbox

    mask = _colour_mask_in_bbox(kleur, bbox)
    if mask is None:
        if verbose:
            rows = [
                ("Status", "Failed"),
                ("Reason", "Mask build failed"),
                ("Colour", kleur),
                ("Area", area_name),
                ("Bot", bot_id),
            ]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="❌", title="Click Colour")
        return False

    pct = _mask_pct(mask)                                    # hoeveel % van area matcht kleur
    mask_pixels_pre = int((mask > 0).sum())                  # pixel count vóór opschoning

    # 1) DILATE: object dikker maken (optioneel)
    dilate_kernel = None
    if dilate_px and dilate_px > 0:
        k = dilate_px * 2 + 1
        dilate_kernel = (k, k)
        kernel = np.ones((k, k), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=1)

    mask_pixels_post = int((mask > 0).sum())                 # pixel count na dilate

    # 2) MIN_SIZE FILTER: ruis weg (connected components)
    mask, kept_components = _filter_mask_by_min_component_area(mask, min_size)
    mask_pixels_filtered = int((mask > 0).sum())             # pixel count na filtering

    min_pct = threshold * 100.0
    too_low = pct < min_pct                                  # warning, geen harde stop

    # ============================================================
    # MODE: mask_random / deep_random
    # ============================================================
    if mode in ("mask_random", "deep_random"):
        mouse_xy = _get_mouse_pos()

        def _pick(mask_to_use):
            if (pick_strategy or "").lower().strip() == "nearest":
                return _nearest_from_mask(
                    mask_to_use,
                    x1,
                    y1,
                    mouse_xy=mouse_xy,
                    k_nearest=nearest_k,
                    weighted=nearest_weighted,
                )
            return _rand_from_mask(mask_to_use, x1, y1)

        chosen = None
        erode_kernel = None

        # deep_random: eerst erode -> klik in kern, minder rand/ruis
        if mode == "deep_random":
            if deep_erode_px and deep_erode_px > 0:
                k = deep_erode_px * 2 + 1
                erode_kernel = (k, k)
                kernel = np.ones((k, k), np.uint8)
                deep_mask = cv2.erode(mask, kernel, iterations=1)
            else:
                deep_mask = mask

            for _ in range(max(1, deep_tries)):
                chosen = _pick(deep_mask)
                if chosen is not None:
                    break

            if chosen is None:
                chosen = _pick(mask)
        else:
            chosen = _pick(mask)

        if chosen is None:
            if verbose:
                rows = [
                    ("Status", "Failed"),
                    ("Mode", mode),
                    ("Colour", kleur.upper()),
                    ("Area", area_name),
                    ("Bot", bot_id),
                    ("Bbox", f"({x1},{y1},{x2},{y2})"),
                    ("Mask Coverage", f"{pct:.2f}%"),
                    ("Mask Pixels (pre)", f"{mask_pixels_pre:,}"),
                    ("Mask Pixels (post)", f"{mask_pixels_post:,}"),
                    ("Mask Pixels (filtered)", f"{mask_pixels_filtered:,}"),
                    ("Min Size", f"{min_size} px (component)"),
                    ("Reason", "No pixels after filtering"),
                ]
                if kept_components is not None:
                    rows.append(("Kept Components", kept_components))
                if dilate_kernel:
                    rows.append(("Dilate", f"{dilate_px}px  kernel={dilate_kernel[0]}x{dilate_kernel[1]}"))
                if mode == "deep_random" and erode_kernel:
                    rows.append(("Erode", f"{deep_erode_px}px  kernel={erode_kernel[0]}x{erode_kernel[1]}"))
                if trace:
                    rows.append(("Caller", _trace(True)))
                _table(rows, icon="🚫", title="Click Colour")
            return False

        mx, my = chosen

        # component stats: handig voor debug/tuning
        local_x = mx - x1
        local_y = my - y1
        comp = _component_stats_at(mask, (local_x, local_y))

        # jitter: menselijk "naast perfect"
        tx = mx + random.randint(-jitter_range, jitter_range)
        ty = my + random.randint(-jitter_range, jitter_range)

        # echte click
        move_and_click((tx, ty), button=button, speed_pct=speed_pct)

        # succes logs alleen in debug
        if verbose and debug:
            rows = [
                ("Status", "Ok (click)"),
                ("Mode", mode),
                ("Colour", kleur.upper()),
                ("Area", area_name),
                ("Bot", bot_id),
                ("Bbox", f"({x1},{y1},{x2},{y2})"),
                ("Mask Coverage", f"{pct:.2f}%"),
                ("Min Size", f"{min_size} px (component)"),
                ("Chosen", f"({mx},{my})"),
                ("Jitter", f"±{jitter_range}"),
                ("Click", f"({tx},{ty})  button={button}  speed={speed_pct:.0f}%"),
            ]
            if too_low:
                rows.append(("Warning", f"Coverage low: {pct:.3f}% < {min_pct:.3f}%"))
            if comp:
                rows.append(("Component Area", f"{comp['area_px']:,} px"))
                rows.append(("Component Box", f"{comp['bbox_w']}x{comp['bbox_h']} (local {comp['bbox_x']},{comp['bbox_y']})"))
                rows.append(("Components", comp["num_components"]))
            if (pick_strategy or "").lower().strip() == "nearest":
                rows.append(("Pick", f"Nearest  k={nearest_k}  weighted={nearest_weighted}"))
                rows.append(("Mouse", f"({mouse_xy[0]},{mouse_xy[1]})"))
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="🧪", title="Click Colour")

        _done(verbose and debug, trace)
        return True

    # ============================================================
    # MODE: center
    # pakt contour centroid -> stabiel, maar voorspelbaarder
    # ============================================================
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        if verbose:
            rows = [
                ("Status", "Failed"),
                ("Mode", mode),
                ("Colour", kleur.upper()),
                ("Area", area_name),
                ("Bot", bot_id),
                ("Bbox", f"({x1},{y1},{x2},{y2})"),
                ("Mask Coverage", f"{pct:.2f}%"),
                ("Reason", "No contours found"),
            ]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="🚫", title="Click Colour")
        return False

    contours = [c for c in contours if cv2.contourArea(c) >= min_size]
    if not contours:
        if verbose:
            rows = [
                ("Status", "Failed"),
                ("Mode", mode),
                ("Colour", kleur.upper()),
                ("Min Size", f"{min_size} px"),
                ("Reason", "Contours exist, but all are under min_size"),
            ]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="📏", title="Click Colour")
        return False

    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    def _center_score(contour):
        M = cv2.moments(contour)
        if M["m00"] == 0:
            return 1e18
        cx0 = int(M["m10"] / M["m00"]) + x1
        cy0 = int(M["m01"] / M["m00"]) + y1
        dist2 = (cx0 - center_x) ** 2 + (cy0 - center_y) ** 2
        area0 = cv2.contourArea(contour)
        return dist2 - (center_bias * area0)

    if prefer_center:
        gekozen = min(contours, key=_center_score)
        pick_note = f"Center (bias={center_bias})"
    else:
        gekozen = max(contours, key=cv2.contourArea)
        pick_note = "Largest"

    M = cv2.moments(gekozen)
    if M["m00"] == 0:
        if verbose:
            rows = [("Status", "Failed"), ("Mode", "center"), ("Reason", "Moments m00=0 (cannot centroid)")]
            if trace:
                rows.append(("Caller", _trace(True)))
            _table(rows, icon="⚠️", title="Click Colour")
        return False

    cx = int(M["m10"] / M["m00"]) + x1
    cy = int(M["m01"] / M["m00"]) + y1

    tx = cx + random.randint(-jitter_range, jitter_range)
    ty = cy + random.randint(-jitter_range, jitter_range)

    move_and_click((tx, ty), button=button, speed_pct=speed_pct)

    if verbose and debug:
        rows = [
            ("Status", "Ok (click)"),
            ("Mode", "Center"),
            ("Pick", pick_note),
            ("Colour", kleur.upper()),
            ("Area", area_name),
            ("Bot", bot_id),
            ("Bbox", f"({x1},{y1},{x2},{y2})"),
            ("Mask Coverage", f"{pct:.2f}%"),
            ("Min Size", f"{min_size} px"),
            ("Centroid", f"({cx},{cy})"),
            ("Jitter", f"±{jitter_range}"),
            ("Click", f"({tx},{ty})  button={button}  speed={speed_pct:.0f}%"),
        ]
        if trace:
            rows.append(("Caller", _trace(True)))
        _table(rows, icon="🧲", title="Click Colour")

    _done(verbose and debug, trace)
    return True

# ============================================================
# RUN (test)
# ============================================================
if __name__ == "__main__":
    click_colour(
        "cyaan",
        "Bot_Area",
        bot_id=1,
        mode="deep_random",
        deep_erode_px=3,
        jitter_range=3,
        min_size=400,
        dilate_px=0,
        verbose=True,
        trace=True,
        debug=True,
    )
