import tkinter as tk
import random
import time
import math
import csv
import json
import platform
from pathlib import Path

# ============================================================
# Mouse Lab: Hes Signature Protocol ✅
# 3 duidelijke fases, minimale mentale load
# Alles loggen voor 100% profiel fit
# ============================================================

BASE_DIR = Path("mouse_profile")

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
BASE_BLUE = "#3a7bff"

TOPBAR_H = 104
SAMPLE_MS = 8
MOVE_EVENT_EVERY_N = 1

MODE = "NORMAL"

STOP_SPEED_PX_S = 30.0
PAUSE_DT_MS = 22.0
TAIL_RADIUS_PX = 40

SIZE_BASE = 54
SIZE_SWEEP = 46
SIZE_SMALL = 22

# Phase sizes
PHASE1_REPS = 30         # BASE -> target -> BASE
PHASE2_REPS = 36         # BASE -> sweep -> BASE
PHASE3_BLOCKS = 16       # click all blocks

# ============================================================
# Helpers
# ============================================================

def now():
    return time.perf_counter()

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

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

def stat_pack(vals):
    return {
        "n": len(vals),
        "p10": round(percentile(vals, 10), 3) if vals else 0.0,
        "p50": round(percentile(vals, 50), 3) if vals else 0.0,
        "p90": round(percentile(vals, 90), 3) if vals else 0.0,
    }

def angle_wrap(a):
    while a <= -math.pi:
        a += 2 * math.pi
    while a > math.pi:
        a -= 2 * math.pi
    return a

def angle_diff(a, b):
    return angle_wrap(a - b)

def datetime_stamp_local():
    return time.strftime("%Y-%m-%d_%H%M%S")

def unique_run_dir(base_dir: Path) -> Path:
    day_dir = base_dir / time.strftime("%Y-%m-%d")
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

# ============================================================
# Point tuple indices
# ============================================================

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

# ============================================================
# App
# ============================================================

