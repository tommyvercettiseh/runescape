from core.config import load_json
areas = load_json("areas.json", required=True)
offsets = load_json("offsets.json", required=True)
print("areas keys:", len(areas))
print("offsets keys:", len(offsets))
