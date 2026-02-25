import sys, subprocess, tkinter as tk, json, random, time, os, shutil

AREA_NAME = "Antiban_Area"

BOT_OFFSETS = {
    1: (0,   0),
    2: (958, 0),
    3: (0,   498),
    4: (958, 498),
}

# =========================
# DEFAULTS + PRESETS
# =========================
DEFAULT_PRESET_KEY = "2"  # welke preset standaard geselecteerd wordt in de launcher
DEFAULT_VERBOSE = False
DEFAULT_NO_OFFSETS = False

# Presets: minutes (min/max)
# green = actief/bot tijd, red = rust
PRESETS = {
    "1": {"name": "Chill",        "bot_min": 30, "bot_max": 50,  "rest_min": 10, "rest_max": 30},
    "2": {"name": "Standaard",    "bot_min": 60, "bot_max": 70,  "rest_min": 10, "rest_max": 15},
    "3": {"name": "Semi-veilig",  "bot_min": 45, "bot_max": 75,  "rest_min": 15, "rest_max": 35},
    "4": {"name": "Harder",       "bot_min": 80, "bot_max": 120, "rest_min": 8,  "rest_max": 18},
    "5": {"name": "Random-heavy", "bot_min": 35, "bot_max": 140, "rest_min": 12, "rest_max": 55},
}

# === START VERBOSE ===
def get_log_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_verbose.log")

def log_status(msg, *, verbose: bool):
    if not verbose:
        return
    try:
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass
    try:
        print(msg)
    except:
        pass
# === END VERBOSE ===

# === START PATHS ===
def find_repo_root(start_path):
    here = os.path.abspath(start_path)
    if os.path.isfile(here):
        here = os.path.dirname(here)

    cur = here
    while True:
        if os.path.isdir(os.path.join(cur, "config")):
            return cur

        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent

def get_areas_path():
    root = find_repo_root(__file__)
    if not root:
        return None
    return os.path.join(root, "config", "areas.json")
# === END PATHS ===

# === START PYTHON ===
def pick_python_exe():
    pyw = shutil.which("pythonw")
    return pyw or sys.executable
# === END PYTHON ===

# === START LAUNCHER ===
def start_bots(bot_min, bot_max, rest_min, rest_max, verbose, no_offsets):
    py = pick_python_exe()
    script = os.path.abspath(__file__)

    for bot_id in range(1, 5):
        args = [py, script, str(bot_id), str(bot_min), str(bot_max), str(rest_min), str(rest_max)]
        if verbose:
            args.append("verbose")
        if no_offsets:
            args.append("no_offsets")
        subprocess.Popen(args, close_fds=True)