class MouseLab:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.root.title("Mouse Lab · Hes Signature ✅")
        self.root.configure(bg=BG)

        sw = int(self.root.winfo_screenwidth())
        sh = int(self.root.winfo_screenheight())
        self.WIN_W = max(980, int(sw * 0.74))
        self.WIN_H = max(720, int(sh * 0.80))
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}+40+40")
        self.root.minsize(920, 680)

        self.CANVAS_W = self.WIN_W
        self.CANVAS_H = self.WIN_H

        self.run_dir = unique_run_dir(BASE_DIR)
        self.session_id = self.run_dir.name

        self.points_csv = self.run_dir / "mouse_points.csv"
        self.events_csv = self.run_dir / "events.csv"
        self.trials_csv = self.run_dir / "trials.csv"
        self.summary_txt = self.run_dir / "summary.txt"
        self.meta_json = self.run_dir / "meta.json"
        self.profile_json = self.run_dir / "profile_preview.json"

        self.running = False
        self.session_start = None

        self.mouse_x = 0
        self.mouse_y = 0
        self.buttons = 0
        self.current_click_id = 0

        self.points = []
        self.events = []
        self.trials = []

        self.last_sample_ts = None
        self.last_sample_xy = None
        self._move_event_counter = 0

        self._last_vx = 0.0
        self._last_vy = 0.0
        self._last_ax = 0.0
        self._last_ay = 0.0
        self._last_heading = 0.0

        self._down_ts = None

        # Phase system
        self.phase = 1
        self.phase_progress = 0
        self.phase_goal = {1: PHASE1_REPS, 2: PHASE2_REPS, 3: PHASE3_BLOCKS}

        self.base_target = None
        self.active_targets = {}   # canvas_id -> dict
        self.current_trial_id = 0

        # Phase orchestration flags
        self._awaiting_base_click = True
        self._awaiting_target_click = False
        self._phase3_remaining = set()

        self._build_ui()
        self._bind_events()
        self._write_meta()

        self._create_base()

        self.update_ui()
        self.update_timer_loop()

    # ============================================================
    # UI
    # ============================================================

    def _btn(self, parent, text, cmd, bg=BTN_BG, fg=BTN_FG):
        return tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg,
            fg=fg,
            activebackground=BTN_ACTIVE,
            activeforeground=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            padx=12,
            pady=6,
            cursor="hand2",
        )

    def _build_ui(self):
        self.top = tk.Frame(self.root, bg=BG, height=TOPBAR_H)
        self.top.pack(fill="x", side="top")
        self.top.pack_propagate(False)

        row1 = tk.Frame(self.top, bg=BG)
        row1.pack(fill="x", side="top", pady=(10, 0), padx=10)

        row2 = tk.Frame(self.top, bg=BG)
        row2.pack(fill="x", side="top", pady=(6, 0), padx=10)

        self.status_lbl = tk.Label(row1, text="PAUSED ⏸️", fg=YELL, bg=BG, font=("Segoe UI", 12, "bold"))
        self.status_lbl.pack(side="left")

        self.phase_lbl = tk.Label(row1, text="", fg=TEXT, bg=BG, font=("Segoe UI", 11, "bold"))
        self.phase_lbl.pack(side="left", padx=(12, 0))

        self.progress_lbl = tk.Label(row1, text="", fg=MUTED, bg=BG, font=("Segoe UI", 10))
        self.progress_lbl.pack(side="left", padx=(12, 0))

        self.btn_start = self._btn(row1, "Start", self.toggle_run)
        self.btn_start.pack(side="right", padx=(6, 0))

        self.btn_finish = self._btn(row1, "Finish & Save", self.finish_and_save, bg="#2a2a2a")
        self.btn_finish.pack(side="right", padx=(6, 0))

        self.btn_next = self._btn(row1, "Next phase", self.force_next_phase, bg="#2a2a2a")
        self.btn_next.pack(side="right", padx=(6, 0))

        self.instr_lbl = tk.Label(row2, text="", fg=YELL, bg=BG, font=("Segoe UI", 11))
        self.instr_lbl.pack(side="left", padx=(6, 0))

        self.hint_lbl = tk.Label(row2, text="", fg=CYAN, bg=BG, font=("Segoe UI", 10))
        self.hint_lbl.pack(side="left", padx=(12, 0))

        self.canvas = tk.Canvas(self.root, bg="#0b0b0b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Configure>", self.on_resize)

    def update_ui(self):
        self.status_lbl.config(text="RUNNING ✅" if self.running else "PAUSED ⏸️")
        self.btn_start.config(text="Pause" if self.running else "Start")

        phase_name = {
            1: "Fase 1 · BASE + return",
            2: "Fase 2 · Lange sweeps",
            3: "Fase 3 · Klik alle kleine blokjes",
        }[self.phase]

        self.phase_lbl.config(text=phase_name)
        self.progress_lbl.config(text=f"{self.phase_progress}/{self.phase_goal[self.phase]}")

        instr, hint = self._phase_instruction()
        self.instr_lbl.config(text=instr)
        self.hint_lbl.config(text=hint)

    def _phase_instruction(self):
        if self.phase == 1:
            return (
                "Ritme: klik BASE → klik target → klik BASE (herhaal)",
                "Niet overdenken. Gewoon jouw tempo 🙂",
            )
        if self.phase == 2:
            return (
                "Ritme: BASE → ver target → BASE → ver target",
                "Maak lange sweeps, daarna rustig homing 🎯",
            )
        return (
            "Klik alle kleine blokjes zo snel mogelijk",
            "Eigen volgorde is prima ⚡",
        )

    def update_timer_loop(self):
        self.update_ui()
        self.root.after(120, self.update_timer_loop)

    # ============================================================
    # Meta + events
    # ============================================================

    def _write_meta(self):
        polling_hz = int(round(1000.0 / SAMPLE_MS))
        meta = {
            "session_id": self.session_id,
            "created_local": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": MODE,
            "sampling_ms": SAMPLE_MS,
            "polling_hz": polling_hz,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "screen_w": int(self.root.winfo_screenwidth()),
            "screen_h": int(self.root.winfo_screenheight()),
            "window_w": int(self.CANVAS_W),
            "window_h": int(self.CANVAS_H),
            "dpi": float(self.root.winfo_fpixels("1i")),
            "protocol": {
                "phase1_reps": PHASE1_REPS,
                "phase2_reps": PHASE2_REPS,
                "phase3_blocks": PHASE3_BLOCKS,
            }
        }
        with open(self.meta_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    def log_event(self, event_type: str, *, button: str = "", target=None, extra=None):
        tstamp = now()
        row = {
            "session_id": self.session_id,
            "t": round(tstamp, 6),
            "x": int(self.mouse_x),
            "y": int(self.mouse_y),
            "event_type": event_type,
            "buttons": int(self.buttons),
            "button": button,
            "click_id": str(self.current_click_id) if self.current_click_id else "",
            "target_id": str(target["trial_id"]) if target else "",
            "label": str(target["label"]) if target else "",
            "phase": int(self.phase),
            "phase_progress": int(self.phase_progress),
            "extra": json.dumps(extra or {}, ensure_ascii=False),
        }
        self.events.append(row)

    # ============================================================
    # Run control
    # ============================================================

    def toggle_run(self):
        if not self.running:
            self.running = True
            if self.session_start is None:
                self.session_start = now()
                self.log_event("session_start", extra={"mode": MODE})
            else:
                self.log_event("session_resume")
            self.last_sample_ts = None
            self.last_sample_xy = None
            self.sample_loop()
        else:
            self.running = False
            self.log_event("session_pause")

    def force_next_phase(self):
        self._advance_phase(forced=True)

    # ============================================================
    # Sampling
    # ============================================================

    def sample_loop(self):
        if not self.running:
            return

        ts = now()

        if self.last_sample_ts is None:
            dt = 0.0
            dt_ms = 0.0
        else:
            dt = ts - self.last_sample_ts
            dt_ms = dt * 1000.0

        # derivatives
        if self.last_sample_xy is None or dt <= 0:
            dx = dy = 0.0
            vx = vy = 0.0
            ax = ay = 0.0
            jerk = 0.0
            heading = self._last_heading
            dheading = 0.0
            curv = 0.0
        else:
            dx = float(self.mouse_x - self.last_sample_xy[0])
            dy = float(self.mouse_y - self.last_sample_xy[1])
            vx = dx / dt
            vy = dy / dt

            ax = (vx - self._last_vx) / dt
            ay = (vy - self._last_vy) / dt

            jx = (ax - self._last_ax) / dt
            jy = (ay - self._last_ay) / dt
            jerk = math.hypot(jx, jy)

            speed_step = math.hypot(vx, vy)
            if speed_step > 1e-9:
                heading = math.atan2(vy, vx)
                dheading = angle_diff(heading, self._last_heading)
                ds = math.hypot(dx, dy)
                curv = abs(dheading) / max(1e-6, ds)
            else:
                heading = self._last_heading
                dheading = 0.0
                curv = 0.0

        speed = math.hypot(vx, vy)
        accel = math.hypot(ax, ay)

        self.last_sample_ts = ts
        self.last_sample_xy = (self.mouse_x, self.mouse_y)
        self._last_vx, self._last_vy = vx, vy
        self._last_ax, self._last_ay = ax, ay
        self._last_heading = heading

        target = self._nearest_active_target()
        if target:
            cx, cy = target["center"]
            dist_t = dist((self.mouse_x, self.mouse_y), (cx, cy))
            inside = 1 if self._inside(target, self.mouse_x, self.mouse_y) else 0
            if inside and target.get("first_enter_ts") is None:
                target["first_enter_ts"] = ts
        else:
            cx = cy = 0.0
            dist_t = 0.0
            inside = 0

        active_trial = target["trial_id"] if target else ""

        self.points.append((
            ts, int(self.mouse_x), int(self.mouse_y), int(self.buttons), active_trial,
            float(dt_ms), float(vx), float(vy), float(speed),
            float(ax), float(ay), float(accel), float(jerk),
            float(heading), float(dheading), float(curv),
            float(dist_t), int(inside),
            int(target["trial_id"]) if target else "",
            str(target["label"]) if target else "",
            float(cx), float(cy),
            int(target["size"]) if target else "",
        ))

        self._move_event_counter += 1
        if (self._move_event_counter % MOVE_EVENT_EVERY_N) == 0:
            self.log_event("move", target=target)

        self.root.after(SAMPLE_MS, self.sample_loop)

    # ============================================================
    # Targets
    # ============================================================

    def on_resize(self, e):
        self.CANVAS_W = int(e.width)
        self.CANVAS_H = int(e.height)
        self._reposition_base()

    def _create_base(self):
        cx, cy = self._base_center()
        s = SIZE_BASE
        x1 = int(cx - s / 2)
        y1 = int(cy - s / 2)
        x2 = x1 + s
        y2 = y1 + s
        cid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=BASE_BLUE, outline="")
        self.base_target = {
            "canvas_id": cid,
            "trial_id": 0,
            "label": "BASE",
            "size": s,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": ((x1 + x2)/2, (y1 + y2)/2),
            "spawn_ts": now(),
            "start_xy": (cx, cy),
            "difficulty": 0.0,
            "miss_clicks": 0,
            "start_point_index": len(self.points),
            "first_enter_ts": None,
            "click_down_ts": None,
            "click_up_ts": None,
        }

    def _reposition_base(self):
        if not self.base_target:
            return
        cx, cy = self._base_center()
        s = self.base_target["size"]
        x1 = int(cx - s / 2)
        y1 = int(cy - s / 2)
        x2 = x1 + s
        y2 = y1 + s
        self.base_target.update({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": ((x1 + x2)/2, (y1 + y2)/2),
        })
        self.canvas.coords(self.base_target["canvas_id"], x1, y1, x2, y2)

    def _base_center(self):
        return (self.CANVAS_W / 2, (self.CANVAS_H - TOPBAR_H) / 2 + TOPBAR_H)

    def _inside(self, t, x, y):
        return (t["x1"] <= x <= t["x2"]) and (t["y1"] <= y <= t["y2"])

    def _nearest_active_target(self):
        if not self.active_targets:
            return None
        m0 = (self.mouse_x, self.mouse_y)
        best = None
        best_d = 1e18
        for _, t in self.active_targets.items():
            d = dist(m0, t["center"])
            if d < best_d:
                best_d = d
                best = t
        return best

    def _next_trial_id(self):
        self.current_trial_id += 1
        return self.current_trial_id

    def _add_target(self, cx, cy, size, label):
        x1 = int(cx - size / 2)
        y1 = int(cy - size / 2)
        x2 = x1 + size
        y2 = y1 + size
        cid = self.canvas.create_rectangle(x1, y1, x2, y2, fill=PINK, outline="")
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        spawn_ts = now()
        trial_id = self._next_trial_id()

        t = {
            "canvas_id": cid,
            "trial_id": trial_id,
            "label": label,
            "size": size,
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "center": center,
            "spawn_ts": spawn_ts,
            "start_xy": (self.mouse_x, self.mouse_y),
            "difficulty": (dist((self.mouse_x, self.mouse_y), center) / max(1, size)),
            "miss_clicks": 0,
            "start_point_index": len(self.points),
            "first_enter_ts": None,
            "click_down_ts": None,
            "click_up_ts": None,
        }
        self.active_targets[cid] = t
        self.log_event("target_spawn", target=t, extra={"label": label, "size": size})
        return t

    # ============================================================
    # Phase logic
    # ============================================================

    def _advance_phase(self, forced=False):
        self._clear_targets()
        self.phase_progress = 0
        self._awaiting_base_click = True
        self._awaiting_target_click = False
        self._phase3_remaining = set()

        if self.phase < 3:
            self.phase += 1
            self.log_event("phase_change", extra={"to": self.phase, "forced": forced})
        else:
            self.log_event("phase_change", extra={"to": "END", "forced": forced})
            self.finish_and_save()
            return

        self.update_ui()

    def _clear_targets(self):
        for cid in list(self.active_targets.keys()):
            try:
                self.canvas.delete(cid)
            except Exception:
                pass
            self.active_targets.pop(cid, None)

    def _spawn_phase_target(self):
        # Phase 1 and 2 spawn single target, phase 3 spawns a set
        if self.phase == 1:
            self._spawn_phase1_target()
        elif self.phase == 2:
            self._spawn_phase2_sweep_target()
        else:
            self._spawn_phase3_blocks()

    def _spawn_phase1_target(self):
        # random medium distance target, within safe margins
        pad = 90
        cx = random.uniform(pad, self.CANVAS_W - pad)
        cy = random.uniform(TOPBAR_H + pad, self.CANVAS_H - pad)
        self._add_target(cx, cy, SIZE_SWEEP, "P1_TARGET")
        self._awaiting_target_click = True

    def _phase2_positions(self):
        # long sweeps: left, right, top, bottom, and corners
        pad = 70
        cx0, cy0 = self._base_center()
        left = (pad, cy0)
        right = (self.CANVAS_W - pad, cy0)
        top = (cx0, TOPBAR_H + pad)
        bottom = (cx0, self.CANVAS_H - pad)
        tl = (pad, TOPBAR_H + pad)
        tr = (self.CANVAS_W - pad, TOPBAR_H + pad)
        bl = (pad, self.CANVAS_H - pad)
        br = (self.CANVAS_W - pad, self.CANVAS_H - pad)
        return [left, right, top, bottom, tl, tr, bl, br]

    def _spawn_phase2_sweep_target(self):
        seq = self._phase2_positions()
        idx = self.phase_progress % len(seq)
        cx, cy = seq[idx]
        self._add_target(cx, cy, SIZE_SWEEP, "P2_SWEEP")
        self._awaiting_target_click = True

    def _spawn_phase3_blocks(self):
        self._clear_targets()
        pad = 70
        cx0, cy0 = self._base_center()

        # 16 blocks around edges (top row, bottom row, left col, right col)
        xs_top = [pad + i * (self.CANVAS_W - 2 * pad) / 5 for i in range(1, 5)]
        xs_bot = xs_top[:]
        ys_left = [TOPBAR_H + pad + i * (self.CANVAS_H - TOPBAR_H - 2 * pad) / 5 for i in range(1, 5)]
        ys_right = ys_left[:]

        positions = []
        for x in xs_top:
            positions.append((x, TOPBAR_H + pad))
        for x in xs_bot:
            positions.append((x, self.CANVAS_H - pad))
        for y in ys_left:
            positions.append((pad, y))
        for y in ys_right:
            positions.append((self.CANVAS_W - pad, y))

        random.shuffle(positions)
        positions = positions[:PHASE3_BLOCKS]

        for i, (cx, cy) in enumerate(positions, start=1):
            t = self._add_target(cx, cy, SIZE_SMALL, "P3_BLOCK")
            self._phase3_remaining.add(t["trial_id"])

        self._awaiting_target_click = True

    # ============================================================
    # Trial metrics
    # ============================================================

    def _compute_trial(self, t, end_ts, outcome):
        pts = self.points[t["start_point_index"]:]
        if len(pts) < 3:
            pts = self.points[max(0, len(self.points) - 3):]

        center = t["center"]
        spawn_ts = t["spawn_ts"]
        end_ms = (end_ts - spawn_ts) * 1000.0

        speeds = [float(p[P_SPEED]) for p in pts]
        accs = [float(p[P_ACCEL]) for p in pts]
        jerks = [float(p[P_JERK]) for p in pts]
        dheads = [float(p[P_DHEADING]) for p in pts]

        max_speed = max(speeds) if speeds else 0.0
        med_speed = median(speeds) if speeds else 0.0

        stop_time_ms = 0.0
        pause_count = 0
        for p in pts:
            dt_ms = float(p[P_DT_MS])
            sp = float(p[P_SPEED])
            if sp < STOP_SPEED_PX_S and dt_ms > 0:
                stop_time_ms += dt_ms
            if dt_ms >= PAUSE_DT_MS:
                pause_count += 1

        enter_ts = t.get("first_enter_ts")
        if enter_ts is None and pts:
            for p in pts:
                if self._inside(t, p[P_X], p[P_Y]):
                    enter_ts = p[P_TS]
                    break

        approach_ms = ((enter_ts - spawn_ts) * 1000.0) if enter_ts is not None else end_ms
        tail_ms = max(0.0, end_ms - approach_ms)

        dwell_in_target_ms = 0.0
        for p in pts:
            if self._inside(t, p[P_X], p[P_Y]):
                dwell_in_target_ms += max(0.0, float(p[P_DT_MS]))

        tail_pts = []
        for p in reversed(pts):
            xy = (p[P_X], p[P_Y])
            if dist(xy, center) <= TAIL_RADIUS_PX:
                tail_pts.append(p)
            else:
                if tail_pts:
                    break
        tail_pts = list(reversed(tail_pts))

        overshoot_px = 0.0
        if tail_pts:
            dists = [dist((p[P_X], p[P_Y]), center) for p in tail_pts]
            overshoot_px = max(0.0, max(dists) - min(dists)) if dists else 0.0

        end_x = float(pts[-1][P_X]) if pts else float(self.mouse_x)
        end_y = float(pts[-1][P_Y]) if pts else float(self.mouse_y)
        dx_end = end_x - float(center[0])
        dy_end = end_y - float(center[1])
        radial_error = math.hypot(dx_end, dy_end)

        total_heading_change = sum(abs(x) for x in dheads) if dheads else 0.0
        curv_vals = [abs(float(p[P_CURV])) for p in pts]
        curv_p50 = percentile(curv_vals, 50) if curv_vals else 0.0
        curv_p90 = percentile(curv_vals, 90) if curv_vals else 0.0

        click_hold_ms = 0.0
        if t.get("click_down_ts") is not None and t.get("click_up_ts") is not None:
            click_hold_ms = max(0.0, (t["click_up_ts"] - t["click_down_ts"]) * 1000.0)

        pre_click_ms = 0.0
        if t.get("click_down_ts") is not None and enter_ts is not None:
            pre_click_ms = max(0.0, (t["click_down_ts"] - enter_ts) * 1000.0)

        return {
            "trial_id": t["trial_id"],
            "phase": int(self.phase),
            "label": t["label"],
            "outcome": outcome,
            "target_size": t["size"],
            "spawn_ts": round(spawn_ts, 6),
            "end_ts": round(end_ts, 6),

            "time_to_end_ms": round(end_ms, 3),
            "approach_time_ms": round(approach_ms, 3),
            "tail_time_ms": round(tail_ms, 3),
            "dwell_in_target_ms": round(dwell_in_target_ms, 3),

            "miss_clicks": int(t["miss_clicks"]),

            "center_x": round(center[0], 2),
            "center_y": round(center[1], 2),
            "end_x": round(end_x, 2),
            "end_y": round(end_y, 2),
            "end_dx": round(dx_end, 3),
            "end_dy": round(dy_end, 3),
            "end_radial_error": round(radial_error, 3),

            "overshoot_px": round(overshoot_px, 3),
            "max_speed_px_s": round(max_speed, 3),
            "median_speed_px_s": round(med_speed, 3),
            "stop_time_ms": round(stop_time_ms, 3),
            "pause_count": int(pause_count),

            "accel_p50": round(percentile(accs, 50), 3) if accs else 0.0,
            "jerk_p50": round(percentile(jerks, 50), 3) if jerks else 0.0,
            "jerk_p90": round(percentile(jerks, 90), 3) if jerks else 0.0,
            "heading_total_change": round(total_heading_change, 6),
            "curv_p50": round(curv_p50, 9),
            "curv_p90": round(curv_p90, 9),

            "pre_click_ms": round(pre_click_ms, 3),
            "click_hold_ms": round(click_hold_ms, 3),
            "points_in_trial": len(pts),
        }

    # ============================================================
    # Input events
    # ============================================================

    def _mouse_in_canvas(self, x_root, y_root):
        x = x_root - self.canvas.winfo_rootx()
        y = y_root - self.canvas.winfo_rooty()
        x = int(clamp(x, 0, self.CANVAS_W))
        y = int(clamp(y, 0, self.CANVAS_H))
        return x, y

    def _bind_events(self):
        self.root.bind("<Motion>", self.on_motion_root)
        self.root.bind("<ButtonPress-1>", self.on_l_down_root)
        self.root.bind("<ButtonRelease-1>", self.on_l_up_root)

        self.root.bind("<KeyPress-space>", lambda e: self.toggle_run())
        self.root.bind("<KeyPress-Escape>", lambda e: self.finish_and_save())

    def on_motion_root(self, e):
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy

    def on_l_down_root(self, e):
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy
        self._handle_left_down()

    def on_l_up_root(self, e):
        cx, cy = self._mouse_in_canvas(e.x_root, e.y_root)
        self.mouse_x, self.mouse_y = cx, cy
        self._handle_left_up()

    def _handle_left_down(self):
        self.buttons = 1
        self.current_click_id += 1

        # detect if click is on BASE
        if self.base_target and self._inside(self.base_target, self.mouse_x, self.mouse_y):
            self.log_event("down", button="left", target=self.base_target)

            # Phase 1 and 2 require base click to start next target
            if self.running and self.phase in (1, 2) and self._awaiting_base_click:
                self._awaiting_base_click = False
                self._spawn_phase_target()
            return

        target = self._nearest_active_target()
        self.log_event("down", button="left", target=target)

        if target and self._inside(target, self.mouse_x, self.mouse_y):
            target["click_down_ts"] = now()

        if not self.running:
            return

        # handle target click
        if target and self._inside(target, self.mouse_x, self.mouse_y):
            self._hit_target(target)
        else:
            # misclick: assign to nearest active target if any
            if target:
                target["miss_clicks"] += 1
                self.canvas.itemconfig(target["canvas_id"], fill=MISS_RED)
                self.root.after(90, lambda cid=target["canvas_id"]: self.canvas.itemconfig(cid, fill=PINK))
                self.log_event("misclick", target=target)
            else:
                self.log_event("misclick")

    def _handle_left_up(self):
        target = self._nearest_active_target()
        hold_ms = ""
        if self._down_ts is not None:
            hold_ms = round((now() - self._down_ts) * 1000.0, 3)
        self.log_event("up", button="left", target=target, extra={"hold_ms": hold_ms})

        if target and self._inside(target, self.mouse_x, self.mouse_y):
            target["click_up_ts"] = now()

        self.buttons = 0

    def _hit_target(self, t):
        cid = t["canvas_id"]
        self.canvas.itemconfig(cid, fill=HIT_GREEN)
        self.root.after(80, lambda: self.canvas.delete(cid))

        end_ts = now()
        trial = self._compute_trial(t, end_ts, outcome="HIT")
        self.trials.append(trial)
        self.log_event("target_end", target=t, extra={"outcome": "HIT"})

        self.active_targets.pop(cid, None)

        # phase bookkeeping
        if self.phase == 1:
            self.phase_progress += 1
            self._awaiting_base_click = True
            self._awaiting_target_click = False
            if self.phase_progress >= self.phase_goal[1]:
                self._advance_phase()
        elif self.phase == 2:
            self.phase_progress += 1
            self._awaiting_base_click = True
            self._awaiting_target_click = False
            if self.phase_progress >= self.phase_goal[2]:
                self._advance_phase()
        else:
            # phase 3: click all blocks
            self.phase_progress += 1
            if t["trial_id"] in self._phase3_remaining:
                self._phase3_remaining.remove(t["trial_id"])
            if self.phase_progress >= self.phase_goal[3] or not self._phase3_remaining:
                self._advance_phase()

        # auto spawn phase3 blocks if needed
        if self.phase == 3 and not self.active_targets:
            self._spawn_phase3_blocks()

    # ============================================================
    # Save
    # ============================================================

    def _build_profile_preview(self):
        profile = {
            "profile_id": "hes_signature_protocol_preview",
            "created_local": datetime_stamp_local(),
            "mode": MODE,
            "resolution": [self.CANVAS_W, self.CANVAS_H],
            "sampling_ms": SAMPLE_MS,
            "globals": {},
            "by_phase": {},
        }

        if not self.trials:
            return profile

        g = self.trials
        profile["globals"] = {
            "time_to_end_ms": stat_pack([float(t["time_to_end_ms"]) for t in g]),
            "approach_time_ms": stat_pack([float(t["approach_time_ms"]) for t in g]),
            "tail_time_ms": stat_pack([float(t["tail_time_ms"]) for t in g]),
            "dwell_in_target_ms": stat_pack([float(t["dwell_in_target_ms"]) for t in g]),
            "overshoot_px": stat_pack([float(t["overshoot_px"]) for t in g]),
            "max_speed_px_s": stat_pack([float(t["max_speed_px_s"]) for t in g]),
            "median_speed_px_s": stat_pack([float(t["median_speed_px_s"]) for t in g]),
            "stop_time_ms": stat_pack([float(t["stop_time_ms"]) for t in g]),
            "miss_clicks": stat_pack([float(t["miss_clicks"]) for t in g]),
            "end_dx": stat_pack([float(t["end_dx"]) for t in g]),
            "end_dy": stat_pack([float(t["end_dy"]) for t in g]),
            "end_radial_error": stat_pack([float(t["end_radial_error"]) for t in g]),
            "jerk_p50": stat_pack([float(t["jerk_p50"]) for t in g]),
            "jerk_p90": stat_pack([float(t["jerk_p90"]) for t in g]),
            "curv_p90": stat_pack([float(t["curv_p90"]) for t in g]),
            "pre_click_ms": stat_pack([float(t["pre_click_ms"]) for t in g]),
            "click_hold_ms": stat_pack([float(t["click_hold_ms"]) for t in g]),
        }

        for ph in (1, 2, 3):
            items = [t for t in self.trials if int(t["phase"]) == ph]
            if not items:
                continue
            profile["by_phase"][str(ph)] = {
                "n": len(items),
                "time_to_end_ms": stat_pack([float(t["time_to_end_ms"]) for t in items]),
                "overshoot_px": stat_pack([float(t["overshoot_px"]) for t in items]),
                "max_speed_px_s": stat_pack([float(t["max_speed_px_s"]) for t in items]),
                "median_speed_px_s": stat_pack([float(t["median_speed_px_s"]) for t in items]),
                "end_radial_error": stat_pack([float(t["end_radial_error"]) for t in items]),
                "jerk_p90": stat_pack([float(t["jerk_p90"]) for t in items]),
            }

        return profile

    def _write_summary(self, profile):
        lines = []
        lines.append("Mouse Lab · Hes Signature Protocol Summary")
        lines.append(f"session_id: {self.session_id}")
        lines.append(f"mode: {MODE}")
        lines.append(f"phase1_reps: {PHASE1_REPS}")
        lines.append(f"phase2_reps: {PHASE2_REPS}")
        lines.append(f"phase3_blocks: {PHASE3_BLOCKS}")
        lines.append("")
        lines.append("Globals (p10/p50/p90):")
        for k, v in profile.get("globals", {}).items():
            lines.append(f"  {k}: n={v.get('n')} p10={v.get('p10')} p50={v.get('p50')} p90={v.get('p90')}")
        lines.append("")
        lines.append("By phase:")
        for ph, blk in profile.get("by_phase", {}).items():
            lines.append(f"  phase {ph} (n={blk.get('n')}):")
            for k, v in blk.items():
                if k == "n":
                    continue
                lines.append(f"    {k}: n={v.get('n')} p10={v.get('p10')} p50={v.get('p50')} p90={v.get('p90')}")

        with open(self.summary_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def finish_and_save(self):
        # flush current state
        self.running = False
        self.log_event("session_end", extra={"phase": self.phase, "phase_progress": self.phase_progress})

        # points
        with open(self.points_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "ts","x","y","buttons","active_trial_id","dt_ms",
                "vx","vy","speed_px_s","ax","ay","accel_px_s2","jerk_px_s3",
                "heading_rad","dheading_rad","curv","dist_to_target","inside_target",
                "target_trial_id","label","target_cx","target_cy","target_size"
            ])
            w.writerows(self.points)

        # events
        if self.events:
            cols = list(self.events[0].keys())
            with open(self.events_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(self.events)

        # trials
        if self.trials:
            cols = list(self.trials[0].keys())
            with open(self.trials_csv, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=cols)
                w.writeheader()
                w.writerows(self.trials)

        profile = self._build_profile_preview()
        with open(self.profile_json, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

        self._write_summary(profile)
        self.update_ui()


if __name__ == "__main__":
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = MouseLab(root)
    root.mainloop()