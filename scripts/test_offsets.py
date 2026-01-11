import sys
from core.bot_offsets import get_offset, get_bot_id

print("argv:", sys.argv)
print("get_bot_id():", get_bot_id())
print("get_offset():", get_offset())
print("get_offset(get_bot_id()):", get_offset(get_bot_id()))