def main_launcher():
    root = tk.Tk()
    root.title("Bot Overlay Launcher")

    # preset selector
    tk.Label(root, text="Preset:").grid(row=0, column=0, sticky="w")
    preset_var = tk.StringVar(value=DEFAULT_PRESET_KEY)

    preset_labels = {k: f"{k}. {v['name']}  (groen {v['bot_min']}-{v['bot_max']}m, rust {v['rest_min']}-{v['rest_max']}m)"
                     for k, v in PRESETS.items()}

    preset_menu = tk.OptionMenu(root, preset_var, *PRESETS.keys())
    preset_menu.grid(row=0, column=1, columnspan=3, sticky="we")

    preset_desc = tk.Label(root, text=preset_labels.get(DEFAULT_PRESET_KEY, ""), fg="gray30", justify="left")
    preset_desc.grid(row=1, column=0, columnspan=4, sticky="w", padx=2)

    def apply_preset(*_):
        k = preset_var.get()
        p = PRESETS.get(k, PRESETS[DEFAULT_PRESET_KEY])
        bot_min.set(p["bot_min"])
        bot_max.set(p["bot_max"])
        rest_min.set(p["rest_min"])
        rest_max.set(p["rest_max"])
        preset_desc.config(text=preset_labels.get(k, ""))

    preset_var.trace_add("write", apply_preset)

    # sliders
    tk.Label(root, text="Bottijd min (min):").grid(row=2, column=0)
    bot_min = tk.Scale(root, from_=30, to=180, orient="horizontal", width=8, length=120)
    bot_min.grid(row=2, column=1)
    tk.Label(root, text="max:").grid(row=2, column=2)
    bot_max = tk.Scale(root, from_=31, to=240, orient="horizontal", width=8, length=120)
    bot_max.grid(row=2, column=3)

    tk.Label(root, text="Rust min (min):").grid(row=3, column=0)
    rest_min = tk.Scale(root, from_=5, to=90, orient="horizontal", width=8, length=120)
    rest_min.grid(row=3, column=1)
    tk.Label(root, text="max:").grid(row=3, column=2)
    rest_max = tk.Scale(root, from_=6, to=120, orient="horizontal", width=8, length=120)
    rest_max.grid(row=3, column=3)

    verbose_var = tk.BooleanVar(value=DEFAULT_VERBOSE)
    no_offsets_var = tk.BooleanVar(value=DEFAULT_NO_OFFSETS)

    tk.Checkbutton(root, text="Verbose (logfile)", variable=verbose_var).grid(row=4, column=0, columnspan=2, sticky="w")
    tk.Checkbutton(root, text="Test: geen offsets", variable=no_offsets_var).grid(row=4, column=2, columnspan=2, sticky="w")

    # set initial preset values
    apply_preset()

    def launch_and_close():
        if verbose_var.get():
            try:
                with open(get_log_path(), "w", encoding="utf-8") as f:
                    f.write("Launcher 🟢\n")
            except:
                pass

        start_bots(bot_min.get(), bot_max.get(), rest_min.get(), rest_max.get(),
                   verbose_var.get(), no_offsets_var.get())
        root.destroy()

    btn = tk.Button(root, text="Start Overlays", command=launch_and_close, bg="#2a8a2d", fg="white")
    btn.grid(row=5, column=0, columnspan=4, pady=12, sticky="we")

    root.mainloop()
# === END LAUNCHER ===

