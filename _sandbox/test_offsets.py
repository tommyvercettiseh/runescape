from core.config import load_json
from core.offsets import apply_offset_to_box

offsets = load_json("offsets.json", required=True)
box = [10, 20, 30, 40]
print("box:", box)
print("bot2:", apply_offset_to_box(box, 2, offsets))
