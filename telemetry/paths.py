from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_DIR = PROJECT_ROOT / "telemetry"
STATE_DIR = TELEMETRY_DIR / "state"

def state_path(bot_id: int) -> Path:
    return STATE_DIR / f"state_bot_{bot_id}.json"
