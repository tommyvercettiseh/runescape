from __future__ import annotations

import json
import math
import random
import statistics
import threading
import time
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Sequence

from .services import HubPaths, discover_sessions, load_master_profile, load_points, normalize_path

BG = "#08111f"
PANEL = "#101b2d"
PANEL_2 = "#142238"
TEXT = "#f5f7ff"
MUTED = "#91a0b8"
BLUE = "#3677ff"
PURPLE = "#8b4dff"
GREEN = "#40d98b"
YELLOW = "#ffd166"
RED = "#ff4d5f"
BORDER = "#24344f"


@dataclass(frozen=True)
class RunMetrics:
    run_id: int
    source_session: str
    similarity: float
    duration_ms: float
    path_length: float
    straightness: float
    curvature: float
    max_step: float
    acceleration_index: float
    jerk_index: float
    fingerprint: str


@dataclass(frozen=True)
class StressReport:
    schema_version: int
    generated_at: str
    profile_id: str
    profile_version: str
    run_count: int
    source_session_count: int
    seed: int
    elapsed_seconds: float
    overall_score: float
    category_scores: dict[str, float]
    verdict: str
    warnings: list[dict[str, str]]
    averages: dict[str, float]
    ranges: dict[str, dict[str, float]]
    runs: list[RunMetrics]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _path_length(path: Sequence[tuple[float, float]]) -> float:
    return sum(math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(path, path[1:]))


def _straightness(path: Sequence[tuple[float, float]]) -> float:
    if len(path) < 2:
        return 1.0
    direct = math.hypot(path[-1][0] - path[0][0], path[-1][1] - path[0][1])
    length = _path_length(path)
    return 1.0 if length <= 1e-9 else direct / length


def _curvature(path: Sequence[tuple[float, float]]) -> float:
    turns: list[float] = []
    for a, b, c in zip(path, path[1:], path[2:]):
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        n1 = math.hypot(*v1)
        n2 = math.hypot(*v2)
        if n1 <= 1e-9 or n2 <= 1e-9:
            continue
        dot = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
        turns.append(abs(math.acos(dot)))
    return statistics.fmean(turns) if turns else 0.0


def _motion_indices(path: Sequence[tuple[float, float]]) -> tuple[float, float, float]:
    steps = [math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(path, path[1:])]
    if not steps:
        return 0.0, 0.0, 0.0
    acceleration = [b - a for a, b in zip(steps, steps[1:])]
    jerk = [b - a for a, b in zip(acceleration, acceleration[1:])]
    return max(steps), statistics.fmean(abs(v) for v in acceleration) if acceleration else 0.0, statistics.fmean(abs(v) for v in jerk) if jerk else 0.0


