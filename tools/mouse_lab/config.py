from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# Mouse Lab: Hes Signature Protocol ✅ (split version)
# ============================================================

ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT / "recordings"
BASE_DIR.mkdir(parents=True, exist_ok=True)

BG = "#101010"
PINK = "#ff4da6"
TEXT = "#e6e6e6"
MUTED = "#a7a7a7"
CYAN = "#4de6ff"
YELL = "#ffe04d"
BTN_BG = "#1c1c1c"
BTN_ACTIVE = "#333333"
HIT_GREEN = "#39ff6a"
MISS_RED = "#ff3b3b"
BASE_BLUE = "#3a7bff"

TOPBAR_H = 104
SAMPLE_MS = 8
MOVE_EVENT_EVERY_N = 1

# The profile hub supplies this environment value. Direct Mouse Lab starts
# remain backwards-compatible and use NORMAL.
MODE = (os.getenv("MOUSE_LAB_LABEL") or "NORMAL").strip().upper()

STOP_SPEED_PX_S = 30.0
PAUSE_DT_MS = 22.0
TAIL_RADIUS_PX = 40

SIZE_BASE = 54
SIZE_SWEEP = 46
SIZE_SMALL = 22

PHASE1_REPS = 30
PHASE2_REPS = 36
PHASE3_BLOCKS = 16

# Point tuple indices
P_TS = 0
P_X = 1
P_Y = 2
P_BUTTONS = 3
P_ACTIVE_TRIAL = 4
P_DT_MS = 5
P_VX = 6
P_VY = 7
P_SPEED = 8
P_AX = 9
P_AY = 10
P_ACCEL = 11
P_JERK = 12
P_HEADING = 13
P_DHEADING = 14
P_CURV = 15
P_DIST_T = 16
P_INSIDE = 17
P_TARGET_TRIAL = 18
P_LABEL = 19
P_CX = 20
P_CY = 21
P_SIZE = 22
