import tkinter as tk
import random
import time
import math
import csv
import json
from pathlib import Path

BASE_DIR = Path("mouse_profile")

def date_stamp_local():
    return time.strftime("%Y-%m-%d")

def datetime_stamp_local():
    return time.strftime("%Y-%m-%d_%H%M%S")

def unique_run_dir(base_dir: Path) -> Path:
    day_dir = base_dir / date_stamp_local()
    day_dir.mkdir(parents=True, exist_ok=True)

    base_name = datetime_stamp_local()
    run_dir = day_dir / base_name
    if not run_dir.exists():
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    i = 2
    while True:
        alt = day_dir / f"{base_name}_{i}"
        if not alt.exists():
            alt.mkdir(parents=True, exist_ok=False)
            return alt
        i += 1

RUN_DIR = unique_run_dir(BASE_DIR)

POINTS_CSV = RUN_DIR / "mouse_points.csv"
TRIALS_CSV = RUN_DIR / "trials.csv"
SEGMENTS_CSV = RUN_DIR / "segments.csv"
SUMMARY_TXT = RUN_DIR / "summary.txt"
META_JSON = RUN_DIR / "meta.json"
PROFILE_JSON = RUN_DIR / "profile_preview.json"
RUNS_INDEX = BASE_DIR / "runs_index.csv"

# fullscreen / resolutie
FORCE_RES = None  # None=auto, of (1920,1080) of (1080,1920)

BG = "#101010"
PINK = "#ff4da6"
TEXT = "#e6e6e6"
MUTED = "#a7a7a7"
CYAN = "#4de6ff"
YELL = "#ffe04d"
BTN_BG = "#1c1c1c"
BTN_BG2 = "#262626"
BTN_FG = TEXT
BTN_ACTIVE = "#333333"
HIT_GREEN = "#39ff6a"
MISS_RED = "#ff3b3b"

SAMPLE_MS = 8
DEFAULT_GOAL_TRIALS = 60
N_ACTIVE_TARGETS = 3

# fixed mode
MODE = "NORMAL"

SIZE_SMALL = 24
SIZE_MED = 36
SIZE_BIG = 72

TAIL_RADIUS_PX = 40
STOP_SPEED_PX_S = 30.0
PAUSE_DT_MS = 22.0

FREE_ROAM_SECONDS = 10.0

USE_FIXED_SEED = True
SEED = 1337
USE_FIXED_SCENARIO_ORDER = True

SCENARIOS = [
    ("PRECISION_SMALL", SIZE_SMALL, 280, 1200, {}),
    ("PRECISION_BIG", SIZE_BIG, 280, 1200, {}),
    ("FAST_TRAVEL", SIZE_MED, 1200, 2200, {}),
    ("MICRO_ADJUST", SIZE_MED, 40, 220, {}),
    ("EDGE_CASE", SIZE_MED, 300, 1600, {"edge_bias": True}),
    ("SWITCH_TARGET", SIZE_MED, 500, 1600, {"paired": True}),
    ("DRAG", SIZE_MED, 300, 1400, {"drag": True}),
]

FREE_ROAM_MODES = {
    "ROAM": ("FREE_ROAM_ROAM", "Beweeg alsof je zoekt 🙂"),
    "HOVER": ("FREE_ROAM_HOVER_READ", "Hover alsof je leest 👀"),
    "PANIC": ("FREE_ROAM_PANIC_FAST", "Snel heen en weer ⚡"),
}

TRACK_SECONDS = 10.0
TRACK_SIZE = 44
TRACK_MAX_SPEED_PX_S = 420.0
TRACK_ACCEL_PX_S2 = 1400.0

TOPBAR_H = 86


def now():
    return time.perf_counter()

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0

def median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return float(s[mid]) if n % 2 else float((s[mid - 1] + s[mid]) / 2)

def percentile(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    if p <= 0:
        return float(s[0])
    if p >= 100:
        return float(s[-1])
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return float(d0 + d1)

def angle_between(v1, v2):
    x1, y1 = v1
    x2, y2 = v2
    d1 = math.hypot(x1, y1)
    d2 = math.hypot(x2, y2)
    if d1 == 0 or d2 == 0:
        return 0.0
    dot = (x1 * x2 + y1 * y2) / (d1 * d2)
    dot = clamp(dot, -1.0, 1.0)
    return math.acos(dot)

def safe_write_json(path: Path, obj: dict):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

def append_runs_index(row: dict):
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "run_dir",
        "created_local",
        "seed",
        "fixed_seed",
        "fixed_order",
        "goal_trials",
        "sample_ms",
        "trials_logged",
        "segments_logged",
    ]
    file_exists = RUNS_INDEX.exists()
    with open(RUNS_INDEX, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in header})

def fmt_s(x):
    return f"{x:.1f}s"

def stat_pack(vals):
    return {
        "p10": round(percentile(vals, 10), 3),
        "p50": round(percentile(vals, 50), 3),
        "p90": round(percentile(vals, 90), 3),
    }

def norm01(x, lo, hi):
    if hi <= lo:
        return 0.5
    return float(clamp((x - lo) / (hi - lo), 0.0, 1.0))