def _fingerprint(path: Sequence[tuple[float, float]]) -> str:
    if not path:
        return "empty"
    sample = path[:: max(1, len(path) // 12)][:12]
    return "|".join(f"{round(x, 2):.2f},{round(y, 2):.2f}" for x, y in sample)


def _similarity(left: Sequence[tuple[float, float]], right: Sequence[tuple[float, float]]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    rms = math.sqrt(sum((ax - bx) ** 2 + (ay - by) ** 2 for (ax, ay), (bx, by) in zip(left, right)) / len(left))
    return _clamp(100.0 * (1.0 - rms / math.sqrt(2.0)))


def simulate_variant(reference: Sequence[tuple[float, float]], rng: random.Random, strength: float = 1.0) -> list[tuple[float, float]]:
    if len(reference) < 2:
        return list(reference)
    phase_a = rng.uniform(0.0, math.tau)
    phase_b = rng.uniform(0.0, math.tau)
    amplitude = rng.uniform(0.004, 0.026) * strength
    drift = rng.uniform(-0.010, 0.010) * strength
    output: list[tuple[float, float]] = []
    for index, (x, y) in enumerate(reference):
        t = index / max(1, len(reference) - 1)
        envelope = math.sin(math.pi * t)
        wave_x = math.sin(t * math.tau * rng.uniform(0.75, 1.65) + phase_a)
        wave_y = math.sin(t * math.tau * rng.uniform(1.05, 2.10) + phase_b)
        nx = x + envelope * amplitude * wave_x * 0.55 + drift * envelope
        ny = y + envelope * amplitude * wave_y
        output.append((max(0.0, min(1.0, nx)), max(0.0, min(1.0, ny))))
    output[0] = reference[0]
    output[-1] = reference[-1]
    return output


def analyze_runs(runs: Sequence[RunMetrics], source_count: int, seed: int, elapsed: float, profile: dict[str, Any]) -> StressReport:
    if not runs:
        raise ValueError("No completed simulation runs.")
    similarities = [run.similarity for run in runs]
    durations = [run.duration_ms for run in runs]
    curvatures = [run.curvature for run in runs]
    max_steps = [run.max_step for run in runs]
    unique_ratio = len({run.fingerprint for run in runs}) / len(runs)
    similarity_spread = statistics.pstdev(similarities) if len(similarities) > 1 else 0.0
    duration_cv = statistics.pstdev(durations) / max(1e-9, statistics.fmean(durations)) if len(durations) > 1 else 0.0

    profile_similarity = _clamp(statistics.fmean(similarities))
    natural_variation = _clamp(55.0 + unique_ratio * 35.0 + min(10.0, similarity_spread * 2.0))
    movement_continuity = _clamp(100.0 - max(0.0, statistics.fmean(max_steps) - 0.10) * 350.0)
    timing_diversity = _clamp(duration_cv * 650.0)
    repetition_control = _clamp(unique_ratio * 100.0)
    physical_plausibility = _clamp(100.0 - sum(1 for value in max_steps if value > 0.20) / len(max_steps) * 100.0)
    outlier_control = _clamp(100.0 - sum(1 for value in similarities if value < 70.0 or value > 99.8) / len(similarities) * 100.0)

    categories = {
        "profile_similarity": round(profile_similarity, 1),
        "natural_variation": round(natural_variation, 1),
        "movement_continuity": round(movement_continuity, 1),
        "timing_diversity": round(timing_diversity, 1),
        "repetition_control": round(repetition_control, 1),
        "physical_plausibility": round(physical_plausibility, 1),
        "outlier_control": round(outlier_control, 1),
    }
    weights = {
        "profile_similarity": 0.20,
        "natural_variation": 0.18,
        "movement_continuity": 0.16,
        "timing_diversity": 0.12,
        "repetition_control": 0.14,
        "physical_plausibility": 0.12,
        "outlier_control": 0.08,
    }
    overall = round(sum(categories[key] * weights[key] for key in weights), 1)
    warnings: list[dict[str, str]] = []
    if unique_ratio < 0.90:
        warnings.append({"severity": "high", "message": "Too many repeated path fingerprints across runs."})
    if timing_diversity < 60:
        warnings.append({"severity": "medium", "message": "Simulated duration variation is narrow."})
    if movement_continuity < 75:
        warnings.append({"severity": "high", "message": "Some runs contain abrupt normalized movement steps."})
    if profile_similarity < 75:
        warnings.append({"severity": "medium", "message": "Generated paths drift too far from source recordings."})
    if outlier_control < 80:
        warnings.append({"severity": "medium", "message": "A notable share of runs falls outside the expected similarity range."})
    if not warnings:
        warnings.append({"severity": "info", "message": "No strong repetition or continuity problems detected."})

    verdict = "Strong demo quality" if overall >= 88 else "Good demo quality" if overall >= 78 else "Needs tuning"
    averages = {
        "similarity": round(statistics.fmean(similarities), 3),
        "duration_ms": round(statistics.fmean(durations), 3),
        "path_length": round(statistics.fmean(run.path_length for run in runs), 5),
        "straightness": round(statistics.fmean(run.straightness for run in runs), 5),
        "curvature": round(statistics.fmean(curvatures), 5),
        "max_step": round(statistics.fmean(max_steps), 5),
        "acceleration_index": round(statistics.fmean(run.acceleration_index for run in runs), 5),
        "jerk_index": round(statistics.fmean(run.jerk_index for run in runs), 5),
    }
    ranges = {
        key: {"min": round(min(values), 5), "max": round(max(values), 5)}
        for key, values in {
            "similarity": similarities,
            "duration_ms": durations,
            "curvature": curvatures,
            "max_step": max_steps,
        }.items()
    }
    return StressReport(
        schema_version=1,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        profile_id=str(profile.get("profile_id") or "unknown"),
        profile_version=str(profile.get("profile_version") or "unknown"),
        run_count=len(runs),
        source_session_count=source_count,
        seed=seed,
        elapsed_seconds=round(elapsed, 3),
        overall_score=overall,
        category_scores=categories,
        verdict=verdict,
        warnings=warnings,
        averages=averages,
        ranges=ranges,
        runs=list(runs),
    )


def run_stress_test(paths: HubPaths, run_count: int = 100, seed: int = 42, progress: Callable[[int, int], None] | None = None) -> StressReport:
    if run_count < 10 or run_count > 5000:
        raise ValueError("Run count must be between 10 and 5000.")
    profile = load_master_profile(paths.master_profile)
    if not profile:
        raise FileNotFoundError("Build a master profile before running the Stress Lab.")
    sessions = [session for session in discover_sessions(paths.recordings, paths.state_file) if session.included and session.points_file]
    references: list[tuple[str, list[tuple[float, float]], float]] = []
    for session in sessions:
        normalized = normalize_path(load_points(session.points_file, max_points=3000), count=64)
        if normalized:
            duration_ms = max(100.0, session.duration_seconds * 1000.0)
            references.append((session.session_id, normalized, duration_ms))
    if not references:
        raise ValueError("No included recordings with usable points.csv were found.")

    rng = random.Random(seed)
    started = time.perf_counter()
    runs: list[RunMetrics] = []
    for run_id in range(1, run_count + 1):
        session_id, reference, source_duration = references[rng.randrange(len(references))]
        variant = simulate_variant(reference, rng, strength=rng.uniform(0.75, 1.35))
        duration_ms = source_duration * rng.lognormvariate(0.0, 0.11)
        max_step, acceleration, jerk = _motion_indices(variant)
        runs.append(
            RunMetrics(
                run_id=run_id,
                source_session=session_id,
                similarity=round(_similarity(reference, variant), 3),
                duration_ms=round(duration_ms, 3),
                path_length=round(_path_length(variant), 6),
                straightness=round(_straightness(variant), 6),
                curvature=round(_curvature(variant), 6),
                max_step=round(max_step, 6),
                acceleration_index=round(acceleration, 6),
                jerk_index=round(jerk, 6),
                fingerprint=_fingerprint(variant),
            )
        )
        if progress and (run_id == run_count or run_id % max(1, run_count // 100) == 0):
            progress(run_id, run_count)
    return analyze_runs(runs, len(references), seed, time.perf_counter() - started, profile)


def save_report(paths: HubPaths, report: StressReport) -> Path:
    output_dir = paths.repo_root / "data" / "mouse_profile_hub" / "stress_lab" / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=False)
    payload = asdict(report)
    (output_dir / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    with (output_dir / "runs.jsonl").open("w", encoding="utf-8") as handle:
        for run in report.runs:
            handle.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")
    return output_dir


class StressLabApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.paths = HubPaths.discover()
        self.report: StressReport | None = None
        root.title("Profile Stress Lab")
        root.geometry("1220x760")
        root.minsize(980, 650)
        root.configure(bg=BG)
        self._build_ui()

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT, activebackground=bg, activeforeground=TEXT, relief="flat", cursor="hand2", **kwargs)

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=22, pady=(20, 12))
        tk.Label(header, text="Profile Stress Lab", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(header, text="Batch simulation for profile consistency, variation, continuity and repetition risk.", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=22, pady=(0, 22))
        controls = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, width=300)
        controls.pack(side="left", fill="y", padx=(0, 12))
        controls.pack_propagate(False)
        results = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        results.pack(side="left", fill="both", expand=True)

        tk.Label(controls, text="Simulation settings", bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 12))
        tk.Label(controls, text="Runs", bg=PANEL, fg=MUTED).pack(anchor="w", padx=16)
        self.runs_var = tk.StringVar(value="100")
        tk.Entry(controls, textvariable=self.runs_var, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", padx=16, pady=(4, 10), ipady=7)
        tk.Label(controls, text="Seed", bg=PANEL, fg=MUTED).pack(anchor="w", padx=16)
        self.seed_var = tk.StringVar(value="42")
        tk.Entry(controls, textvariable=self.seed_var, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat").pack(fill="x", padx=16, pady=(4, 14), ipady=7)
        self.start_button = self._button(controls, "Start simulation", self.start, bg=PURPLE, pady=10)
        self.start_button.pack(fill="x", padx=16)
        self.progress = ttk.Progressbar(controls, maximum=100)
        self.progress.pack(fill="x", padx=16, pady=(14, 6))
        self.status = tk.Label(controls, text="Ready", bg=PANEL, fg=MUTED, wraplength=260, justify="left")
        self.status.pack(anchor="w", padx=16)
        self.open_button = self._button(controls, "Open latest results folder", self.open_results, state="disabled", pady=8)
        self.open_button.pack(fill="x", padx=16, pady=(16, 0))

        top = tk.Frame(results, bg=PANEL)
        top.pack(fill="x", padx=18, pady=18)
        self.score_label = tk.Label(top, text="—", bg=PANEL_2, fg=TEXT, font=("Segoe UI", 34, "bold"), width=5, height=2)
        self.score_label.pack(side="left")
        summary = tk.Frame(top, bg=PANEL)
        summary.pack(side="left", fill="x", expand=True, padx=18)
        self.verdict_label = tk.Label(summary, text="Run a simulation", bg=PANEL, fg=TEXT, font=("Segoe UI", 16, "bold"))
        self.verdict_label.pack(anchor="w")
        self.detail_label = tk.Label(summary, text="The report will use your included recordings and current master profile.", bg=PANEL, fg=MUTED, justify="left", wraplength=650)
        self.detail_label.pack(anchor="w", pady=(6, 0))

        self.metrics_tree = ttk.Treeview(results, columns=("metric", "score"), show="headings", height=8)
        self.metrics_tree.heading("metric", text="Category")
        self.metrics_tree.heading("score", text="Score")
        self.metrics_tree.column("metric", width=260)
        self.metrics_tree.column("score", width=100, anchor="center")
        self.metrics_tree.pack(fill="x", padx=18)

        tk.Label(results, text="Warnings and observations", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=18, pady=(18, 6))
        self.warning_list = tk.Listbox(results, bg=PANEL_2, fg=TEXT, selectbackground=BLUE, relief="flat", height=8)
        self.warning_list.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def start(self):
        try:
            run_count = int(self.runs_var.get())
            seed = int(self.seed_var.get())
        except ValueError:
            messagebox.showerror("Stress Lab", "Runs and seed must be whole numbers.")
            return
        self.start_button.config(state="disabled")
        self.open_button.config(state="disabled")
        self.progress["value"] = 0
        self.status.config(text="Running batch simulation...", fg=YELLOW)

        def progress(done: int, total: int):
            self.root.after(0, lambda: self.progress.configure(value=done / total * 100.0))

        def worker():
            try:
                report = run_stress_test(self.paths, run_count, seed, progress)
                folder = save_report(self.paths, report)
                self.root.after(0, lambda: self.finished(report, folder, None))
            except Exception as exc:
                self.root.after(0, lambda: self.finished(None, None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def finished(self, report: StressReport | None, folder: Path | None, error: Exception | None):
        self.start_button.config(state="normal")
        if error:
            self.status.config(text=f"Failed: {error}", fg=RED)
            messagebox.showerror("Stress Lab", str(error))
            return
        assert report is not None and folder is not None
        self.report = report
        self.latest_folder = folder
        self.progress["value"] = 100
        self.status.config(text=f"Completed {report.run_count} runs in {report.elapsed_seconds:.2f}s\nSaved to {folder}", fg=GREEN)
        self.score_label.config(text=f"{report.overall_score:.0f}")
        self.verdict_label.config(text=report.verdict)
        self.detail_label.config(text=f"Profile {report.profile_id} · {report.source_session_count} source sessions · seed {report.seed}")
        for item in self.metrics_tree.get_children():
            self.metrics_tree.delete(item)
        for key, value in report.category_scores.items():
            self.metrics_tree.insert("", "end", values=(key.replace("_", " ").title(), f"{value:.1f}/100"))
        self.warning_list.delete(0, "end")
        for warning in report.warnings:
            self.warning_list.insert("end", f"[{warning['severity'].upper()}] {warning['message']}")
        self.open_button.config(state="normal")

    def open_results(self):
        folder = getattr(self, "latest_folder", None)
        if folder is None:
            return
        import os
        os.startfile(folder) if hasattr(os, "startfile") else None


def main():
    root = tk.Tk()
    StressLabApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
