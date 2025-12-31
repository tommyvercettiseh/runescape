import json
from pathlib import Path

from core.paths import CONFIG_DIR

PRESETS_FILE = Path(CONFIG_DIR) / "templates_presets.json"

DEFAULT_PRESET = {
    "method_name": "TM_CCOEFF_NORMED",
    "vorm_drempel": 90.0,
    "kleur_drempel": 60.0,
}


def normalize_image_name(image_name: str) -> str:
    image_name = (image_name or "").strip()
    if not image_name.lower().endswith(".png"):
        image_name += ".png"
    return image_name


def load_presets() -> dict:
    if not PRESETS_FILE.exists():
        return {}
    try:
        return json.loads(PRESETS_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_presets(presets: dict) -> None:
    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2, ensure_ascii=False), encoding="utf-8")


def load_preset(image_name: str) -> dict:
    name = normalize_image_name(image_name)
    presets = load_presets()
    raw = presets.get(name, {})
    if not isinstance(raw, dict):
        raw = {}
    return DEFAULT_PRESET | raw


def save_preset(image_name: str, method_name: str, vorm_drempel: float, kleur_drempel: float) -> dict:
    name = normalize_image_name(image_name)
    presets = load_presets()
    presets[name] = {
        "method_name": str(method_name),
        "vorm_drempel": float(vorm_drempel),
        "kleur_drempel": float(kleur_drempel),
    }
    save_presets(presets)
    return presets[name]
