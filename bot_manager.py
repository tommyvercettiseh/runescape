from __future__ import annotations

import os
import sys
import json
import time
import random
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from pynput import mouse as _pynput_mouse
    from pynput import keyboard as _pynput_keyboard
except Exception:
    _pynput_mouse = None
    _pynput_keyboard = None

try:
    from telemetry import update_state
except Exception:
    update_state = None

try:
    from telemetry import battery_tracker as _battery_tracker
except Exception:
    _battery_tracker = None


# =========================
# PATHS
# =========================

PROJECT_ROOT = Path(r"C:\Users\Hesse\Desktop\Runescape")

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RUNNER_PATH = PROJECT_ROOT / "runner.py"
OVERLAY_LAUNCHER = PROJECT_ROOT / "tools" / "overlay_launcher.py"
CONFIG_FILE = PROJECT_ROOT / "botmanager_config.json"
BOT_IDS = [1, 2, 3, 4]


# =========================
# HELPERS
# =========================
def load_json(path: Path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        pass
    return fallback


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def list_scripts_map() -> dict[str, str]:
    if not SCRIPTS_DIR.exists():
        return {}
    mapping: dict[str, str] = {}
    for p in SCRIPTS_DIR.rglob("*.py"):
        if p.name.startswith("_"):
            continue
        if p.name == "__init__.py":
            continue
        mapping[p.name] = str(p.resolve())
    return dict(sorted(mapping.items(), key=lambda kv: kv[0].lower()))


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _key_to_str(k) -> str:
    try:
        return k.char  # type: ignore[attr-defined]
    except Exception:
        return str(k).replace("Key.", "")


class BotInputRecorder:
    def __init__(self, bot_id: int, out_dir: Path, log_fn):
        self.bot_id = bot_id
        self.out_dir = out_dir
        self.log = log_fn

        self.running = False
        self.t0 = 0.0
        self.events: list[dict] = []
        self._last_t: float | None = None
        self._key_down: dict[str, float] = {}
        self._lock = threading.Lock()
        self._listeners_started = False

        if _pynput_mouse is not None and _pynput_keyboard is not None:
            self._mouse_listener = _pynput_mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll,
            )
            self._kb_listener = _pynput_keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
        else:
            self._mouse_listener = None
            self._kb_listener = None

    def _available(self) -> bool:
        return _pynput_mouse is not None and _pynput_keyboard is not None

    def start(self) -> bool:
        if not self._available():
            self.log("❌ Recorder: pynput ontbreekt, kan geen input loggen")
            return False
        if not self._listeners_started:
            self._listeners_started = True
            if self._mouse_listener:
                self._mouse_listener.start()
            if self._kb_listener:
                self._kb_listener.start()
        self.running = True
        self.t0 = time.perf_counter()
        with self._lock:
            self.events.clear()
            self._last_t = None
            self._key_down.clear()
        return True

    def stop_and_save(self, reason: str = "") -> Path | None:
        if not self.running:
            return None

        self.running = False
        with self._lock:
            duration = self.events[-1]["t"] if self.events else 0.0
            events_copy = list(self.events)

        session = {
            "created": _now_stamp(),
            "bot_id": self.bot_id,
            "duration_sec": round(float(duration), 6),
            "events": len(events_copy),
            "reason": reason,
            "source": "bot_manager",
            "data": events_copy,
        }

        self.out_dir.mkdir(parents=True, exist_ok=True)
        out = self.out_dir / f"input_log_bot{self.bot_id}_{_today_stamp()}.json"

        existing = load_json(out, None)
        if isinstance(existing, dict) and "sessions" in existing:
            payload = existing
            if payload.get("bot_id") != self.bot_id:
                payload["bot_id"] = self.bot_id
            payload.setdefault("date", _today_stamp())
            payload.setdefault("sessions", [])
            payload["sessions"].append(session)
        else:
            payload = {
                "bot_id": self.bot_id,
                "date": _today_stamp(),
                "sessions": [session],
            }

        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return out

    def _t(self) -> float:
        return time.perf_counter() - self.t0

    def _push(self, e: dict) -> None:
        if not self.running:
            return
        with self._lock:
            if self._last_t is None:
                e["dt"] = 0.0
            else:
                e["dt"] = round(e["t"] - self._last_t, 6)
            self._last_t = e["t"]
            self.events.append(e)

    # -------------------------
    # MOUSE
    # -------------------------
    def _on_move(self, x: int, y: int) -> None:
        self._push({"t": self._t(), "type": "mouse_move", "x": int(x), "y": int(y)})

    def _on_click(self, x: int, y: int, btn, pressed: bool) -> None:
        b = "right" if btn == _pynput_mouse.Button.right else "left"
        self._push(
            {
                "t": self._t(),
                "type": "mouse_click",
                "x": int(x),
                "y": int(y),
                "button": b,
                "pressed": bool(pressed),
            }
        )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        dx = int(dx)
        dy = int(dy)
        if dx == 0 and dy == 0:
            return
        self._push(
            {
                "t": self._t(),
                "type": "mouse_scroll",
                "x": int(x),
                "y": int(y),
                "dx": dx,
                "dy": dy,
            }
        )

    # -------------------------
    # KEYBOARD
    # -------------------------
    def _on_press(self, k) -> None:
        key = _key_to_str(k)
        now = self._t()
        self._key_down[key] = now
        self._push({"t": now, "type": "key_down", "key": key})

    def _on_release(self, k) -> None:
        key = _key_to_str(k)
        now = self._t()
        started = self._key_down.pop(key, None)
        dur = round(now - started, 6) if started is not None else None
        self._push(
            {
                "t": now,
                "type": "key_up",
                "key": key,
                "held_sec": dur,
            }
        )


