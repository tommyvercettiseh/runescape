from __future__ import annotations

import time
from pathlib import Path

from core.paths import IMAGES_DIR
from vision.image_detection import detect_image


def _pack_dir(label: str, pack: str) -> Path:
    label = (label or "").strip().lower()
    return Path(IMAGES_DIR) / label / pack


def list_templates(label: str, pack: str = "templates") -> list[Path]:
    d = _pack_dir(label, pack)
    if not d.exists():
        return []
    return sorted([p for p in d.glob("*.png") if p.is_file()])


def detect_bank_best(
    label: str,
    area_name: str,
    bot_id: int = 1,
    pack: str = "active",   # "active" of "templates"
    method: str = "TM_CCOEFF_NORMED",
    min_shape: float = 75.0,
    min_color: float = 55.0,
    verbose: bool = False,
):
    templates = list_templates(label, pack=pack)
    if not templates:
        return None

    best_hit = None
    best_shape = -1.0
    best_color = -1.0
    best_name = ""

    subdir = f"{label}/{pack}"

    for p in templates:
        hit = detect_image(
            p.name,
            area_name,
            bot_id=bot_id,
            method=method,
            subdir=subdir,
            verbose=False,
        )
        if not hit:
            continue

        vorm = float(hit.get("vorm", 0.0))
        kleur = float(hit.get("kleur", 0.0))

        if vorm >= min_shape and kleur >= min_color:
            if (vorm > best_shape) or (vorm == best_shape and kleur > best_color):
                best_hit = hit
                best_shape = vorm
                best_color = kleur
                best_name = p.name

    if verbose:
        if best_hit:
            print(f"🟢 bank hit {label} best={best_name} shape={best_shape:.2f} color={best_color:.2f}")
        else:
            print(f"🔴 bank miss {label} pack={pack}")

    return best_hit


def test_bank_winners(
    label: str,
    area_name: str,
    bot_id: int = 1,
    pack: str = "templates",
    seconds: float = 10.0,
    fps: float = 8.0,
    min_shape: float = 75.0,
    min_color: float = 55.0,
    verbose: bool = True,
):
    templates = list_templates(label, pack=pack)
    frames = max(1, int(seconds * fps))
    hits = 0

    for i in range(frames):
        best = detect_bank_best(
            label=label,
            area_name=area_name,
            bot_id=bot_id,
            pack=pack,
            min_shape=min_shape,
            min_color=min_color,
            verbose=False,
        )

        if best:
            hits += 1

        if verbose:
            print(f"#{i+1:03d} hit={bool(best)}")

        time.sleep(1.0 / max(1e-6, fps))

    return {
        "frames": frames,
        "hits": hits,
        "hit_rate": hits / frames * 100.0,
    }
