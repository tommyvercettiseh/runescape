from __future__ import annotations

import cv2
import numpy as np


METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    # stabiele sigmoid
    x = np.clip(x, -12.0, 12.0)
    return 1.0 / (1.0 + np.exp(-x))


def scoremap_0_1(match_result: np.ndarray, method_name: str) -> np.ndarray:
    """
    Scoremap 0..1 ZONDER global minmax-normalize (die veroorzaakt ghost hits).
    Normed methods: direct clamped.
    Non-normed methods: z-score -> sigmoid voor stabiele schaal.
    """
    mr = match_result.astype(np.float32)

    # Normed methods hebben vaste betekenisvolle ranges:
    if method_name == "TM_CCOEFF_NORMED":
        # range ~[-1..1] => map naar [0..1]
        return np.clip((mr + 1.0) * 0.5, 0.0, 1.0)

    if method_name == "TM_CCORR_NORMED":
        # range ~[0..1]
        return np.clip(mr, 0.0, 1.0)

    if method_name == "TM_SQDIFF_NORMED":
        # range ~[0..1] (lager beter) => invert
        return np.clip(1.0 - mr, 0.0, 1.0)

    # Non-normed methods: score is niet “absoluut”
    # We zetten om naar relatieve “peakiness” via z-score.
    mean = float(mr.mean())
    std = float(mr.std()) + 1e-6
    z = (mr - mean) / std

    # SQDIFF: lager is beter, dus teken omdraaien (laag -> hoog)
    if method_name == "TM_SQDIFF":
        z = -z

    # Sigmoid maakt: z=0 -> 0.5, z=+3 -> ~0.95, z=+5 -> ~0.99
    # Dit gedraagt zich veel stabieler dan minmax.
    scores = _sigmoid(z)

    return scores.astype(np.float32)


def find_all_matches_with_nms(
    scores_0_1: np.ndarray,
    template_width: int,
    template_height: int,
    minimum_score_0_1: float,
    maximum_hits: int = 50,
    nms_radius_pixels: int | None = None,
):
    if nms_radius_pixels is None:
        nms_radius_pixels = max(6, int(min(template_width, template_height) * 0.35))

    ys, xs = np.where(scores_0_1 >= float(minimum_score_0_1))
    if len(xs) == 0:
        return []

    values = scores_0_1[ys, xs]
    order = np.argsort(values)[::-1]

    picked = []
    r2 = int(nms_radius_pixels * nms_radius_pixels)

    for idx in order:
        x = int(xs[idx])
        y = int(ys[idx])
        score = float(values[idx])

        too_close = False
        for px, py, _ in picked:
            dx = x - px
            dy = y - py
            if (dx * dx + dy * dy) <= r2:
                too_close = True
                break

        if too_close:
            continue

        picked.append((x, y, score))
        if len(picked) >= int(maximum_hits):
            break

    return picked


def color_score_lab_0_100(template_rgb: np.ndarray, patch_rgb: np.ndarray):
    if patch_rgb.shape[:2] != template_rgb.shape[:2]:
        patch_rgb = cv2.resize(
            patch_rgb,
            (template_rgb.shape[1], template_rgb.shape[0]),
            interpolation=cv2.INTER_AREA,
        )

    tpl = cv2.cvtColor(template_rgb, cv2.COLOR_RGB2LAB)
    pat = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2LAB)

    diff = cv2.absdiff(tpl, pat).astype(np.float32)
    mae = float(np.mean(diff))

    return float(np.clip(100.0 - (mae * 0.75), 0.0, 100.0))


def peak_zscore(scores_0_1: np.ndarray) -> float:
    """
    Optioneel: handig in je debugger om ghost hits te killen.
    Als template niet bestaat, is best-score vaak geen echte “piek”.
    """
    best = float(np.max(scores_0_1))
    avg = float(np.mean(scores_0_1))
    std = float(np.std(scores_0_1)) + 1e-6
    return (best - avg) / std