# =========================
# GUI
# =========================
class BotManagerGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("🧰 Script Manager (loop)")
        self.geometry("820x660")  # kleiner overall
        self.configure(bg="#181A1B")
        self.resizable(False, False)

        # iets kleinere fonts
        self.font_title = ("Segoe UI Black", 16, "bold")
        self.font_sub = ("Segoe UI Semibold", 10)
        self.font_bot = ("Segoe UI Semibold", 10)
        self.font_status = ("Consolas", 9)
        self.font_button = ("Segoe UI Black", 11)

        self.main_thread = threading.current_thread()

        self.config = load_json(CONFIG_FILE, {})
        self.scripts_map = list_scripts_map()
        self.scripts = list(self.scripts_map.keys())

        self.processes: dict[int, subprocess.Popen] = {}
        self.input_recorders: dict[int, BotInputRecorder] = {}

        self.overlay_proc: subprocess.Popen | None = None
        self.carousel_thread: threading.Thread | None = None
        self.carousel_stop = threading.Event()
        self.carousel_running = False

        self.bot_script_var: dict[int, tk.StringVar] = {}
        self.bot_active_var: dict[int, tk.BooleanVar] = {}

        self.bot_frame: dict[int, tk.Frame] = {}
        self.bot_status_lbl: dict[int, tk.Label] = {}

        self.bot_dd_script: dict[int, ttk.Combobox] = {}

        self.bot_active_lbl_text: dict[int, tk.StringVar] = {}
        self.bot_active_lbl_widget: dict[int, tk.Label] = {}

        self.btn_overlay: tk.Button | None = None
        self.btn_play_top: tk.Button | None = None
        self.btn_start_loop: tk.Button | None = None
        self.btn_stop_all: tk.Button | None = None

        # Loop mode: 1 = 1 ronde, 2 = oneindig
        self.loop_mode_var = tk.IntVar()
        self.delay_var = tk.IntVar()

        # HOTKEY STATE
        self.is_paused = False

        self._build_ui()
        self._bind_hotkeys()

    # =========================
    # UI safe call
    # =========================
    def _ui(self, fn):
        if threading.current_thread() is self.main_thread:
            fn()
        else:
            self.after(0, fn)

    def log(self, msg: str):
        def _do():
            self.status_box.config(state="normal")
            self.status_box.insert("end", msg + "\n")
            self.status_box.see("end")
            self.status_box.config(state="disabled")
        self._ui(_do)

    # =========================
    # HOTKEYS
    # F8 pause/resume
    # F9 play/start
    # ESC stop + close
    # =========================
    def _bind_hotkeys(self):
        self.bind_all("<F8>", lambda _e: self.toggle_pause())
        self.bind_all("<F9>", lambda _e: self.play_carousel())
        self.bind_all("<Escape>", lambda _e: self.stop_and_exit())
        self.protocol("WM_DELETE_WINDOW", self.stop_and_exit)

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.log("⏸️ PAUSED (F8 om verder te gaan)")
        else:
            self.log("▶️ RESUMED")
        self._set_loop_ui(self.carousel_running)

    def stop_and_exit(self):
        self.log("🧨 ESC: stop alles + sluiten")
        try:
            self.stop_all()
        finally:
            try:
                self.stop_overlay()
            except Exception:
                pass
            self.after(50, self.destroy)

    # =========================
    # BUILD UI
    # =========================
    def _build_ui(self):
        top = tk.Frame(self, bg="#191b17")
        top.pack(fill="x", pady=6)

        tk.Label(
            top,
            text="💎 Manager",
            font=self.font_title,
            fg="#5fffa1",
            bg="#191b17",
            padx=10,
            pady=6,
        ).pack(side="left")

        self.btn_play_top = tk.Button(
            top,
            text="▶️ Play (F9)",
            font=("Segoe UI", 9, "bold"),
            command=self.play_carousel,
            bg="#16b870",
            fg="#fff",
            activebackground="#29db92",
            relief="groove",
            width=12,
        )
        self.btn_play_top.pack(side="right", padx=8)

        self.btn_overlay = tk.Button(
            top,
            text="🟪 Start overlay",
            font=("Segoe UI", 9, "bold"),
            command=self.toggle_overlay,
            bg="#7c3aed",
            fg="#fff",
            activebackground="#8f5bff",
            relief="groove",
        )
        self.btn_overlay.pack(side="right", padx=8)

        tk.Button(
            top,
            text="🔄 Refresh",
            font=("Segoe UI", 9, "bold"),
            command=self.refresh_all,
            bg="#2c6cff",
            fg="#fff",
            activebackground="#4d86ff",
            relief="groove",
        ).pack(side="right", padx=8)

        info = tk.Frame(self, bg="#181A1B")
        info.pack(fill="x", padx=10)

        tk.Label(info, text=f"Scripts: {SCRIPTS_DIR}", font=self.font_sub, fg="#abffe1", bg="#181A1B").pack(anchor="w")
        tk.Label(info, text=f"Runner: {RUNNER_PATH}", font=self.font_sub, fg="#abffe1", bg="#181A1B").pack(anchor="w")

        bots = tk.Frame(self, bg="#1f2325", bd=2, relief="ridge")
        bots.pack(pady=8, padx=10, fill="x")

        bots.grid_columnconfigure(0, weight=1, uniform="botcol")
        bots.grid_columnconfigure(1, weight=1, uniform="botcol")

        pos = {1: (0, 0), 2: (0, 1), 3: (1, 0), 4: (1, 1)}

        for bot_id in BOT_IDS:
            r, c = pos[bot_id]

            # kleinere tiles: minder padding, compact layout
            tile = tk.Frame(bots, bg="#232b19", highlightthickness=3)
            tile.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            tile.grid_columnconfigure(0, weight=1)
            self.bot_frame[bot_id] = tile

            header = tk.Frame(tile, bg="#232b19")
            header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
            header.grid_columnconfigure(0, weight=1)

            tk.Label(header, text=f"Bot {bot_id}", font=self.font_bot, fg="#e2eede", bg="#232b19").grid(row=0, column=0, sticky="w")

            script_var = tk.StringVar()
            default_script = self.config.get(f"script_{bot_id}", "")
            if default_script not in self.scripts:
                default_script = self.scripts[0] if self.scripts else ""
            script_var.set(default_script)
            self.bot_script_var[bot_id] = script_var

            dd_script = ttk.Combobox(
                tile,
                textvariable=script_var,
                values=self.scripts,
                width=34,  # smaller
                state="readonly",
                font=("Segoe UI", 9),
            )
            dd_script.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
            dd_script.bind("<<ComboboxSelected>>", lambda _e: self.save_config())
            self.bot_dd_script[bot_id] = dd_script

            footer = tk.Frame(tile, bg="#232b19")
            footer.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
            footer.grid_columnconfigure(2, weight=1)

            active = tk.BooleanVar(value=bool(self.config.get(f"active_{bot_id}", True)))
            self.bot_active_var[bot_id] = active

            cb = tk.Checkbutton(
                footer,
                variable=active,
                bg="#232b19",
                selectcolor="#0d3222",
                activebackground="#232b19",
                command=lambda b=bot_id: self._on_active_toggle(b),
            )
            cb.grid(row=0, column=0, sticky="w", padx=(0, 6))

            active_text = tk.StringVar()
            lbl_active = tk.Label(footer, textvariable=active_text, bg="#232b19", font=("Segoe UI", 9, "bold"))
            lbl_active.grid(row=0, column=1, sticky="w")
            self.bot_active_lbl_text[bot_id] = active_text
            self.bot_active_lbl_widget[bot_id] = lbl_active

            st = tk.Label(
                footer,
                text="IDLE",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=2,
                bg="#2a2a2b",
                fg="#a2ffb8",
                relief="flat",
            )
            st.grid(row=0, column=2, sticky="e", padx=(0, 6))
            self.bot_status_lbl[bot_id] = st

        runtime = tk.Frame(self, bg="#1b1d1e", bd=2, relief="ridge")
        runtime.pack(padx=10, pady=(6, 0), fill="x")

        tk.Label(runtime, text="⏱️ Max runtime (loop)", bg="#1b1d1e", fg="#abffe1", font=self.font_sub)\
            .grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 4))

        self.scale_hours = tk.Scale(
            runtime, from_=0, to=24, orient="horizontal",
            bg="#1b1d1e", fg="#d2ffe6", troughcolor="#0f1213",
            highlightthickness=0, length=220, command=self._update_runtime
        )
        self.scale_hours.set(int(self.config.get("runtime_hours", 0)))
        self.scale_hours.grid(row=1, column=1, sticky="w", padx=6, pady=6)

        self.scale_minutes = tk.Scale(
            runtime, from_=0, to=59, orient="horizontal",
            bg="#1b1d1e", fg="#d2ffe6", troughcolor="#0f1213",
            highlightthickness=0, length=220, command=self._update_runtime
        )
        self.scale_minutes.set(int(self.config.get("runtime_minutes", 0)))
        self.scale_minutes.grid(row=2, column=1, sticky="w", padx=6, pady=(0, 8))

        tk.Label(runtime, text="Uren", bg="#1b1d1e", fg="#d2ffe6").grid(row=1, column=0, sticky="w", padx=10)
        tk.Label(runtime, text="Minuten", bg="#1b1d1e", fg="#d2ffe6").grid(row=2, column=0, sticky="w", padx=10)

        self.runtime_label = tk.Label(runtime, text="", bg="#1b1d1e", fg="#b3ffd4", font=("Segoe UI", 9, "bold"))
        self.runtime_label.grid(row=1, column=2, rowspan=2, sticky="w", padx=10)
        self._update_runtime()

        try:
            delay_seconds = int(self.config.get("delay_seconds", 0))
        except Exception:
            delay_seconds = 0
        self.delay_var.set(delay_seconds)

        tk.Label(runtime, text="Delay (sec)", bg="#1b1d1e", fg="#d2ffe6").grid(row=3, column=0, sticky="w", padx=10)
        delay_spin = tk.Spinbox(
            runtime,
            from_=0,
            to=3600,
            width=6,
            textvariable=self.delay_var,
            command=self.save_config,
            bg="#0f1213",
            fg="#d2ffe6",
            buttonbackground="#0f1213",
            highlightthickness=0,
        )
        delay_spin.grid(row=3, column=1, sticky="w", padx=6, pady=(0, 8))
        delay_spin.bind("<FocusOut>", lambda _e: self.save_config())
        delay_spin.bind("<Return>", lambda _e: self.save_config())

        mode = tk.Frame(self, bg="#1b1d1e", bd=2, relief="ridge")
        mode.pack(padx=10, pady=(8, 0), fill="x")

        tk.Label(mode, text="🔁 Loop mode", bg="#1b1d1e", fg="#abffe1", font=self.font_sub)\
            .pack(side="left", padx=10, pady=8)

        saved_mode = int(self.config.get("loop_mode", 2))
        if saved_mode not in (1, 2):
            saved_mode = 2
        self.loop_mode_var.set(saved_mode)

        tk.Radiobutton(
            mode, text="1 ronde", value=1, variable=self.loop_mode_var,
            bg="#1b1d1e", fg="#d2ffe6", selectcolor="#0f1213",
            activebackground="#1b1d1e", activeforeground="#d2ffe6",
            command=self.save_config
        ).pack(side="left", padx=10)

        tk.Radiobutton(
            mode, text="Oneindig", value=2, variable=self.loop_mode_var,
            bg="#1b1d1e", fg="#d2ffe6", selectcolor="#0f1213",
            activebackground="#1b1d1e", activeforeground="#d2ffe6",
            command=self.save_config
        ).pack(side="left", padx=10)

        log_frame = tk.Frame(self, bg="#141716")
        log_frame.pack(padx=10, pady=(10, 6), fill="both", expand=True)

        self.status_box = tk.Text(
            log_frame,
            height=9,
            width=104,
            bg="#141716",
            fg="#bbffe0",
            font=self.font_status,
            borderwidth=2,
            relief="sunken",
        )
        self.status_box.pack(side="left", fill="both", expand=True)
        self.status_box.insert("end", "🤖 [Console] logs komen hier...\n")
        self.status_box.config(state="disabled")

        sb = tk.Scrollbar(log_frame, command=self.status_box.yview, bg="#191b17")
        sb.pack(side="right", fill="y")
        self.status_box["yscrollcommand"] = sb.set

        btns = tk.Frame(self, bg="#181A1B")
        btns.pack(pady=8)

        self.btn_start_loop = tk.Button(
            btns, text="▶️ Start loop (F9)", font=self.font_button,
            command=self.play_carousel, bg="#16b870", fg="#fff",
            width=22, activebackground="#29db92", relief="groove",
        )
        self.btn_start_loop.pack(side="left", padx=8)

        self.btn_stop_all = tk.Button(
            btns, text="⛔ Stop (ESC)", font=self.font_button,
            command=self.stop_all, bg="#e34d60", fg="#fff",
            width=12, activebackground="#ff6b7c", relief="groove",
        )
        self.btn_stop_all.pack(side="left", padx=8)

        self.save_config()
        self._sync_overlay_button()

        for bot_id in BOT_IDS:
            self.set_status(bot_id, "idle")
            self._apply_bot_controls(bot_id)

        self.log(f"🧭 SCRIPTS_DIR exists={SCRIPTS_DIR.exists()} scripts={len(self.scripts)}")

    # =========================
    # CONFIG
    # =========================
    def save_config(self):
        for bot_id in BOT_IDS:
            self.config[f"active_{bot_id}"] = bool(self.bot_active_var[bot_id].get())
            self.config[f"script_{bot_id}"] = self.bot_script_var[bot_id].get()

        self.config["runtime_hours"] = int(self.scale_hours.get())
        self.config["runtime_minutes"] = int(self.scale_minutes.get())
        self.config["loop_mode"] = int(self.loop_mode_var.get())
        self.config["delay_seconds"] = self._delay_seconds()

        save_json(CONFIG_FILE, self.config)

    def refresh_all(self):
        self.scripts_map = list_scripts_map()
        self.scripts = list(self.scripts_map.keys())

        for bot_id in BOT_IDS:
            self.bot_dd_script[bot_id]["values"] = self.scripts
            if self.bot_script_var[bot_id].get() not in self.scripts and self.scripts:
                self.bot_script_var[bot_id].set(self.scripts[0])

        self.save_config()
        self.log(f"🔄 Refresh klaar scripts={len(self.scripts)}")

    def _update_runtime(self, *_):
        h = int(self.scale_hours.get())
        m = int(self.scale_minutes.get())
        total = h * 60 + m
        self.runtime_label.config(text=("Onbeperkt" if total == 0 else f"{h}u {m}m  totaal {total} min"))
        self.save_config()

    def _max_runtime_seconds(self) -> int:
        h = int(self.scale_hours.get())
        m = int(self.scale_minutes.get())
        return h * 3600 + m * 60

    def _delay_seconds(self) -> int:
        try:
            value = int(self.delay_var.get())
        except Exception:
            value = 0
        if value < 0:
            value = 0
        if value > 3600:
            value = 3600
        try:
            self.delay_var.set(value)
        except Exception:
            pass
        return value

    def _has_next_active_bot(self, current_bot_id: int) -> bool:
        try:
            idx = BOT_IDS.index(current_bot_id)
        except ValueError:
            return False
        return any(self.bot_active_var[b].get() for b in BOT_IDS[idx + 1 :])

    def _sleep_with_pause(self, total_sec: float) -> bool:
        remaining = float(total_sec)
        if remaining <= 0:
            return True
        while remaining > 0:
            if self.carousel_stop.is_set():
                return False
            if self.is_paused:
                time.sleep(0.15)
                continue
            step = min(0.2, remaining)
            time.sleep(step)
            remaining -= step
        return True

    # =========================
    # STATUS + CONTROLS
    # =========================
    def set_status(self, bot_id: int, state: str):
        def _do():
            lbl = self.bot_status_lbl[bot_id]
            if state == "idle":
                lbl.config(text="IDLE", bg="#2a2a2b", fg="#a2ffb8", relief="flat")
            elif state == "running":
                lbl.config(text="RUN", bg="#19e57c", fg="#131e15", relief="groove")
            elif state == "done":
                lbl.config(text="DONE", bg="#85ffa8", fg="#151d18", relief="groove")
            elif state == "fail":
                lbl.config(text="FAIL", bg="#e34d60", fg="#fff", relief="groove")
            self._apply_bot_controls(bot_id)
        self._ui(_do)

    def _on_active_toggle(self, bot_id: int):
        self.save_config()
        if not self.bot_active_var[bot_id].get() and bot_id in self.processes:
            self.stop_bot(bot_id)
        self._apply_bot_controls(bot_id)

    def _apply_bot_controls(self, bot_id: int):
        def _do():
            is_active = bool(self.bot_active_var[bot_id].get())
            is_running = bot_id in self.processes and self.processes[bot_id].poll() is None

            tile = self.bot_frame[bot_id]
            txt = self.bot_active_lbl_text[bot_id]
            lbl = self.bot_active_lbl_widget[bot_id]

            if is_active:
                txt.set("Active")
                lbl.config(fg="#19e57c")
                tile.config(highlightbackground="#55ff44", highlightcolor="#55ff44")
            else:
                txt.set("Inactive")
                lbl.config(fg="#ff9d2e")
                tile.config(highlightbackground="#3a3a3a", highlightcolor="#3a3a3a")

            lock = self.carousel_running or is_running
            self.bot_dd_script[bot_id].config(state="disabled" if lock else "readonly")
        self._ui(_do)

    def _set_loop_ui(self, running: bool):
        def _do():
            if not self.btn_start_loop or not self.btn_stop_all:
                return

            if self.btn_play_top:
                if running:
                    if self.is_paused:
                        self.btn_play_top.config(text="⏸️ Paused (F8)", state="normal", bg="#2a2a2b", activebackground="#2a2a2b")
                    else:
                        self.btn_play_top.config(text="🎠 Playing…", state="disabled", bg="#2a2a2b", activebackground="#2a2a2b")
                else:
                    self.btn_play_top.config(text="▶️ Play (F9)", state="normal", bg="#16b870", activebackground="#29db92")

            if running:
                if self.is_paused:
                    self.btn_start_loop.config(text="⏸️ Paused (F8)", state="normal", bg="#2a2a2b", activebackground="#2a2a2b")
                else:
                    self.btn_start_loop.config(text="🎠 Loop draait…", state="disabled", bg="#2a2a2b", activebackground="#2a2a2b")
                self.btn_stop_all.config(state="normal")
            else:
                self.btn_start_loop.config(text="▶️ Start loop (F9)", state="normal", bg="#16b870", activebackground="#29db92")
                self.btn_stop_all.config(state="normal")
        self._ui(_do)

    # =========================
    # OVERLAY
    # =========================
    def _overlay_running(self) -> bool:
        return self.overlay_proc is not None and self.overlay_proc.poll() is None

    def _sync_overlay_button(self):
        if not self.btn_overlay:
            return
        if self._overlay_running():
            self.btn_overlay.config(text="🟥 Stop overlay", bg="#e34d60", activebackground="#ff6b7c")
        else:
            self.btn_overlay.config(text="🟪 Start overlay", bg="#7c3aed", activebackground="#8f5bff")

    def toggle_overlay(self):
        if self._overlay_running():
            self.stop_overlay()
        else:
            self.start_overlay()

    def start_overlay(self):
        if not OVERLAY_LAUNCHER.exists():
            messagebox.showerror("overlay_launcher.py ontbreekt", f"Niet gevonden:\n{OVERLAY_LAUNCHER}")
            return
        try:
            self.log("🟪 Overlay start...")
            self.overlay_proc = subprocess.Popen(
                [sys.executable, str(OVERLAY_LAUNCHER)],
                cwd=str(PROJECT_ROOT),
                env=os.environ.copy(),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except Exception as e:
            self.log(f"❌ Overlay fout: {e}")
            self.overlay_proc = None
        self._sync_overlay_button()

    def stop_overlay(self):
        if not self._overlay_running():
            self.overlay_proc = None
            self._sync_overlay_button()
            return
        try:
            self.log("🟥 Overlay stop...")
            self.overlay_proc.terminate()
            try:
                self.overlay_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.overlay_proc.kill()
        except Exception as e:
            self.log(f"❌ Overlay stop fout: {e}")
        finally:
            self.overlay_proc = None
            self._sync_overlay_button()

    # =========================
    # PROCESS HELPERS
    # =========================
    def _battery_budget_sec(self, bot_id: int) -> float:
        """
        Daily per-bot budget in seconds used for telemetry.battery_tracker.
        Config keys (optional):
          - battery_budget_hours / battery_budget_minutes (global)
          - battery_budget_hours_{bot_id} / battery_budget_minutes_{bot_id} (per bot override)
          - battery_budget_hours_min / battery_budget_hours_max (global daily range; stable per bot per day)
          - battery_budget_hours_min_{bot_id} / battery_budget_hours_max_{bot_id} (per bot daily range override)
        """

        def _as_int(v, default: int) -> int:
            try:
                return int(v)
            except Exception:
                return default

        def _as_float(v) -> float | None:
            try:
                return float(v)
            except Exception:
                return None

        # If we already wrote today's battery file, keep using the same budget
        # for the rest of the day (even if config changes mid-day).
        date = _today_stamp()
        day_path = PROJECT_ROOT / "telemetry" / "battery" / f"battery_bot{int(bot_id)}_{date}.json"
        existing = load_json(day_path, {})
        if isinstance(existing, dict):
            b = existing.get("budget_sec")
            if isinstance(b, (int, float)) and float(b) > 0:
                return float(b)

        # Optional: choose a per-day budget in a range (e.g. 7-10 hours).
        min_h = self.config.get(f"battery_budget_hours_min_{bot_id}", None)
        max_h = self.config.get(f"battery_budget_hours_max_{bot_id}", None)
        if min_h is None or max_h is None:
            min_h = self.config.get("battery_budget_hours_min", None)
            max_h = self.config.get("battery_budget_hours_max", None)

        lo = _as_float(min_h) if min_h is not None else None
        hi = _as_float(max_h) if max_h is not None else None
        if lo is not None and hi is not None:
            lo = max(0.0, lo)
            hi = max(0.0, hi)
            if hi < lo:
                lo, hi = hi, lo

            # Deterministic "random" per bot per day. This avoids budget jitter
            # across multiple sessions while still giving day-to-day variance.
            rng = random.Random(f"battery_budget_bot{int(bot_id)}_{date}")
            hours = rng.uniform(lo, hi)
            budget_sec = max(0.0, hours * 3600.0)
            # Round to nearest minute so logs look clean.
            budget_sec = round(budget_sec / 60.0) * 60.0
            return float(budget_sec)

        gh = _as_int(self.config.get("battery_budget_hours", 8), 8)
        gm = _as_int(self.config.get("battery_budget_minutes", 0), 0)

        h = self.config.get(f"battery_budget_hours_{bot_id}", None)
        m = self.config.get(f"battery_budget_minutes_{bot_id}", None)
        if h is None:
            h = gh
        if m is None:
            m = gm

        h = _as_int(h, gh)
        m = _as_int(m, gm)

        if h < 0:
            h = 0
        if m < 0:
            m = 0
        if m > 59:
            m = 59

        return float(h * 3600 + m * 60)

    def _battery_begin_session(self, bot_id: int, *, script_name: str, pid: int | None) -> None:
        if _battery_tracker is None:
            return

        budget_sec = self._battery_budget_sec(bot_id)
        started_at = time.time()
        meta = {"source": "bot_manager", "script": str(script_name), "pid": pid}
        try:
            _battery_tracker.begin_session(
                bot_id,
                started_at=started_at,
                budget_sec=budget_sec,
                meta=meta,
            )
            open_path = PROJECT_ROOT / "telemetry" / "battery" / f"open_bot{int(bot_id)}.json"
            self.log(f"[Battery] tracking started | bot={bot_id} budget_sec={int(budget_sec)} open={open_path}")
        except Exception as e:
            self.log(f"[Battery] begin_session error | bot={bot_id} err={e}")

    def _battery_end_session(
        self,
        bot_id: int,
        *,
        reason: str,
        script_name: str,
        pid: int | None,
        rc: int | None,
    ) -> None:
        if _battery_tracker is None:
            return

        ended_at = time.time()
        meta = {"source": "bot_manager", "script": str(script_name), "pid": pid, "rc": rc}
        try:
            payload = _battery_tracker.end_session(
                bot_id,
                ended_at=ended_at,
                reason=str(reason),
                meta=meta,
            )
            if not payload:
                return

            date = payload.get("date") or _today_stamp()
            day_path = PROJECT_ROOT / "telemetry" / "battery" / f"battery_bot{int(bot_id)}_{date}.json"
            used_sec = payload.get("used_sec")
            budget_sec = payload.get("budget_sec")
            fatigue = payload.get("fatigue")
            battery = payload.get("battery")

            self.log(
                f"[Battery] updated | bot={bot_id} date={date} used_sec={used_sec} budget_sec={budget_sec} "
                f"fatigue={fatigue} battery={battery}"
            )
            self.log(f"[Battery] file: {day_path}")
        except Exception as e:
            self.log(f"[Battery] end_session error | bot={bot_id} err={e}")

    def _get_input_recorder(self, bot_id: int) -> BotInputRecorder:
        rec = self.input_recorders.get(bot_id)
        if rec is None:
            rec = BotInputRecorder(bot_id, PROJECT_ROOT / "recordings", self.log)
            self.input_recorders[bot_id] = rec
        return rec

    def _start_input_recording(self, bot_id: int) -> None:
        rec = self._get_input_recorder(bot_id)
        if rec.start():
            self.log(f"🎥 Input wordt opgenomen (Bot {bot_id})")
            self.log(f"🧾 Logs map: {rec.out_dir}")

    def _stop_input_recording(self, bot_id: int, reason: str = "") -> None:
        rec = self.input_recorders.get(bot_id)
        if not rec:
            return
        out = rec.stop_and_save(reason=reason)
        if out:
            self.log(f"🧾 Input log saved: {out.name}")

    def _get_script_path(self, bot_id: int) -> Path | None:
        script_name = self.bot_script_var[bot_id].get()
        real_path = self.scripts_map.get(script_name, "")
        if not script_name or not real_path:
            return None
        p = Path(real_path).resolve()
        return p if p.exists() else None

    def _start_proc(self, bot_id: int, script_path: Path) -> subprocess.Popen | None:
        if not RUNNER_PATH.exists():
            self.log("❌ runner.py ontbreekt")
            return None

        env = os.environ.copy()
        env["BOT_ID"] = str(bot_id)
        env["PYTHONUTF8"] = "1"

        try:
            return subprocess.Popen(
                [sys.executable, str(RUNNER_PATH), str(script_path), str(bot_id)],
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
        except Exception as e:
            self.log(f"❌ start fout: {e}")
            return None

    def _stream_output(self, bot_id: int, proc: subprocess.Popen):
        try:
            if not proc.stdout:
                return
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                self.log(f"[Bot {bot_id}] {line.rstrip()}")
        except Exception as e:
            self.log(f"[Bot {bot_id}] ⚠️ log-reader fout: {e}")
        finally:
            try:
                if proc.stdout:
                    proc.stdout.close()
            except Exception:
                pass

    def stop_bot(self, bot_id: int):
        proc = self.processes.get(bot_id)
        if not proc or proc.poll() is not None:
            self.processes.pop(bot_id, None)
            return
        try:
            self._stop_input_recording(bot_id, reason="stop_bot")
            self.log(f"⛔ Stop Bot {bot_id}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.log(f"⚠️ Force kill Bot {bot_id}")
                proc.kill()
        except Exception as e:
            self.log(f"❌ Stop fout Bot {bot_id}: {e}")
        finally:
            rc = proc.returncode if proc else None
            self._battery_end_session(
                bot_id,
                reason="stop_bot",
                script_name=self.bot_script_var[bot_id].get(),
                pid=getattr(proc, "pid", None),
                rc=(int(rc) if isinstance(rc, int) else None),
            )
            if update_state:
                rc = proc.returncode if proc else None
                update_state(
                    bot_id,
                    active=False,
                    ui_status="stopped",
                    last_rc=rc,
                    ended_at=time.time(),
                )
            self.processes.pop(bot_id, None)

    # =========================
    # LOOP (CAROUSEL)
    # =========================
    def play_carousel(self):
        if self.carousel_thread and self.carousel_thread.is_alive():
            if self.is_paused:
                self.is_paused = False
                self.log("▶️ RESUMED (F9)")
                self._set_loop_ui(True)
                return
            self.log("⏳ Loop draait al")
            return

        if not any(self.bot_active_var[b].get() for b in BOT_IDS):
            self.log("🟠 Geen Active bots geselecteerd")
            return

        self.is_paused = False
        self.carousel_stop.clear()
        self.save_config()

        max_s = self._max_runtime_seconds()
        end_time = None if max_s == 0 else time.time() + max_s

        def run():
            self.carousel_running = True
            self._set_loop_ui(True)
            for b in BOT_IDS:
                self._apply_bot_controls(b)

            mode = int(self.loop_mode_var.get())
            self.log("🎠 Start loop (Active bots)")
            self.log("🔁 Mode: " + ("1 ronde" if mode == 1 else "Oneindig"))

            try:
                ronde = 0

                while not self.carousel_stop.is_set():
                    while self.is_paused and not self.carousel_stop.is_set():
                        time.sleep(0.15)

                    ronde += 1

                    if not any(self.bot_active_var[b].get() for b in BOT_IDS):
                        self.log("🟠 Geen Active bots meer, stoppen")
                        self.carousel_stop.set()
                        return

                    if end_time is not None and time.time() >= end_time:
                        self.log("⏰ Max runtime bereikt, stoppen")
                        self.stop_all()
                        return

                    self.log(f"🧭 Ronde {ronde} start")

                    for bot_id in BOT_IDS:
                        if self.carousel_stop.is_set():
                            return

                        while self.is_paused and not self.carousel_stop.is_set():
                            time.sleep(0.15)

                        if end_time is not None and time.time() >= end_time:
                            self.log("⏰ Max runtime bereikt tijdens ronde, stoppen")
                            self.stop_all()
                            return

                        if not self.bot_active_var[bot_id].get():
                            continue

                        sp = self._get_script_path(bot_id)
                        if not sp:
                            self.set_status(bot_id, "fail")
                            self.log(f"🔴 Bot {bot_id} geen script")
                            continue

                        self.set_status(bot_id, "running")
                        self.log(f"▶️ Bot {bot_id} -> {sp.name}")

                        proc = self._start_proc(bot_id, sp)
                        if not proc:
                            self.set_status(bot_id, "fail")
                            continue

                        if update_state:
                            update_state(
                                bot_id,
                                active=True,
                                ui_status="running",
                                script=sp.name,
                                script_path=str(sp),
                                started_at=time.time(),
                            )

                        self.processes[bot_id] = proc
                        self._battery_begin_session(bot_id, script_name=sp.name, pid=getattr(proc, "pid", None))

                        threading.Thread(target=self._stream_output, args=(bot_id, proc), daemon=True).start()
                        self._start_input_recording(bot_id)

                        while proc.poll() is None:
                            if self.carousel_stop.is_set():
                                self.stop_bot(bot_id)
                                return

                            while self.is_paused and not self.carousel_stop.is_set():
                                time.sleep(0.15)

                            if end_time is not None and time.time() >= end_time:
                                self.stop_bot(bot_id)
                                self.stop_all()
                                return

                            time.sleep(0.2)

                        rc = proc.returncode or 0
                        self._stop_input_recording(bot_id, reason="process_exit")
                        self._battery_end_session(
                            bot_id,
                            reason="process_exit",
                            script_name=sp.name,
                            pid=getattr(proc, "pid", None),
                            rc=int(rc),
                        )
                        if update_state:
                            update_state(
                                bot_id,
                                active=False,
                                ui_status=("done" if rc == 0 else "fail"),
                                last_rc=rc,
                                ended_at=time.time(),
                            )

                        self.set_status(bot_id, "done" if rc == 0 else "fail")
                        if not self._sleep_with_pause(0.12):
                            return

                        delay_s = self._delay_seconds()
                        if delay_s > 0 and self._has_next_active_bot(bot_id):
                            self.log(f"⏳ Wacht {delay_s}s voor volgende bot")
                            if not self._sleep_with_pause(delay_s):
                                return

                    self.log(f"✅ Ronde {ronde} klaar")

                    if mode == 1:
                        self.log("🛑 1 ronde mode, stoppen")
                        self.carousel_stop.set()
                        return

            finally:
                self.carousel_running = False
                self._set_loop_ui(False)
                for b in BOT_IDS:
                    self._apply_bot_controls(b)
                self.log("🛑 Loop gestopt")

        self.carousel_thread = threading.Thread(target=run, daemon=True)
        self.carousel_thread.start()

    def stop_all(self):
        self.carousel_stop.set()
        self.is_paused = False
        for bot_id in BOT_IDS:
            self.stop_bot(bot_id)
        self.carousel_running = False
        self._set_loop_ui(False)
        for b in BOT_IDS:
            self._apply_bot_controls(b)
        self.log("🛑 Stop all klaar")


# =========================
# START
# =========================
if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = BotManagerGUI()
    app.mainloop()
