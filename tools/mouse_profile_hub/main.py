from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .services import (
    HubPaths,
    SessionInfo,
    build_master_profile,
    discover_sessions,
    generate_profile_replay,
    load_master_profile,
    load_points,
    normalize_path,
    set_session_included,
    similarity_score,
    start_mouse_lab,
    stop_process,
)

BG = "#08111f"
PANEL = "#101b2d"
PANEL_2 = "#142238"
TEXT = "#f5f7ff"
MUTED = "#91a0b8"
BLUE = "#3677ff"
PURPLE = "#8b4dff"
RED = "#ff4d5f"
GREEN = "#40d98b"
YELLOW = "#ffd166"
BORDER = "#24344f"


class ProfileHubApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.paths = HubPaths.discover()
        self.sessions: list[SessionInfo] = []
        self.session_by_item: dict[str, SessionInfo] = {}
        self.mouse_lab_process = None
        self.building = False

        root.title("Personal Input Profile Hub")
        root.configure(bg=BG)
        root.geometry("1450x880")
        root.minsize(1120, 720)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._configure_styles()
        self._build_layout()
        self.refresh_data()
        self._poll_process()

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=PANEL, foreground=TEXT, fieldbackground=PANEL, bordercolor=BORDER, rowheight=34, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background=PANEL_2, foreground=MUTED, relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#23427a")])
        style.configure("TCombobox", fieldbackground=PANEL_2, background=PANEL_2, foreground=TEXT)

    def _button(self, parent, text, command, bg=PANEL_2, fg=TEXT, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg, activeforeground=fg, relief="flat", cursor="hand2", **kwargs)

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
        tk.Label(self.sidebar, text="〽  Input Hub", bg="#0c1728", fg=TEXT, font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=22, pady=(28, 30))
        for index, label in enumerate(("Dashboard", "Record", "Sessions", "Master Profile", "Replay Lab", "Settings")):
            tk.Label(self.sidebar, text=f"  {label}", bg="#1d3763" if index == 0 else "#0c1728", fg=TEXT if index == 0 else MUTED, font=("Segoe UI", 11, "bold" if index == 0 else "normal"), anchor="w", padx=18, pady=12).pack(fill="x", padx=12, pady=3)
        tk.Frame(self.sidebar, bg="#0c1728").pack(fill="both", expand=True)
        storage = tk.Frame(self.sidebar, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        storage.pack(fill="x", padx=14, pady=18)
        tk.Label(storage, text="LOCAL PROFILE", bg=PANEL, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(13, 3))
        self.sidebar_profile_version = tk.Label(storage, text="No profile", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold"))
        self.sidebar_profile_version.pack(anchor="w", padx=14)
        self.sidebar_status = tk.Label(storage, text="● Ready", bg=PANEL, fg=GREEN, font=("Segoe UI", 9), wraplength=170, justify="left")
        self.sidebar_status.pack(anchor="w", padx=14, pady=(8, 13))

    def _build_header(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Personal Input Profile Hub", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left")
        self._button(row, "Refresh", self.refresh_data, padx=18, pady=8).pack(side="right")

    def _build_kpis(self, parent):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(16, 0))
        self.kpi_values = {}
        for key, title in (("recordings", "Total recordings"), ("hours", "Recorded time"), ("labels", "Labels"), ("version", "Profile version"), ("latest", "Last recording")):
            card = tk.Frame(row, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 10))
            value = tk.Label(card, text="—", bg=PANEL_2, fg=TEXT, font=("Segoe UI", 18, "bold"))
            value.pack(anchor="w", padx=16, pady=(13, 1))
            tk.Label(card, text=title, bg=PANEL_2, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=16, pady=(0, 13))
            self.kpi_values[key] = value

    def _panel(self, parent, title, row, column):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 8 if column == 0 else 0), pady=(0 if row == 0 else 8, 8 if row == 0 else 0))
        tk.Label(frame, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(14, 10))
        return frame

    def _build_record_panel(self, parent):
        panel = self._panel(parent, "1  Record", 0, 0)
        body = tk.Frame(panel, bg=PANEL)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.rec_indicator = tk.Label(body, text="READY", bg="#18352f", fg="#8ff0c0", font=("Segoe UI", 20, "bold"), width=8, height=3)
        self.rec_indicator.pack(side="left", padx=(0, 18))
        controls = tk.Frame(body, bg=PANEL)
        controls.pack(side="left", fill="both", expand=True)
        tk.Label(controls, text="Recording label", bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        self.label_var = tk.StringVar(value="Gaming")
        self.label_box = ttk.Combobox(controls, textvariable=self.label_var, values=("Gaming", "Browsing", "Precision", "Coding", "Work", "Relaxed", "Fatigued"), state="normal")
        self.label_box.pack(fill="x", pady=(4, 10))
        self.start_button = self._button(controls, "Start Mouse Lab", self.launch_mouse_lab, bg=RED, fg="white", font=("Segoe UI", 10, "bold"), pady=10)
        self.start_button.pack(fill="x")
        self.stop_button = self._button(controls, "Stop Mouse Lab", self.stop_mouse_lab, pady=8, state="disabled")
        self.stop_button.pack(fill="x", pady=(8, 0))
        tk.Label(controls, text="Het gekozen label wordt opgeslagen als Mouse Lab-mode. Output en fouten gaan naar data/mouse_profile_hub/logs.", bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=300, justify="left").pack(anchor="w", pady=(10, 0))

    def _build_sessions_panel(self, parent):
        panel = self._panel(parent, "2  Analyze Sessions", 0, 1)
        columns = ("date", "label", "duration", "events", "quality", "included")
        self.sessions_tree = ttk.Treeview(panel, columns=columns, show="headings", selectmode="browse")
        for column, title, width in (("date", "Date", 145), ("label", "Label", 95), ("duration", "Duration", 80), ("events", "Points", 70), ("quality", "Quality", 70), ("included", "Profile", 75)):
            self.sessions_tree.heading(column, text=title)
            self.sessions_tree.column(column, width=width, anchor="center" if column != "date" else "w")
        self.sessions_tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.sessions_tree.bind("<<TreeviewSelect>>", lambda _event: self.draw_selected_replay())
        self.sessions_tree.bind("<Double-1>", lambda _event: self.toggle_selected_session())
        actions = tk.Frame(panel, bg=PANEL)
        actions.pack(fill="x", padx=14, pady=(0, 12))
        self._button(actions, "Toggle included", self.toggle_selected_session, padx=12, pady=6).pack(side="left")
        tk.Label(actions, text="Dubbelklik werkt ook", bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=10)

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
        self.build_button = self._button(panel, "Rebuild selected profile", self.rebuild_profile, bg=BLUE, fg="white", pady=9)
        self.build_button.pack(fill="x", padx=16, pady=16)

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
        self.similarity_label = tk.Label(footer, text="Select a recording", bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold"))
        self.similarity_label.pack(side="left")
        self._button(footer, "Refresh replay", self.draw_selected_replay, bg=PURPLE, fg="white", padx=16, pady=7).pack(side="right")

    def refresh_data(self):
        self.sessions = discover_sessions(self.paths.recordings, self.paths.state_file)
        profile = load_master_profile(self.paths.master_profile)
        self._render_sessions()
        self._render_profile(profile)
        self._render_kpis(profile)
        if self.sessions and not self.sessions_tree.selection():
            first = self.sessions_tree.get_children()[0] if self.sessions_tree.get_children() else None
            if first:
                self.sessions_tree.selection_set(first)
        self.draw_selected_replay()

    def _render_sessions(self):
        self.session_by_item.clear()
        for item in self.sessions_tree.get_children():
            self.sessions_tree.delete(item)
        for session in self.sessions[:500]:
            item = self.sessions_tree.insert("", "end", values=(session.modified_at.strftime("%Y-%m-%d %H:%M"), session.label, session.duration_text, session.event_count, session.quality, "Yes" if session.included else "No"))
            self.session_by_item[item] = session

    def _render_kpis(self, profile):
        labels = {session.label for session in self.sessions}
        total_hours = sum(session.duration_seconds for session in self.sessions) / 3600.0
        self.kpi_values["recordings"].config(text=str(len(self.sessions)))
        self.kpi_values["hours"].config(text=f"{total_hours:.1f} h")
        self.kpi_values["labels"].config(text=str(len(labels)))
        self.kpi_values["version"].config(text=str(profile.get("profile_version") or "—"))
        latest = self.sessions[0].modified_at.strftime("%d-%m %H:%M") if self.sessions else "—"
        self.kpi_values["latest"].config(text=latest)

    @staticmethod
    def _stat(profile, key, percentile="p50", default="—"):
        value = (profile.get("globals") or {}).get(key, {}).get(percentile)
        return default if value is None else value

    def _render_profile(self, profile):
        if not profile:
            self.profile_summary.config(text="Nog geen masterprofiel. Selecteer recordings en bouw het profiel.")
            self.sidebar_profile_version.config(text="No profile")
            for label in self.metric_labels.values():
                label.config(text="—")
            return
        sources = profile.get("sources") or []
        created = profile.get("created_local") or "Unknown"
        version = profile.get("profile_version") or "0.1.0"
        self.profile_summary.config(text=f"Profile {version} · gebouwd {created}\nRuntime export: {self.paths.runtime_profile.name}")
        self.sidebar_profile_version.config(text=f"v{version}")
        self.metric_labels["speed"].config(text=f"{self._stat(profile, 'median_speed_px_s')} px/s")
        self.metric_labels["click"].config(text=f"{self._stat(profile, 'click_hold_ms')} ms")
        self.metric_labels["overshoot"].config(text=f"{self._stat(profile, 'overshoot_px')} px")
        self.metric_labels["sources"].config(text=str(len(sources)))

    def selected_session(self) -> SessionInfo | None:
        selection = self.sessions_tree.selection()
        return self.session_by_item.get(selection[0]) if selection else None

    def toggle_selected_session(self):
        session = self.selected_session()
        if session is None:
            return
        set_session_included(self.paths.state_file, session.session_id, not session.included)
        self.refresh_data()

    def launch_mouse_lab(self):
        if self.mouse_lab_process is not None and self.mouse_lab_process.poll() is None:
            messagebox.showinfo("Mouse Lab", "Mouse Lab draait al.")
            return
        try:
            self.mouse_lab_process = start_mouse_lab(self.paths, self.label_var.get())
            self.sidebar_status.config(text=f"● Mouse Lab running · {self.label_var.get()}", fg=GREEN)
            self.rec_indicator.config(text="REC", bg="#3c1620", fg="#ff9aaa")
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
        except OSError as exc:
            self.sidebar_status.config(text="● Mouse Lab failed", fg=RED)
            messagebox.showerror("Mouse Lab", f"Mouse Lab kon niet starten:\n{exc}")

    def stop_mouse_lab(self):
        stop_process(self.mouse_lab_process)
        self.mouse_lab_process = None
        self._set_lab_stopped("Mouse Lab stopped")
        self.refresh_data()

    def _set_lab_stopped(self, status="Ready"):
        self.sidebar_status.config(text=f"● {status}", fg=GREEN)
        self.rec_indicator.config(text="READY", bg="#18352f", fg="#8ff0c0")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def _poll_process(self):
        if self.mouse_lab_process is not None and self.mouse_lab_process.poll() is not None:
            code = self.mouse_lab_process.returncode
            self.mouse_lab_process = None
            self._set_lab_stopped("Recording saved" if code == 0 else f"Mouse Lab exited ({code})")
            self.refresh_data()
        self.root.after(1000, self._poll_process)

    def rebuild_profile(self):
        if self.building:
            return
        selected = [session for session in self.sessions if session.included]
        if not selected:
            messagebox.showwarning("Master Profile", "Schakel minimaal één geldige recording in.")
            return
        self.building = True
        self.build_button.config(state="disabled", text="Building profile...")
        self.sidebar_status.config(text=f"● Building from {len(selected)} sessions...", fg=YELLOW)

        def worker():
            try:
                master = build_master_profile(self.paths, selected)
                self.root.after(0, lambda: self._build_finished(master, None))
            except Exception as exc:
                self.root.after(0, lambda: self._build_finished(None, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _build_finished(self, master, error):
        self.building = False
        self.build_button.config(state="normal", text="Rebuild selected profile")
        if error is not None:
            self.sidebar_status.config(text="● Build failed", fg=RED)
            messagebox.showerror("Profile build failed", str(error))
            return
        self.sidebar_status.config(text="● Profile and runtime export rebuilt", fg=GREEN)
        self.refresh_data()
        messagebox.showinfo("Master Profile", f"Profiel gebouwd uit {len(master.get('sources') or [])} sessions.\nRuntimeprofiel: {self.paths.runtime_profile}")

    def draw_selected_replay(self):
        session = self.selected_session()
        profile = load_master_profile(self.paths.master_profile)
        if session is None:
            self._draw_empty(self.real_canvas, "Real recording")
            self._draw_empty(self.profile_canvas, "Profile replay")
            self.similarity_label.config(text="Select a recording")
            return
        points = load_points(session.points_file)
        real = normalize_path(points)
        replay = generate_profile_replay(real, profile)
        if not real:
            self._draw_empty(self.real_canvas, "No usable points.csv")
            self._draw_empty(self.profile_canvas, "Profile replay unavailable")
            self.similarity_label.config(text="Recording contains no readable path")
            return
        self._draw_path(self.real_canvas, real, "Real recording")
        self._draw_path(self.profile_canvas, replay, "Profile replay")
        score = similarity_score(real, replay)
        self.similarity_label.config(text=f"Path similarity: {score:.1f}% · {session.label}" if score is not None else "Similarity unavailable")

    def _draw_empty(self, canvas, text):
        canvas.delete("all")
        canvas.create_text(max(150, canvas.winfo_width() / 2), max(75, canvas.winfo_height() / 2), text=text, fill=MUTED, font=("Segoe UI", 10))

    def _draw_path(self, canvas, points, title):
        canvas.delete("all")
        width = max(300, canvas.winfo_width())
        height = max(150, canvas.winfo_height())
        pad = 28
        canvas.create_text(14, 14, text=title, fill=MUTED, anchor="nw", font=("Segoe UI", 9, "bold"))
        scaled = [(pad + x * (width - pad * 2), pad + y * (height - pad * 2)) for x, y in points]
        if len(scaled) > 1:
            flat = [coordinate for point in scaled for coordinate in point]
            canvas.create_line(*flat, fill="#e9efff", width=2, smooth=True)
        sx, sy = scaled[0]
        tx, ty = scaled[-1]
        canvas.create_oval(sx - 5, sy - 5, sx + 5, sy + 5, fill=PURPLE, outline="")
        canvas.create_oval(tx - 13, ty - 13, tx + 13, ty + 13, outline=RED, width=3)
        canvas.create_oval(tx - 4, ty - 4, tx + 4, ty + 4, fill="white", outline="")

    def on_close(self):
        if self.mouse_lab_process is not None and self.mouse_lab_process.poll() is None:
            if not messagebox.askyesno("Close hub", "Mouse Lab draait nog. Stoppen en afsluiten?"):
                return
            stop_process(self.mouse_lab_process)
        self.root.destroy()


def main():
    root = tk.Tk()
    ProfileHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
