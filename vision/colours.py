import numpy as np

COLOR_RANGES = {
    "groen":  [((35, 50, 50), (85, 255, 255))],
    "rood":   [((0, 80, 80), (10, 255, 255)), ((170, 80, 80), (179, 255, 255))],
    "oranje": [((10, 80, 80), (20, 255, 255))],
    "geel":   [((20, 80, 80), (35, 255, 255))],
    "blauw":  [((95, 50, 50), (135, 255, 255))],
    "cyaan":  [((82, 50, 50), (98, 255, 255))],
    "paars":  [((135, 50, 50), (170, 255, 255))],
}

COLOR_ALIASES = {
    "green": "groen", "g": "groen",
    "red": "rood", "r": "rood",
    "yellow": "geel", "y": "geel",
    "blue": "blauw", "b": "blauw",
    "cyan": "cyaan", "c": "cyaan",
    "purple": "paars", "p": "paars",
    "orange": "oranje", "o": "oranje",
}

def compile_ranges_np():
    return {
        k: [(np.array(lo, dtype=np.uint8), np.array(hi, dtype=np.uint8)) for lo, hi in v]
        for k, v in COLOR_RANGES.items()
    }

def normalize_colour(colour):
    if not colour:
        return colour

    c = str(colour).lower().strip()
    return COLOR_ALIASES.get(c, c)