class MouseLab:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.update_idletasks()
        sw = int(self.root.winfo_screenwidth())
        sh = int(self.root.winfo_screenheight())
        if FORCE_RES is not None:
            self.WIN_W, self.WIN_H = int(FORCE_RES[0]), int(FORCE_RES[1])
        else:
            self.WIN_W, self.WIN_H = sw, sh

        self.root.title("Mouse Lab 🎯 (NORMAL only)")
        self.root.configure(bg=BG)
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+0+0")
        self.root.resizable(False, False)

        self.topbar = tk.Frame(self.root, bg=BG, height=TOPBAR_H)
        self.topbar.pack(side="top", fill="x")
        self.topbar.pack_propagate(False)

        self.row1 = tk.Frame(self.topbar, bg=BG)
        self.row1.pack(side="top", fill="x", padx=10, pady=(8, 2))
        self.row2 = tk.Frame(self.topbar, bg=BG)
        self.row2.pack(side="top", fill="x", padx=10, pady=(2, 8))

        self.status_lbl = tk.Label(self.row1, text="PAUSED ⏸️", fg=TEXT, bg=BG, font=("Segoe UI", 12, "bold"))
        self.status_lbl.pack(side="left")

        self.mode_lbl = tk.Label(self.row1, text=f"Mode: {MODE}", fg=YELL, bg=BG, font=("Segoe UI", 11, "bold"))
        self.mode_lbl.pack(side="left", padx=(14, 0))

        self.timer_lbl = tk.Label(self.row1, text="", fg=CYAN, bg=BG, font=("Segoe UI", 11))
        self.timer_lbl.pack(side="left", padx=(14, 0))

        self.progress_lbl = tk.Label(self.row1, text="0/60", fg=MUTED, bg=BG, font=("Segoe UI", 11))
        self.progress_lbl.pack(side="left", padx=(14, 0))

        # goal chooser
        self.goal_var = tk.IntVar(value=DEFAULT_GOAL_TRIALS)
        goal_frame = tk.Frame(self.row1, bg=BG)
        goal_frame.pack(side="left", padx=(18, 0))
        tk.Label(goal_frame, text="Target goal:", fg=MUTED, bg=BG, font=("Segoe UI", 10)).pack(side="left")
        self.goal_spin = tk.Spinbox(
            goal_frame,
            from_=10,
            to=9999,
            increment=10,
            width=6,
            textvariable=self.goal_var,
            bg=BTN_BG2,
            fg=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            justify="center",
            insertbackground=TEXT,
        )
        self.goal_spin.pack(side="left", padx=(6, 6))
        self.btn_apply_goal = self._btn(goal_frame, "Apply", self.apply_goal, bg=BTN_BG2)
        self.btn_apply_goal.pack(side="left")

        self.btn_start = self._btn(self.row1, "Start", self.ui_start_pause)
        self.btn_start.pack(side="right", padx=(6, 0))

        self.btn_finish = self._btn(self.row1, "Finish & Save", self.finish_and_save, bg="#2a2a2a")
        self.btn_finish.pack(side="right", padx=(6, 0))

        self.btn_save_exit = self._btn(self.row1, "Save & Exit", self.stop_and_save, bg="#2a2a2a")
        self.btn_save_exit.pack(side="right", padx=(6, 0))

        self.btn_reset = self._btn(self.row1, "Reset", self.reset_session, bg="#2a2a2a")
        self.btn_reset.pack(side="right", padx=(6, 0))

        self.btn_skip = self._btn(self.row1, "Skip target", self.skip_nearest, bg="#2a2a2a")
        self.btn_skip.pack(side="right", padx=(6, 0))

        # segments row
        self.segs_frame = tk.Frame(self.row2, bg=BG)
        self.segs_frame.pack(side="left")
        tk.Label(self.segs_frame, text="Segments:", fg=MUTED, bg=BG, font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))

        self.btn_roam = self._btn(self.segs_frame, "ROAM 10s", lambda: self.start_free_roam("ROAM"), bg=BTN_BG2)
        self.btn_roam.pack(side="left", padx=(0, 6))

        self.btn_hover = self._btn(self.segs_frame, "HOVER/READ 10s", lambda: self.start_free_roam("HOVER"), bg=BTN_BG2)
        self.btn_hover.pack(side="left", padx=(0, 6))

        self.btn_panic = self._btn(self.segs_frame, "PANIC 10s", lambda: self.start_free_roam("PANIC"), bg=BTN_BG2)
        self.btn_panic.pack(side="left", padx=(0, 6))

        self.btn_track = self._btn(self.segs_frame, "TRACK 10s", self.start_track_moving, bg=BTN_BG2)
        self.btn_track.pack(side="left", padx=(0, 6))

        self.info_lbl = tk.Label(self.row2, text=f"Saving to: {RUN_DIR}", fg=MUTED, bg=BG, font=("Segoe UI", 9))
        self.info_lbl.pack(side="right")

        self.canvas = tk.Canvas(self.root, width=self.WIN_W, height=self.WIN_H - TOPBAR_H, bg=BG, highlightthickness=0)
        self.canvas.pack(side="top", fill="both", expand=True)

        # mouse events MUST be on canvas
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", self.on_l_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_l_up)

        # hotkeys minimal
        self.root.bind("<KeyPress-space>", lambda e: self.ui_start_pause())
        self.root.bind("<KeyPress-Escape>", self.stop_and_save)
        self.root.bind("<KeyPress-r>", self.reset_session)
        self.root.bind("<KeyPress-Return>", self.skip_nearest)
        self.root.bind("<KeyPress-F6>", lambda e: self.start_free_roam("ROAM"))
        self.root.bind("<KeyPress-F7>", lambda e: self.start_free_roam("HOVER"))
        self.root.bind("<KeyPress-F8>", lambda e: self.start_free_roam("PANIC"))
        self.root.bind("<KeyPress-F9>", lambda e: self.start_track_moving())
        self.root.protocol("WM_DELETE_WINDOW", self.stop_and_save)

        if USE_FIXED_SEED:
            random.seed(SEED)

        self.running = False
        self.session_start = None
        self.mouse_x = 0
        self.mouse_y = 0
        self.buttons = 0

        self.points = []
        self.trials = []
        self.segments = []

        self.active_targets = {}
        self.hits_done = 0
        self.current_trial_id = 0

        self.last_sample_ts = None
        self.last_sample_xy = None

        self.drag_active = False
        self.drag_line_id = None
        self.drag_target_trial_id = None

        self.free_roam_active = False
        self.free_roam_label = None
        self.free_roam_end_ts = None
        self.free_roam_segment_start_ts = None

        self.track_active = False
        self.track_label = "TRACK_MOVING"
        self.track_end_ts = None
        self.track_start_ts = None
        self.track_target_id = None
        self.track_vx = 0.0
        self.track_vy = 0.0
        self.track_x = 0.0
        self.track_y = 0.0
        self.track_inside_ms = 0.0
        self.track_dist_samples = []

        self._scenario_index = 0
        if USE_FIXED_SCENARIO_ORDER:
            self._scenario_order = [s[0] for s in SCENARIOS]
        else:
            self._scenario_order = [s[0] for s in SCENARIOS]
            random.shuffle(self._scenario_order)

        # goal
        self.goal_trials = int(self.goal_var.get())

        self.update_ui()
        self.update_timer_loop()

    def _btn(self, parent, text, cmd, bg=BTN_BG):
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=BTN_FG,
            activebackground=BTN_ACTIVE,
            activeforeground=BTN_FG,
            relief="flat",
            padx=10,
            pady=6,
            font=("Segoe UI", 10),
            cursor="hand2",
        )

    def apply_goal(self):
        try:
            v = int(self.goal_var.get())
        except Exception:
            v = DEFAULT_GOAL_TRIALS
        v = max(10, min(9999, v))
        self.goal_trials = v
        self.goal_var.set(v)
        self.update_ui()

    def update_ui(self):
        self.status_lbl.config(text="RUNNING ✅" if self.running else "PAUSED ⏸️")
        self.mode_lbl.config(text=f"Mode: {MODE}")
        self.progress_lbl.config(text=f"{self.hits_done}/{self.goal_trials}")
        self.btn_start.config(text="Pause" if self.running else "Start")

    def update_timer_loop(self):
        ts = now()
        timer_txt = ""

        if self.free_roam_active and self.free_roam_end_ts is not None:
            remaining = self.free_roam_end_ts - ts
            timer_txt = f"{self.free_roam_label} • {fmt_s(max(0.0, remaining))}"
            if remaining <= 0:
                self.end_free_roam_segment(outcome="DONE")

        if self.track_active and self.track_end_ts is not None:
            remaining = self.track_end_ts - ts
            timer_txt = f"{self.track_label} • {fmt_s(max(0.0, remaining))}"
            if remaining <= 0:
                self.end_track_moving(outcome="DONE")

        self.timer_lbl.config(text=timer_txt)
        self.update_ui()
        self.root.after(80, self.update_timer_loop)

    def ui_start_pause(self):
        if not self.running:
            self.running = True
            if self.session_start is None:
                self.session_start = now()
            self.last_sample_ts = None
            self.last_sample_xy = None
            self.sample_loop()
        else:
            self.running = False
        self.update_ui()

    def reset_session(self, _=None):
        for tid in list(self.active_targets.keys()):
            self.canvas.delete(tid)
        self.active_targets.clear()

        if self.drag_line_id is not None:
            self.canvas.delete(self.drag_line_id)
        if self.track_target_id is not None:
            self.canvas.delete(self.track_target_id)

        self.running = False
        self.session_start = None
        self.buttons = 0

        self.points = []
        self.trials = []
        self.segments = []

        self.hits_done = 0
        self.current_trial_id = 0

        self.last_sample_ts = None
        self.last_sample_xy = None

        self.drag_active = False
        self.drag_line_id = None
        self.drag_target_trial_id = None

        self.free_roam_active = False
        self.free_roam_label = None
        self.free_roam_end_ts = None
        self.free_roam_segment_start_ts = None

        self.track_active = False
        self.track_end_ts = None
        self.track_start_ts = None
        self.track_target_id = None
        self.track_inside_ms = 0.0
        self.track_dist_samples = []
        self.track_vx = 0.0
        self.track_vy = 0.0
        self.track_x = 0.0
        self.track_y = 0.0

        self.timer_lbl.config(text="")
        self.update_ui()

    def finish_and_save(self):
        # stop maar laat window open (handig om meteen nieuwe run te starten of logs te checken)
        self.running = False
        if self.free_roam_active:
            self.end_free_roam_segment(outcome="ABORT")
        if self.track_active:
            self.end_track_moving(outcome="ABORT")
        self.save_logs()
        self.status_lbl.config(text="SAVED ✅ (you can Reset or Exit)")
        self.update_ui()

    def stop_and_save(self, _=None):
        self.running = False
        if self.free_roam_active:
            self.end_free_roam_segment(outcome="ABORT")
        if self.track_active:
            self.end_track_moving(outcome="ABORT")

        self.save_logs()
        try:
            self.root.destroy()
        except Exception:
            pass

    # visuals
    def flash_target(self, tid, color, ms=120):
        if tid is None:
            return
        try:
            prev = self.canvas.itemcget(tid, "fill")
            self.canvas.itemconfig(tid, fill=color)
            self.root.after(ms, lambda: self.canvas.itemconfig(tid, fill=prev))
        except Exception:
            pass

    # input handlers
    def on_motion(self, e):
        self.mouse_x = int(clamp(e.x, 0, self.WIN_W))
        self.mouse_y = int(clamp(e.y, 0, self.WIN_H - TOPBAR_H))
        if self.drag_active and self.drag_line_id is not None:
            x0, y0 = self.canvas.coords(self.drag_line_id)[:2]
            self.canvas.coords(self.drag_line_id, x0, y0, self.mouse_x, self.mouse_y)

    def on_l_down(self, e):
        self.mouse_x = int(clamp(e.x, 0, self.WIN_W))
        self.mouse_y = int(clamp(e.y, 0, self.WIN_H - TOPBAR_H))
        self.buttons = 1
        if self.running and (not self.track_active):
            tid = self.find_nearest_target()
            if tid is not None:
                t = self.active_targets[tid]
                if t.get("is_drag", False):
                    self.start_drag(t)
                    return
            self.try_hit()

    def on_l_up(self, e):
        self.mouse_x = int(clamp(e.x, 0, self.WIN_W))
        self.mouse_y = int(clamp(e.y, 0, self.WIN_H - TOPBAR_H))
        self.buttons = 0
        if self.running and self.drag_active:
            self.finish_drag()

    def sample_loop(self):
        if not self.running:
            return

        ts = now()
        if self.last_sample_ts is None:
            dt_ms = 0.0
            speed = 0.0
        else:
            dt = ts - self.last_sample_ts
            dt_ms = dt * 1000.0
            if self.last_sample_xy is None or dt <= 0:
                speed = 0.0
            else:
                d = dist(self.last_sample_xy, (self.mouse_x, self.mouse_y))
                speed = d / dt

        self.last_sample_ts = ts
        self.last_sample_xy = (self.mouse_x, self.mouse_y)

        active_trial_id = self.pick_primary_trial_id()
        self.points.append((ts, self.mouse_x, self.mouse_y, self.buttons, active_trial_id, dt_ms, speed, MODE))

        if self.track_active:
            self.track_tick(ts, dt_ms)

        if (not self.track_active) and self.running and len(self.active_targets) == 0 and self.hits_done < self.goal_trials:
            while len(self.active_targets) < N_ACTIVE_TARGETS:
                self.spawn_target()

        self.root.after(SAMPLE_MS, self.sample_loop)

    def pick_primary_trial_id(self):
        if not self.active_targets:
            return None
        m = (self.mouse_x, self.mouse_y)
        best_trial = None
        best_d = 1e18
        for _, t in self.active_targets.items():
            d = dist(m, t["center"])
            if d < best_d:
                best_d = d
                best_trial = t["trial_id"]
        return best_trial

    # targets
    def pick_scenario(self):
        if USE_FIXED_SCENARIO_ORDER:
            name = self._scenario_order[self._scenario_index % len(self._scenario_order)]
            self._scenario_index += 1
            for s in SCENARIOS:
                if s[0] == name:
                    return s
            return SCENARIOS[0]
        return random.choice(SCENARIOS)

    def next_trial_id(self):
        self.current_trial_id += 1
        return self.current_trial_id

    def pick_point_at_distance(self, start, dmin, dmax, edge_bias=False):
        sx, sy = start
        canvas_h = self.WIN_H - TOPBAR_H
        for _ in range(80):
            if edge_bias and random.random() < 0.65:
                edge = random.choice(["L", "R", "T", "B"])
                if edge == "L":
                    x = random.randint(20, 80)
                    y = random.randint(40, canvas_h - 60)
                elif edge == "R":
                    x = random.randint(self.WIN_W - 80, self.WIN_W - 20)
                    y = random.randint(40, canvas_h - 60)
                elif edge == "T":
                    x = random.randint(60, self.WIN_W - 60)
                    y = random.randint(40, 90)
                else:
                    x = random.randint(60, self.WIN_W - 60)
                    y = random.randint(canvas_h - 120, canvas_h - 60)
            else:
                x = random.randint(60, self.WIN_W - 60)
                y = random.randint(60, canvas_h - 70)

            d = dist((sx, sy), (x, y))
            if dmin <= d <= dmax:
                return x, y
        return random.randint(60, self.WIN_W - 60), random.randint(60, canvas_h - 70)

    def add_target(self, cx, cy, size, label, start, trial_id, group_id=None, is_drag=False):
        x1 = int(cx - size / 2)
        y1 = int(cy - size / 2)
        x2 = x1 + size
        y2 = y1 + size
        tid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=PINK, outline="")
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        spawn_ts = now()
        difficulty = (dist(start, center) / size) if size > 0 else 0.0

        self.active_targets[tid] = {
            "canvas_id": tid,
            "trial_id": trial_id,
            "label": label,
            "mode": MODE,
            "size": size,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": center,
            "spawn_ts": spawn_ts,
            "start_xy": start,
            "difficulty": difficulty,
            "miss_clicks": 0,
            "start_point_index": len(self.points),
            "is_drag": bool(is_drag),
            "paired_group": group_id,
        }

    def spawn_target(self):
        if self.hits_done >= self.goal_trials:
            return

        label, size, dmin, dmax, extra = self.pick_scenario()
        start = (self.mouse_x, self.mouse_y)

        edge_bias = bool(extra.get("edge_bias", False))
        paired = bool(extra.get("paired", False))
        do_drag = bool(extra.get("drag", False))

        if paired:
            group_id = f"g{self.current_trial_id + 1}"
            trial_id_a = self.next_trial_id()
            trial_id_b = self.next_trial_id()

            cx, cy = self.pick_point_at_distance(start, dmin, dmax, edge_bias=edge_bias)
            cx2, cy2 = self.pick_point_at_distance((cx, cy), 120, 280, edge_bias=False)

            self.add_target(cx, cy, size, label, start, trial_id_a, group_id=group_id, is_drag=False)
            self.add_target(cx2, cy2, size, label, start, trial_id_b, group_id=group_id, is_drag=False)
            return

        trial_id = self.next_trial_id()
        cx, cy = self.pick_point_at_distance(start, dmin, dmax, edge_bias=edge_bias)
        self.add_target(cx, cy, size, label, start, trial_id, group_id=None, is_drag=do_drag)

    def find_nearest_target(self):
        if not self.active_targets:
            return None
        m = (self.mouse_x, self.mouse_y)
        best_tid = None
        best_d = 1e18
        for tid, t in self.active_targets.items():
            d = dist(m, t["center"])
            if d < best_d:
                best_d = d
                best_tid = tid
        return best_tid

    # drag
    def start_drag(self, target):
        self.drag_active = True
        self.drag_target_trial_id = target["trial_id"]
        self.drag_line_id = self.canvas.create_line(
            self.mouse_x, self.mouse_y, self.mouse_x, self.mouse_y, fill=CYAN, width=2
        )

    def finish_drag(self):
        tid_hit = None
        for tid, t in self.active_targets.items():
            if t.get("is_drag", False) and t["trial_id"] == self.drag_target_trial_id:
                tid_hit = tid
                break

        if self.drag_line_id is not None:
            self.canvas.delete(self.drag_line_id)

        self.drag_active = False
        self.drag_line_id = None

        if tid_hit is None:
            self.drag_target_trial_id = None
            return

        t = self.active_targets.pop(tid_hit)
        self.canvas.delete(tid_hit)

        end_ts = now()
        end_point_index = len(self.points)

        inside = (t["x1"] <= self.mouse_x <= t["x2"] and t["y1"] <= self.mouse_y <= t["y2"])
        outcome = "DRAG_HIT" if inside else "DRAG_MISS"
        trial = self.compute_trial_metrics(t, end_ts, end_point_index, outcome=outcome)
        self.trials.append(trial)

        self.hits_done += 1
        self.drag_target_trial_id = None

        if self.hits_done >= self.goal_trials:
            self.finish_and_save()
            return

        while len(self.active_targets) < N_ACTIVE_TARGETS:
            self.spawn_target()

        self.update_ui()

    # click logic
    def skip_nearest(self, _=None):
        if (not self.running) or self.track_active:
            return
        tid = self.find_nearest_target()
        if tid is None:
            return

        t = self.active_targets.pop(tid)
        self.canvas.delete(tid)

        end_ts = now()
        end_point_index = len(self.points)
        trial = self.compute_trial_metrics(t, end_ts, end_point_index, outcome="SKIPPED")
        self.trials.append(trial)

        self.hits_done += 1
        if self.hits_done >= self.goal_trials:
            self.finish_and_save()
            return

        while len(self.active_targets) < N_ACTIVE_TARGETS:
            self.spawn_target()

        self.update_ui()

    def try_hit(self):
        hit_tid = None
        for tid, t in self.active_targets.items():
            if t["x1"] <= self.mouse_x <= t["x2"] and t["y1"] <= self.mouse_y <= t["y2"]:
                hit_tid = tid
                break

        if hit_tid is None:
            near_tid = self.find_nearest_target()
            if near_tid is not None:
                self.active_targets[near_tid]["miss_clicks"] += 1
                self.flash_target(near_tid, MISS_RED, ms=110)
            return

        self.flash_target(hit_tid, HIT_GREEN, ms=110)

        t = self.active_targets.pop(hit_tid)
        self.root.after(120, lambda tid=hit_tid: self.canvas.delete(tid))

        end_ts = now()
        end_point_index = len(self.points)

        if t.get("paired_group"):
            group = t["paired_group"]
            for tid2, t2 in list(self.active_targets.items()):
                if t2.get("paired_group") == group:
                    t2["paired_group"] = None

        trial = self.compute_trial_metrics(t, end_ts, end_point_index, outcome="HIT")
        self.trials.append(trial)

        self.hits_done += 1
        if self.hits_done >= self.goal_trials:
            self.finish_and_save()
            return

        while len(self.active_targets) < N_ACTIVE_TARGETS:
            self.spawn_target()

        self.update_ui()

    # segments
    def start_free_roam(self, key):
        if not self.running:
            return
        if self.track_active or self.free_roam_active:
            return
        label, _tip = FREE_ROAM_MODES[key]
        self.free_roam_active = True
        self.free_roam_label = label
        self.free_roam_end_ts = now() + FREE_ROAM_SECONDS
        self.free_roam_segment_start_ts = now()
        self.timer_lbl.config(text=f"{label} • {fmt_s(FREE_ROAM_SECONDS)}")

    def end_free_roam_segment(self, outcome="DONE"):
        end_ts = now()
        self.segments.append({
            "start_ts": self.free_roam_segment_start_ts,
            "end_ts": end_ts,
            "label": self.free_roam_label,
            "outcome": outcome,
            "notes": json.dumps({"mode": MODE}, ensure_ascii=False),
        })
        self.free_roam_active = False
        self.free_roam_label = None
        self.free_roam_end_ts = None
        self.free_roam_segment_start_ts = None

    # tracking
    def start_track_moving(self):
        if not self.running:
            return
        if self.free_roam_active or self.track_active:
            return

        for tid in list(self.active_targets.keys()):
            self.canvas.delete(tid)
        self.active_targets.clear()

        self.track_active = True
        self.track_start_ts = now()
        self.track_end_ts = self.track_start_ts + TRACK_SECONDS
        self.track_inside_ms = 0.0
        self.track_dist_samples = []

        w = self.WIN_W
        h = self.WIN_H - TOPBAR_H

        self.track_x = random.randint(120, w - 120)
        self.track_y = random.randint(120, h - 120)
        self.track_vx = random.uniform(-140, 140)
        self.track_vy = random.uniform(-140, 140)

        self.track_target_id = self.canvas.create_rectangle(
            int(self.track_x - TRACK_SIZE / 2),
            int(self.track_y - TRACK_SIZE / 2),
            int(self.track_x + TRACK_SIZE / 2),
            int(self.track_y + TRACK_SIZE / 2),
            fill=YELL,
            outline=""
        )

        self.timer_lbl.config(text=f"{self.track_label} • {fmt_s(TRACK_SECONDS)} • blijf in het gele blok 😅")

    def track_tick(self, ts, dt_ms):
        if (not self.track_active) or (self.track_end_ts is None):
            return

        dt = max(0.001, dt_ms / 1000.0)

        ax = random.uniform(-TRACK_ACCEL_PX_S2, TRACK_ACCEL_PX_S2)
        ay = random.uniform(-TRACK_ACCEL_PX_S2, TRACK_ACCEL_PX_S2)
        self.track_vx += ax * dt
        self.track_vy += ay * dt

        sp = math.hypot(self.track_vx, self.track_vy)
        if sp > TRACK_MAX_SPEED_PX_S:
            scale = TRACK_MAX_SPEED_PX_S / max(1e-6, sp)
            self.track_vx *= scale
            self.track_vy *= scale

        self.track_x += self.track_vx * dt
        self.track_y += self.track_vy * dt

        w = self.WIN_W
        h = self.WIN_H - TOPBAR_H

        pad_x = 80
        pad_y = 80
        if self.track_x < pad_x or self.track_x > w - pad_x:
            self.track_vx *= -0.85
            self.track_x = clamp(self.track_x, pad_x, w - pad_x)
        if self.track_y < pad_y or self.track_y > h - pad_y:
            self.track_vy *= -0.85
            self.track_y = clamp(self.track_y, pad_y, h - pad_y)

        x1 = int(self.track_x - TRACK_SIZE / 2)
        y1 = int(self.track_y - TRACK_SIZE / 2)
        x2 = int(self.track_x + TRACK_SIZE / 2)
        y2 = int(self.track_y + TRACK_SIZE / 2)

        if self.track_target_id is not None:
            self.canvas.coords(self.track_target_id, x1, y1, x2, y2)

        inside = (x1 <= self.mouse_x <= x2 and y1 <= self.mouse_y <= y2)
        if inside:
            self.track_inside_ms += dt_ms

        d = dist((self.mouse_x, self.mouse_y), (self.track_x, self.track_y))
        self.track_dist_samples.append(d)

    def end_track_moving(self, outcome="DONE"):
        end_ts = now()

        if self.track_target_id is not None:
            self.canvas.delete(self.track_target_id)

        total_ms = max(1.0, (end_ts - self.track_start_ts) * 1000.0) if self.track_start_ts else 1.0
        inside_pct = (self.track_inside_ms / total_ms) * 100.0
        mean_dist = avg(self.track_dist_samples) if self.track_dist_samples else 0.0
        max_dist = max(self.track_dist_samples) if self.track_dist_samples else 0.0

        notes = {
            "mode": MODE,
            "inside_pct": round(inside_pct, 3),
            "mean_dist_px": round(mean_dist, 3),
            "max_dist_px": round(max_dist, 3),
            "seconds": round(TRACK_SECONDS, 3),
        }

        self.segments.append({
            "start_ts": self.track_start_ts,
            "end_ts": end_ts,
            "label": self.track_label,
            "outcome": outcome,
            "notes": json.dumps(notes, ensure_ascii=False),
        })

        self.track_active = False
        self.track_start_ts = None
        self.track_end_ts = None
        self.track_target_id = None
        self.timer_lbl.config(text="")

        while len(self.active_targets) < N_ACTIVE_TARGETS and self.hits_done < self.goal_trials:
            self.spawn_target()

    # metrics
    def compute_trial_metrics(self, t, end_ts, end_point_index, outcome="HIT"):
        pts = self.points[t["start_point_index"]:end_point_index]
        if len(pts) < 2:
            pts = self.points[max(0, end_point_index - 2):end_point_index]

        start_xy = t["start_xy"]
        center = t["center"]

        path_len = 0.0
        speeds = []
        stop_time_ms = 0.0
        pause_count = 0

        for i in range(1, len(pts)):
            a = (pts[i - 1][1], pts[i - 1][2])
            b = (pts[i][1], pts[i][2])
            path_len += dist(a, b)

        for p in pts:
            dt_ms = p[5]
            sp = p[6]
            speeds.append(sp)
            if sp < STOP_SPEED_PX_S and dt_ms > 0:
                stop_time_ms += dt_ms
            if dt_ms >= PAUSE_DT_MS:
                pause_count += 1

        max_speed = max(speeds) if speeds else 0.0
        med_speed = median(speeds) if speeds else 0.0

        time_to_peak_ms = 0.0
        if speeds:
            idx = speeds.index(max_speed)
            if 0 <= idx < len(pts):
                time_to_peak_ms = (pts[idx][0] - t["spawn_ts"]) * 1000.0

        straight = dist(start_xy, center)
        efficiency = (straight / path_len) if path_len > 0 else 0.0
        efficiency = min(1.0, max(0.0, efficiency))

        tail_pts = []
        for p in reversed(pts):
            xy = (p[1], p[2])
            if dist(xy, center) <= TAIL_RADIUS_PX:
                tail_pts.append(p)
            else:
                if tail_pts:
                    break
        tail_pts = list(reversed(tail_pts))

        overshoot_px = 0.0
        if tail_pts:
            dists = [dist((p[1], p[2]), center) for p in tail_pts]
            overshoot_px = max(0.0, max(dists) - min(dists)) if dists else 0.0

        tail_wiggles = 0
        if len(tail_pts) >= 4:
            angles = []
            for i in range(1, len(tail_pts)):
                dx = tail_pts[i][1] - tail_pts[i - 1][1]
                dy = tail_pts[i][2] - tail_pts[i - 1][2]
                angles.append(math.atan2(dy, dx))
            for i in range(2, len(angles)):
                a1 = angles[i - 1] - angles[i - 2]
                a2 = angles[i] - angles[i - 1]
                if a1 != 0 and a2 != 0 and ((a1 > 0) != (a2 > 0)):
                    tail_wiggles += 1

        curvature = 0.0
        if len(pts) >= 3:
            turn_sum = 0.0
            for i in range(2, len(pts)):
                x0, y0 = pts[i - 2][1], pts[i - 2][2]
                x1, y1 = pts[i - 1][1], pts[i - 1][2]
                x2, y2 = pts[i][1], pts[i][2]
                v1 = (x1 - x0, y1 - y0)
                v2 = (x2 - x1, y2 - y1)
                turn_sum += angle_between(v1, v2)
            curvature = (turn_sum / path_len) if path_len > 0 else 0.0

        return {
            "trial_id": t["trial_id"],
            "outcome": outcome,
            "label": t["label"],
            "mode": MODE,
            "paired_group": t.get("paired_group") or "",
            "difficulty": round(t["difficulty"], 4),
            "target_size": t["size"],
            "spawn_ts": t["spawn_ts"],
            "end_ts": end_ts,
            "time_to_end_ms": round((end_ts - t["spawn_ts"]) * 1000.0, 3),
            "miss_clicks": t["miss_clicks"],
            "start_x": round(start_xy[0], 2),
            "start_y": round(start_xy[1], 2),
            "center_x": round(center[0], 2),
            "center_y": round(center[1], 2),
            "path_length_px": round(path_len, 3),
            "straight_dist_px": round(straight, 3),
            "efficiency": round(efficiency, 5),
            "overshoot_px": round(overshoot_px, 3),
            "tail_wiggles": tail_wiggles,
            "max_speed_px_s": round(max_speed, 3),
            "median_speed_px_s": round(med_speed, 3),
            "time_to_peak_speed_ms": round(time_to_peak_ms, 3),
            "stop_time_ms": round(stop_time_ms, 3),
            "pause_count": int(pause_count),
            "curvature": round(curvature, 8),
            "points_in_trial": len(pts),
        }

    def build_profile_preview(self):
        profile = {
            "profile_id": "hes_normal_only_preview",
            "created_local": datetime_stamp_local(),
            "resolution": [self.WIN_W, self.WIN_H],
            "sampling_ms": SAMPLE_MS,
            "mode": MODE,
            "goal_trials": self.goal_trials,
            "globals": {},
            "by_scenario": {},
            "segments": {},
        }

        if self.trials:
            med_s = [float(t.get("median_speed_px_s", 0.0)) for t in self.trials]
            vmax = [float(t.get("max_speed_px_s", 0.0)) for t in self.trials]
            stop = [float(t.get("stop_time_ms", 0.0)) for t in self.trials]
            over = [float(t.get("overshoot_px", 0.0)) for t in self.trials]
            pauses = [float(t.get("pause_count", 0.0)) for t in self.trials]
            eff = [float(t.get("efficiency", 0.0)) for t in self.trials]

            profile["globals"] = {
                "median_speed_px_s": stat_pack(med_s),
                "max_speed_px_s": stat_pack(vmax),
                "stop_time_ms": stat_pack(stop),
                "overshoot_px": stat_pack(over),
                "pause_count": stat_pack(pauses),
                "efficiency": stat_pack(eff),
            }

            for lbl, *_rest in SCENARIOS:
                items = [t for t in self.trials if t.get("label") == lbl]
                if not items:
                    continue
                profile["by_scenario"][lbl] = {
                    "time_to_end_ms": stat_pack([float(x.get("time_to_end_ms", 0.0)) for x in items]),
                    "efficiency": stat_pack([float(x.get("efficiency", 0.0)) for x in items]),
                    "overshoot_px": stat_pack([float(x.get("overshoot_px", 0.0)) for x in items]),
                    "tail_wiggles": stat_pack([float(x.get("tail_wiggles", 0.0)) for x in items]),
                }

        # segments summary (track)
        seg_track = []
        for s in self.segments:
            if s.get("label") == self.track_label:
                try:
                    notes = json.loads(s.get("notes", "{}"))
                    seg_track.append(notes)
                except Exception:
                    pass

        if seg_track:
            inside = [float(x.get("inside_pct", 0.0)) for x in seg_track]
            mean_dist = [float(x.get("mean_dist_px", 0.0)) for x in seg_track]
            max_dist = [float(x.get("max_dist_px", 0.0)) for x in seg_track]
            profile["segments"]["TRACK_MOVING"] = {
                "inside_pct": stat_pack(inside),
                "mean_dist_px": stat_pack(mean_dist),
                "max_dist_px": stat_pack(max_dist),
            }

        return profile

    def save_logs(self):
        with open(POINTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts", "x", "y", "buttons", "active_trial_id", "dt_ms", "speed_px_s", "mode"])
            w.writerows(self.points)

        with open(TRIALS_CSV, "w", newline="", encoding="utf-8") as f:
            cols = list(self.trials[0].keys()) if self.trials else []
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for row in self.trials:
                w.writerow(row)

        with open(SEGMENTS_CSV, "w", newline="", encoding="utf-8") as f:
            cols = ["start_ts", "end_ts", "label", "outcome", "notes"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for row in self.segments:
                w.writerow(row)

        # summary
        by = {}
        for t in self.trials:
            by.setdefault((t["label"], t["outcome"]), []).append(t)

        def stat(items, key):
            return avg([float(x.get(key, 0.0)) for x in items]) if items else 0.0

        out = []
        out.append(f"trials={len(self.trials)} goal={self.goal_trials}")
        out.append(f"segments={len(self.segments)}")
        out.append(f"seed={SEED} fixed_seed={USE_FIXED_SEED} fixed_order={USE_FIXED_SCENARIO_ORDER}")
        out.append(f"mode={MODE}")
        out.append("")
        out.append("Per label/outcome (means):")

        labels_order = [s[0] for s in SCENARIOS]
        outcomes_order = ["HIT", "SKIPPED", "DRAG_HIT", "DRAG_MISS"]
        for lbl in labels_order:
            for oc in outcomes_order:
                items = by.get((lbl, oc), [])
                if not items:
                    continue
                out.append(
                    f"{lbl:14} {oc:8} n={len(items):3} "
                    f"t_ms={stat(items,'time_to_end_ms'):8.1f} "
                    f"miss={stat(items,'miss_clicks'):5.2f} "
                    f"eff={stat(items,'efficiency'):6.3f} "
                    f"over={stat(items,'overshoot_px'):6.2f} "
                    f"vmax={stat(items,'max_speed_px_s'):8.1f} "
                    f"stop_ms={stat(items,'stop_time_ms'):8.1f} "
                    f"curv={stat(items,'curvature'):.6f}"
                )

        SUMMARY_TXT.write_text("\n".join(out), encoding="utf-8")

        meta = {
            "created_local": datetime_stamp_local(),
            "run_dir": str(RUN_DIR),
            "seed": SEED,
            "fixed_seed": USE_FIXED_SEED,
            "fixed_order": USE_FIXED_SCENARIO_ORDER,
            "goal_trials": self.goal_trials,
            "sample_ms": SAMPLE_MS,
            "scenarios": [s[0] for s in SCENARIOS],
            "free_roam_seconds": FREE_ROAM_SECONDS,
            "track_seconds": TRACK_SECONDS,
            "resolution": [self.WIN_W, self.WIN_H],
            "topbar_h": TOPBAR_H,
            "mode": MODE,
        }
        safe_write_json(META_JSON, meta)

        profile_preview = self.build_profile_preview()
        safe_write_json(PROFILE_JSON, profile_preview)

        append_runs_index({
            "run_dir": str(RUN_DIR),
            "created_local": datetime_stamp_local(),
            "seed": SEED,
            "fixed_seed": USE_FIXED_SEED,
            "fixed_order": USE_FIXED_SCENARIO_ORDER,
            "goal_trials": self.goal_trials,
            "sample_ms": SAMPLE_MS,
            "trials_logged": len(self.trials),
            "segments_logged": len(self.segments),
        })

        print("Saved logs to:", RUN_DIR.resolve())
        print("Profile preview:", PROFILE_JSON.resolve())


if __name__ == "__main__":
    root = tk.Tk()
    app = MouseLab(root)
    root.mainloop()