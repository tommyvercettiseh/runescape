from __future__ import annotations

import tkinter as tk
from pathlib import Path
import sys

if __package__ is None or __package__ == "":
    ROOT = Path(__file__).resolve().parents[2]  # .../Runescape
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    __package__ = "tools.mouse_lab"
from .config import (
    BASE_DIR,
    BG, TEXT, MUTED, CYAN, YELL,
    BTN_BG, BTN_ACTIVE,
    TOPBAR_H,
    MODE,
    SAMPLE_MS,
    PHASE1_REPS, PHASE2_REPS, PHASE3_BLOCKS,
)
from .export import Exporter
from .recorder import Recorder
from .tasks import TaskRunner
from .features import now, compute_trial
from .profile_fit import ProfileBuilder


class MouseLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Mouse Lab · Hes Signature ✅")
        self.root.configure(bg=BG)

        sw = int(self.root.winfo_screenwidth())
        sh = int(self.root.winfo_screenheight())
        win_w = max(980, int(sw * 0.74))
        win_h = max(720, int(sh * 0.80))
        self.root.geometry(f"{win_w}x{win_h}+40+40")
        self.root.minsize(920, 680)

        self.top = None
        self.canvas = None

        self.exporter = Exporter(BASE_DIR)
        self.session_id = self.exporter.session_id

        self.trials = []

        self._build_ui()

        self.tasks = TaskRunner(self.canvas)

        self.recorder = Recorder(
            self.root,
            self.canvas,
            get_nearest_target=lambda x, y: self.tasks.nearest_active_target(x, y),
            is_inside_target=lambda t, x, y: (t["x1"] <= x <= t["x2"]) and (t["y1"] <= y <= t["y2"]),
            on_left_down_task=self._on_left_down_task,
            on_left_up_task=self._on_left_up_task,
            session_id=self.session_id,
            mode=MODE,
            sample_ms=SAMPLE_MS,
        )
        self.recorder.set_finish_request_callback(self.finish_and_save)

        self._write_meta()

        self.update_ui()
        self.update_timer_loop()

    def _btn(self, parent, text, cmd, bg=BTN_BG, fg=TEXT):
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

        self.btn_start = self._btn(row1, "Start", self.recorder_toggle)
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

    def _phase_instruction(self):
        if self.tasks.phase == 1:
            return ("Ritme: klik BASE → klik target → klik BASE (herhaal)",
                    "Niet overdenken. Gewoon jouw tempo 🙂")
        if self.tasks.phase == 2:
            return ("Ritme: BASE → ver target → BASE → ver target",
                    "Maak lange sweeps, daarna rustig homing 🎯")
        return ("Klik alle kleine blokjes zo snel mogelijk",
                "Eigen volgorde is prima ⚡")

    def update_ui(self):
        self.status_lbl.config(text="RUNNING ✅" if self.recorder.running else "PAUSED ⏸️")
        self.btn_start.config(text="Pause" if self.recorder.running else "Start")

        phase_name = {
            1: "Fase 1 · BASE + return",
            2: "Fase 2 · Lange sweeps",
            3: "Fase 3 · Klik alle kleine blokjes",
        }[self.tasks.phase]

        self.phase_lbl.config(text=phase_name)
        self.progress_lbl.config(text=f"{self.tasks.phase_progress}/{self.tasks.phase_goal[self.tasks.phase]}")

        instr, hint = self._phase_instruction()
        self.instr_lbl.config(text=instr)
        self.hint_lbl.config(text=hint)

    def update_timer_loop(self):
        self.update_ui()
        self.root.after(120, self.update_timer_loop)

    def recorder_toggle(self):
        self.recorder.toggle_run()

    def on_resize(self, e):
        self.tasks.on_resize(int(e.width), int(e.height))

    def force_next_phase(self):
        res = self.tasks.advance_phase(forced=True)
        self.recorder.log_event("phase_change", extra={"to": self.tasks.phase if res != "END" else "END", "forced": True})
        if res == "END":
            self.finish_and_save()

    def _on_left_down_task(self, running: bool, mouse_x: int, mouse_y: int, start_point_index: int):
        out = self.tasks.on_left_down(running=running, mouse_x=mouse_x, mouse_y=mouse_y, start_point_index=start_point_index)

        if out.get("base") and running and self.tasks.phase in (1, 2) and not self.tasks._awaiting_base_click:
            t = self.tasks.nearest_active_target(mouse_x, mouse_y)
            if t:
                self.recorder.log_event("target_spawn", target=t, extra={"label": t["label"], "size": t["size"]})

        return out

    def _on_left_up_task(self, mouse_x: int, mouse_y: int):
        t = self.tasks.on_left_up(mouse_x=mouse_x, mouse_y=mouse_y)

        # ✅ FIX: finalize HIT on release if we were inside a target
        # on_left_up returns a target only when release happens inside it.
        if t and self.recorder.running:
            self.tasks.finalize_hit(t)

        return t

    def _write_meta(self):
        dpi = float(self.root.winfo_fpixels("1i"))
        self.exporter.write_meta(
            mode=MODE,
            sample_ms=SAMPLE_MS,
            root_screen_w=int(self.root.winfo_screenwidth()),
            root_screen_h=int(self.root.winfo_screenheight()),
            window_w=int(self.canvas.winfo_width() or 0),
            window_h=int(self.canvas.winfo_height() or 0),
            dpi=dpi,
            protocol={
                "phase1_reps": PHASE1_REPS,
                "phase2_reps": PHASE2_REPS,
                "phase3_blocks": PHASE3_BLOCKS,
            },
        )

    def finish_and_save(self):
        self.recorder.running = False
        self.recorder.log_event("session_end", extra={"phase": self.tasks.phase, "phase_progress": self.tasks.phase_progress})

        self.exporter.write_points(self.recorder.points)
        self.exporter.write_dict_rows(self.exporter.events_csv, self.recorder.events)
        self.exporter.write_dict_rows(self.exporter.trials_csv, self.trials)

        pb = ProfileBuilder()
        profile = pb.build_profile_preview(
            self.trials,
            mode=MODE,
            canvas_w=int(self.canvas.winfo_width()),
            canvas_h=int(self.canvas.winfo_height()),
            sampling_ms=SAMPLE_MS,
        )
        self.exporter.write_profile_json(profile)
        self.exporter.write_summary(profile, mode=MODE, phase1_reps=PHASE1_REPS, phase2_reps=PHASE2_REPS, phase3_blocks=PHASE3_BLOCKS)

        self.update_ui()

    def on_target_hit(self, target):
        end_ts = now()
        trial = compute_trial(self.recorder.points, target, end_ts, outcome="HIT", mouse_xy_fallback=(self.recorder.mouse_x, self.recorder.mouse_y))
        self.trials.append(trial)
        self.recorder.log_event("target_end", target=target, extra={"outcome": "HIT"})


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    app = MouseLabApp(root)

    orig_finalize = app.tasks.finalize_hit

    def finalize_and_record(t):
        app.on_target_hit(t)
        orig_finalize(t)

    app.tasks.finalize_hit = finalize_and_record

    root.mainloop()


if __name__ == "__main__":
    main()