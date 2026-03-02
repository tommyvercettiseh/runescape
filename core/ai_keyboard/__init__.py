"""
AI Keyboard Public API
=======================

Gebruik dit bestand om clean imports te doen:

from core.ai_keyboard import (
    type_text,
    press_key,
    hold_key,
    combo,
    get_keyboard_config,
)

Interne modules blijven verborgen.
"""

from .ai_keyboard import (
    type_text,
    press_key,
    hold_key,
    combo,
)

from .ai_keyboard_settings import (
    get_keyboard_config,
)

__all__ = [
    "type_text",
    "press_key",
    "hold_key",
    "combo",
    "get_keyboard_config",
]