# === START OVERLAY ===
def run_overlay(bot_id, bot_min, bot_max, rest_min, rest_max, verbose, no_offsets):
    log_status(f"Bot {bot_id} start 🟡", verbose=verbose)

    areas_path = get_areas_path()
    if not areas_path or not os.path.isfile(areas_path):
        log_status("areas.json niet gevonden 🔴🖼️", verbose=verbose)
        raise SystemExit("areas.json niet gevonden 🔴🖼️ (verwacht: <repo>/config/areas.json)")
    log_status("areas.json gevonden 🟢🖼️", verbose=verbose)

    with open(areas_path, "r", encoding="utf-8") as f:
        areas = json.load(f)
    log_status("areas.json geladen 🟢", verbose=verbose)

    if AREA_NAME not in areas:
        log_status("AREA_NAME ontbreekt 🔴🖼️", verbose=verbose)
        raise SystemExit(f"AREA_NAME '{AREA_NAME}' niet gevonden in areas.json 🔴")

    area = areas[AREA_NAME]
    base_coords = area.get("coords") if isinstance(area, dict) else area

    if not isinstance(base_coords, (list, tuple)) or len(base_coords) != 4:
        log_status("Coords formaat fout 🔴🖼️", verbose=verbose)
        raise SystemExit("Coords moeten [x1,y1,x2,y2] zijn 🔴🖼️")

    def offset_area(coords, offset):
        x1, y1, x2, y2 = coords
        ox, oy = offset
        return [x1 + ox, y1 + oy, x2 + ox, y2 + oy]

    class OverlayWindow:
        def __init__(self, parent, coords):
            x1, y1, x2, y2 = coords
            w, h = x2 - x1, y2 - y1

            self.win = tk.Toplevel(parent)
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            self.win.geometry(f"{w}x{h}+{x1}+{y1}")

            self.excluded = False
            self.mode = "green"
            self.win.config(bg=self.mode)

            btn_close = tk.Button(self.win, text="✖", bd=0, bg="black", fg="white",
                                  highlightthickness=0, command=self.win.destroy)
            btn_close.place(x=w - 20, y=h - 20, width=18, height=18)

            btn_debug = tk.Button(self.win, text="⚡", bd=0, bg="red", fg="white",
                                  highlightthickness=0, command=self.force_red)
            btn_debug.place(x=w - 42, y=h - 20, width=18, height=18)

            group_center_x = w - 22
            self.btn_exclude = tk.Button(
                self.win, text="Exclude", font=("Segoe UI", 7), bd=0,
                bg="#7c3aed", fg="white", highlightthickness=0,
                command=self.toggle_exclude
            )
            self.btn_exclude.place(x=group_center_x, y=h - 24, width=76, height=18, anchor="s")

            self.timer = tk.Label(self.win, font=("Segoe UI", 8), bg=self.mode, fg="white")
            self.timer.place(x=5, y=5)

            self.next_mode = "red"
            self.next_switch = time.time() + random.randint(bot_min * 60, bot_max * 60)

            log_status("Overlay gemaakt 🟢🖼️", verbose=verbose)
            self._loop()

        def _schedule_next(self):
            if self.excluded:
                self.next_mode = "red"
                self.next_switch = float("inf")
                return

            if self.mode == "green":
                self.next_mode = "red"
                secs = random.randint(bot_min * 60, bot_max * 60)
            else:
                self.next_mode = "green"
                secs = random.randint(rest_min * 60, rest_max * 60)

            self.next_switch = time.time() + secs

        def _loop(self):
            now = time.time()

            if self.excluded:
                self.mode = "red"
                self.win.config(bg="red")
                self.timer.config(bg="red", text="EXCLUDED")
                self.win.after(1000, self._loop)
                return

            if now >= self.next_switch:
                self.mode = self.next_mode
                self.win.config(bg=self.mode)
                self.timer.config(bg=self.mode)
                self._schedule_next()

            rem = max(int(self.next_switch - now), 0)
            m, s = divmod(rem, 60)
            self.timer.config(text=f"{m:02d}:{s:02d}")

            self.win.after(1000, self._loop)

        def force_red(self):
            self.mode = "red"
            self.win.config(bg="red")
            self.timer.config(bg="red")
            self.next_mode = "green"
            self.next_switch = time.time() + random.randint(rest_min * 60, rest_max * 60)

        def toggle_exclude(self):
            self.excluded = not self.excluded
            if self.excluded:
                self.mode = "red"
                self.btn_exclude.config(text="Include", bg="gray20")
                self.win.config(bg="red")
                self.timer.config(bg="red", text="EXCLUDED")
                self.next_mode = "red"
                self.next_switch = float("inf")
            else:
                self.btn_exclude.config(text="Exclude", bg="#7c3aed")
                self.mode = "green"
                self.win.config(bg="green")
                self.timer.config(bg="green")
                self.next_mode = "red"
                self.next_switch = time.time() + random.randint(bot_min * 60, bot_max * 60)

    root = tk.Tk()
    root.withdraw()

    if no_offsets:
        offset = (0, 0)
        log_status("Offsets uit 🟢🖼️", verbose=verbose)
    else:
        offset = BOT_OFFSETS.get(bot_id, (0, 0))
        log_status("Offsets aan 🟢🖼️", verbose=verbose)

    coords = offset_area(base_coords, offset)
    log_status("Coords klaar 🟢🖼️", verbose=verbose)

    OverlayWindow(root, coords)
    root.mainloop()
# === END OVERLAY ===

# === START ENTRYPOINT ===
if __name__ == "__main__":
    # Zonder args: launcher
    if len(sys.argv) == 1:
        main_launcher()
    else:
        # Met args: overlay instance
        try:
            bot_id = int(sys.argv[1])
            bot_min = int(sys.argv[2])
            bot_max = int(sys.argv[3])
            rest_min = int(sys.argv[4])
            rest_max = int(sys.argv[5])

            tail = [a.lower() for a in sys.argv[6:]]
            verbose = "verbose" in tail
            no_offsets = "no_offsets" in tail
        except:
            raise SystemExit("Argumenten ontbreken 🔴")

        run_overlay(bot_id, bot_min, bot_max, rest_min, rest_max, verbose, no_offsets)
# === END ENTRYPOINT ===