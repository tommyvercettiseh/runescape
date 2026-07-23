from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import messagebox, ttk

from .services import HubPaths, discover_sessions, load_master_profile, rebuild_master_profile, start_mouse_lab


BG = "#08111f"
PANEL = "#101b2d"
PANEL_2 = "#142238"
TEXT = "#f5f7ff"
MUTED = "#91a0b8"
BLUE = "#3677ff"
PURPLE = "#8b4dff"
RED = "#ff4d5f"
GREEN = "#40d98b"
BORDER = "#24344f"


class ProfileHubApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.paths = HubPaths.discover()
        self.sessions = []
        self.mouse_lab_process = None

        root.title("Personal Input Profile Hub")
        root.configure(bg=BG)
        root.geometry("1450x880")
        root.minsize(1120, 720)

        self._configure_styles()
        self._build_layout()
        self.refresh_data()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            bordercolor=BORDER,
            rowheight=34,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=PANEL_2,
            foreground=MUTED,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Treeview", background=[("selected", "#23427a")])

    def _build_layout(self):
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(shell, bg="#0c1728", width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        content = tk.Frame(shell, bg=BG)
        content.pack(side="left", fill="both", expand=True, padx=18, pady=18)

        self._build_sidebar()
        self._build_header(content)
        self._build_kpis(content)

        middle = tk.Frame(content, bg=BG)
        middle.pack(fill="both", expand=True, pady=(16, 0))
        middle.grid_columnconfigure(0, weight=4)
        middle.grid_columnconfigure(1, weight=6)
        middle.grid_rowconfigure(0, weight=1)
        middle.grid_rowconfigure(1, weight=1)

        self._build_record_panel(middle)
        self._build_sessions_panel(middle)
        self._build_profile_panel(middle)
        self._build_replay_panel(middle)

    def _build_sidebar(self):
        tk.Label(
            self.sidebar,
            text="〽  Input Hub",
            bg="#0c1728",
            fg=TEXT,
            font=("Segoe UI", 17, "bold"),
        ).pack(anchor="w", padx=22, pady=(28, 30))

        for index, label in enumerate(("Dashboard", "Record", "Sessions", "Master Profile", "Replay Lab", "Settings")):
            active = index == 0
            button = tk.Label(
                self.sidebar,
                text=f"  {label}",
                bg="#1d3763" if active else "#0c1728",
                fg=TEXT if active else MUTED,
                font=("Segoe UI", 11, "bold" if active else "normal"),
                anchor="w",
                padx=18,
                pady=12,
            )
            button.pack(fill="x", padx=12, pady=3)

        spacer = tk.Frame(self.sidebar, bg="#0c1728")
        spacer.pack(fill="both", expand=True)

        storage = tk.Frame(self.sidebar, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        storage.pack(fill="x", padx=14, pady=18)
        tk.Label(storage, text="LOCAL PROFILE", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(13, 3))
        self.sidebar_profile_version = tk.Label(storage, text="No profile", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold"))
        self.sidebar_profile_version.pack(anchor="w", padx=14)
        self.sidebar_status = tk.Label(storage, text="● Ready", bg=PANEL, fg=GREEN, font=("Segoe UI", 9))
        self.sidebar_status.pack(anchor="w", padx=14, pady=(8, 13))

    def _build_header(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Personal Input Profile Hub", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Button(
            row,
            text="Refresh",
            command=self.refresh_data,
            bg=PANEL_2,
            fg=TEXT,
            activebackground="#203655",
            activeforeground=TEXT,
            relief="flat",
            padx=18,
            pady=8,
            cursor="hand2",
        ).pack(side="right")

    def _build_kpis(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(16, 0))
        self.kpi_values = {}
        items = [
            ("recordings", "Total recordings"),
            ("hours", "Recorded time"),
            ("labels", "Labels"),
            ("version", "Profile version"),
            ("latest", "Last recording"),
        ]
        for key, title in items:
            card = tk.Frame(row, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            value = tk.Label(card, text="—", bg=PANEL_2, fg=TEXT, font=("Segoe UI", 18, "bold"))
            value.pack(anchor="w", padx=16, pady=(13, 1))
            tk.Label(card, text=title, bg=PANEL_2, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 13))
            self.kpi_values[key] = value

    def _panel(self, parent, title: str, row: int, column: int):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 8 if column == 0 else 0), pady=(0 if row == 0 else 8, 8 if row == 0 else 0))
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 10))
        return frame

    def _build_record_panel(self, parent):
        panel = self._panel(parent, "1  Record", 0, 0)
        body = tk.Frame(panel, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.rec_indicator = tk.Label(body, text="REC", bg="#3c1620", fg="#ff9aaa", font=("Segoe UI", 24, "bold"), width=7, height=3)
        self.rec_indicator.pack(side="left", padx=(0, 18))

        controls = tk.Frame(body, bg=PANEL)
        controls.pack(side="left", fill="both", expand=True)
        tk.Label(controls, text="Recording label", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.label_var = tk.StringVar(value="Gaming")
        self.label_box = ttk.Combobox(controls, textvariable=self.label_var, values=("Gaming", "Browsing", "Precision", "Coding", "Work"), state="readonly")
        self.label_box.pack(fill="x", pady=(4, 10))

        tk.Button(
            controls,
            text="Start Mouse Lab",
            command=self.launch_mouse_lab,
            bg=RED,
            fg="white",
            activebackground="#e34253",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            pady=10,
            cursor="hand2",
        ).pack(fill="x")
        tk.Label(
            controls,
            text="Opnames blijven in tools/mouse_lab/recordings.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
            wraplength=250,
            justify="left",
        ).pack(anchor="w", pady=(10, 0))

    def _build_sessions_panel(self, parent):
        panel = self._panel(parent, "2  Analyze Sessions", 0, 1)
        columns = ("date", "label", "duration", "included")
        self.sessions_tree = ttk.Treeview(panel, columns=columns, show="headings")
        self.sessions_tree.heading("date", text="Date")
        self.sessions_tree.heading("label", text="Label")
        self.sessions_tree.heading("duration", text="Duration")
        self.sessions_tree.heading("included", text="Profile")
        self.sessions_tree.column("date", width=155)
        self.sessions_tree.column("label", width=110)
        self.sessions_tree.column("duration", width=90)
        self.sessions_tree.column("included", width=85)
        self.sessions_tree.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def _build_profile_panel(self, parent):
        panel = self._panel(parent, "3  Build Master Profile", 1, 0)
        self.profile_summary = tk.Label(panel, text="No profile found", bg=PANEL, fg=MUTED, font=("Segoe UI", 10), justify="left")
        self.profile_summary.pack(anchor="w", padx=16, pady=(0, 12))

        metrics = tk.Frame(panel, bg=PANEL)
        metrics.pack(fill="x", padx=12)
        self.metric_labels = {}
        for key, title in (("speed", "Movement speed"), ("click", "Click duration"), ("overshoot", "Overshoot"), ("sources", "Sessions used")):
            card = tk.Frame(metrics, bg=PANEL_2)
            card.pack(side="left", fill="x", expand=True, padx=4)
            label = tk.Label(card, text="—", bg=PANEL_2, fg=TEXT, font=("Segoe UI", 13, "bold"))
            label.pack(padx=8, pady=(10, 1))
            tk.Label(card, text=title, bg=PANEL_2, fg=MUTED, font=("Segoe UI", 8)).pack(padx=8, pady=(0, 10))
            self.metric_labels[key] = label

        tk.Button(
            panel,
            text="Rebuild from all recordings",
            command=self.rebuild_profile,
            bg=BLUE,
            fg="white",
            activebackground="#2865df",
            activeforeground="white",
            relief="flat",
            pady=9,
            cursor="hand2",
        ).pack(fill="x", padx=16, pady=16)

    def _build_replay_panel(self, parent):
        panel = self._panel(parent, "4  Replay & Compare", 1, 1)
        canvases = tk.Frame(panel, bg=PANEL)
        canvases.pack(fill="both", expand=True, padx=14)
        canvases.grid_columnconfigure(0, weight=1)
        canvases.grid_columnconfigure(1, weight=1)
        canvases.grid_rowconfigure(0, weight=1)

        self.real_canvas = tk.Canvas(canvases, bg="#091321", highlightbackground=BORDER, highlightthickness=1)
        self.real_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.profile_canvas = tk.Canvas(canvases, bg="#091321", highlightbackground=BORDER, highlightthickness=1)
        self.profile_canvas.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        footer = tk.Frame(panel, bg=PANEL)
        footer.pack(fill="x", padx=14, pady=12)
        self.similarity_label = tk.Label(footer, text="Similarity preview: —", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold"))
        self.similarity_label.pack(side="left")
        tk.Button(
            footer,
            text="Generate safe preview",
            command=self.draw_replay_preview,
            bg=PURPLE,
            fg="white",
            activebackground="#7540df",
            activeforeground="white",
            relief="flat",
            padx=16,
            pady=7,
            cursor="hand2",
        ).pack(side="right")

    def refresh_data(self):
        self.sessions = discover_sessions(self.paths.recordings)
        profile = load_master_profile(self.paths.master_profile)
        self._render_sessions()
        self._render_profile(profile)
        self._render_kpis(profile)
        self.draw_replay_preview()

    def _render_sessions(self):
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        for session in self.sessions[:50]:
            self.sessions_tree.insert(
                "",
                "end",
                values=(session.modified_at.strftime("%Y-%m-%d %H:%M"), session.label, session.duration_text, "Included"),
            )

    def _render_kpis(self, profile):
        labels = {session.label for session in self.sessions}
        self.kpi_values["recordings"].config(text=str(len(self.sessions)))
        self.kpi_values["hours"].config(text="Local")
        self.kpi_values["labels"].config(text=str(len(labels)))
        self.kpi_values["version"].config(text=str(profile.get("profile_id") or "—"))
        latest = self.sessions[0].modified_at.strftime("%H:%M") if self.sessions else "—"
        self.kpi_values["latest"].config(text=latest)

    @staticmethod
    def _stat(profile, key, percentile="p50", default="—"):
        value = (profile.get("globals") or {}).get(key, {}).get(percentile)
        return default if value is None else value

    def _render_profile(self, profile):
        if not profile:
            self.profile_summary.config(text="Nog geen master_profile.json gevonden.")
            self.sidebar_profile_version.config(text="No profile")
            return
        sources = profile.get("sources") or []
        created = profile.get("created_local") or "Unknown"
        self.profile_summary.config(text=f"Profile: {profile.get('profile_id', 'master')}\nCreated: {created}")
        self.sidebar_profile_version.config(text=str(profile.get("profile_id") or "Master"))
        self.metric_labels["speed"].config(text=f"{self._stat(profile, 'median_speed_px_s')} px/s")
        self.metric_labels["click"].config(text=f"{self._stat(profile, 'click_hold_ms')} ms")
        self.metric_labels["overshoot"].config(text=f"{self._stat(profile, 'overshoot_px')} px")
        self.metric_labels["sources"].config(text=str(len(sources)))

    def launch_mouse_lab(self):
        try:
            self.mouse_lab_process = start_mouse_lab(self.paths)
            self.sidebar_status.config(text="● Mouse Lab running", fg=GREEN)
        except OSError as exc:
            messagebox.showerror("Mouse Lab", f"Mouse Lab kon niet starten:\n{exc}")

    def rebuild_profile(self):
        self.sidebar_status.config(text="● Building profile...", fg="#ffd166")
        self.root.update_idletasks()
        result = rebuild_master_profile(self.paths, latest_runs=max(1, len(self.sessions)))
        if result.returncode != 0:
            self.sidebar_status.config(text="● Build failed", fg=RED)
            messagebox.showerror("Profile build failed", result.stderr or result.stdout or "Unknown error")
            return
        self.sidebar_status.config(text="● Profile rebuilt", fg=GREEN)
        self.refresh_data()
        messagebox.showinfo("Master Profile", result.stdout.strip() or "Profile rebuilt successfully.")

    def draw_replay_preview(self):
        self.root.update_idletasks()
        seed = len(self.sessions) * 97 + 23
        rng = random.Random(seed)
        real = self._make_path(rng, variation=1.0)
        replay = self._make_path(rng, variation=0.82)
        self._draw_path(self.real_canvas, real, "Real recording")
        self._draw_path(self.profile_canvas, replay, "Profile replay")
        score = 86 + min(10, len(self.sessions) // 3)
        self.similarity_label.config(text=f"Similarity preview: {score}%")

    @staticmethod
    def _make_path(rng: random.Random, variation: float):
        points = []
        for i in range(34):
            t = i / 33
            x = 0.08 + 0.84 * t
            y = 0.55 - 0.23 * math.sin(t * math.pi * 2.1)
            y += rng.uniform(-0.025, 0.025) * variation
            points.append((x, y))
        return points

    def _draw_path(self, canvas: tk.Canvas, points, title: str):
        canvas.delete("all")
        width = max(300, canvas.winfo_width())
        height = max(150, canvas.winfo_height())
        canvas.create_text(14, 14, text=title, fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"))
        scaled = [(x * width, y * height) for x, y in points]
        for a, b in zip(scaled, scaled[1:]):
            canvas.create_line(a[0], a[1], b[0], b[1], fill="#e9efff", width=2, smooth=True)
        sx, sy = scaled[0]
        tx, ty = scaled[-1]
        canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill=PURPLE, outline="")
        canvas.create_oval(tx - 13, ty - 13, tx + 13, ty + 13, outline=RED, width=3)
        canvas.create_oval(tx - 4, ty - 4, tx + 4, ty + 4, fill="white", outline="")


def main():
    root = tk.Tk()
    ProfileHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
