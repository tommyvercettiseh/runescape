def get_bot_offset(bot_id, offsets_by_bot_id):
    xy = offsets_by_bot_id.get(str(bot_id), [0, 0])
    return int(xy[0]), int(xy[1])


def apply_offset_to_box(box, bot_id, offsets_by_bot_id):
    x1, y1, x2, y2 = box
    ox, oy = get_bot_offset(bot_id, offsets_by_bot_id)
    return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]
