"""
offsets_math_draft.py

Doel:
Pure rekenmodule voor offsets.

Waarom:
Jij gebruikt offsets overal (areas, playback, image recognition).
Door dit als "pure math" te houden, kun je het overal hergebruiken zonder side-effects.
"""

from typing import Sequence


def get_bot_offset(bot_id: int, offsets_by_bot_id: dict[str, list[int]]) -> tuple[int, int]:
    """
    Haalt de offset (x,y) op voor een bot_id uit de offsets dictionary.
    """
    offset_list = offsets_by_bot_id.get(str(bot_id), [0, 0])
    offset_x = int(offset_list[0])
    offset_y = int(offset_list[1])
    return offset_x, offset_y


def apply_offset_to_box(
    box_coordinates: Sequence[int],
    bot_id: int,
    offsets_by_bot_id: dict[str, list[int]],
) -> list[int]:
    """
    Past de bot-offset toe op een bounding box: [x1,y1,x2,y2].
    """
    x1, y1, x2, y2 = box_coordinates
    offset_x, offset_y = get_bot_offset(bot_id, offsets_by_bot_id)

    return [x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y]
