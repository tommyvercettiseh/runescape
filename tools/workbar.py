from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

# ============================================================
# PATHS / CONFIG
# ============================================================
HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]  # .../Runescape
TOOLS_DIR = ROOT / "tools"
STATE_FILE = TOOLS_DIR / "_workbar_state.json"

PYTHON_EXE = sys.executable
PYTHONW_EXE = str(Path(sys.executable).with_name("pythonw.exe"))

IGNORE_DIRS = {"__pycache__", ".git", ".venv", "venv", ".idea", ".vscode"}
IGNORE_FILES = {"__init__.py", "_workbar_state.json"}
ONLY_PY_FILES = True

APP_TITLE = "🧰 Workbar"
BTN_PADX = 6
BTN_PADY = 6
BTN_MIN_W = 16

# ============================================================
# HELPERS
# ============================================================
def is_windows() -> bool:
    return os.name == "nt"

def relpath(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except:
        return str(p)

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except:
        pass

def scan_tools() -> list[Path]:
    tools: list[Path] = []
    if not TOOLS_DIR.exists():
        return tools

    for dirpath, dirnames, filenames in os.walk(TOOLS_DIR):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for fn in filenames:
            if fn in IGNORE_FILES:
                continue
            if ONLY_PY_FILES and not fn.lower().endswith(".py"):
                continue

            p = Path(dirpath) / fn
            if p.resolve() == HERE:
                continue
            # keep state files hidden; allow other _ prefixed scripts if you want, but default hide
            if p.name.startswith("_") and p.name != "_workbar_state.json":
                continue
            tools.append(p)

    tools.sort(key=lambda x: str(x).lower())
    return tools

def spawn(script_path: Path, *, use_pythonw: bool, args: str = "", cwd: Path | None = None) -> subprocess.Popen:
    exe = PYTHON_EXE
    if use_pythonw and is_windows() and Path(PYTHONW_EXE).exists():
        exe = PYTHONW_EXE

    cmd = [exe, str(script_path)]
    args = (args or "").strip()
    if args:
        cmd += args.split()

    creationflags = 0
    if is_windows() and (not use_pythonw):
        creationflags = subprocess.CREATE_NEW_CONSOLE

    return subprocess.Popen(cmd, cwd=str(cwd or ROOT), creationflags=creationflags)

# ============================================================
# CONFIG WINDOW (checkbox list)
# ============================================================
class ConfigWindow(tk.Toplevel):
    def __init__(self, master: "Workbar", tools: list[Path], visible_set: set[str], always_on_top: bool):
        super().__init__(master)
        self.master = master
        self.tools = tools
        self.visible_set = set(visible_set)
        self.title("⚙️ Configure buttons")
        self.geometry("640x520")
        self.minsize(560, 420)

        self.var_top = tk.BooleanVar(value=always_on_top)
        self.search_var = tk.StringVar(value="")
        self.vars: dict[str, tk.BooleanVar] = {}  # relpath -> var

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Zoek:").grid(row=0, column=0, sticky="w")
        ent = ttk.Entry(top, textvariable=self.search_var)
        ent.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        ent.bind("<KeyRelease>", lambda e: self._render_list())

        ttk.Checkbutton(top, text="📌 Always on top", variable=self.var_top).grid(row=0, column=2, sticky="e")

        actions = ttk.Frame(self, padding=(10, 0, 10, 10))
        actions.grid(row=1, column=0, sticky="ew")
        ttk.Button(actions, text="✅ Select all", command=self._select_all).pack(side="left")
        ttk.Button(actions, text="🧹 Clear", command=self._clear_all).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="🔁 Invert", command=self._invert).pack(side="left", padx=(8, 0))

        body = ttk.Frame(self, padding=(10, 0, 10, 10))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=sb.set)

        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        bot = ttk.Frame(self, padding=10)
        bot.grid(row=3, column=0, sticky="ew")
        bot.columnconfigure(0, weight=1)
        ttk.Button(bot, text="💾 Save", command=self._save).pack(side="right")
        ttk.Button(bot, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 8))

        # init vars
        for p in self.tools:
            r = relpath(p)
            self.vars[r] = tk.BooleanVar(value=(r in self.visible_set))

        self._render_list()
        ent.focus_set()

    def _render_list(self):
        # clear
        for w in self.inner.winfo_children():
            w.destroy()

        q = self.search_var.get().strip().lower()

        row = 0
        for p in self.tools:
            r = relpath(p)
            name = p.stem
            if q and (q not in r.lower() and q not in name.lower()):
                continue

            cb = ttk.Checkbutton(self.inner, text=f"{name}   ({r})", variable=self.vars[r])
            cb.grid(row=row, column=0, sticky="w", pady=2)
            row += 1

        # if nothing matched
        if row == 0:
            ttk.Label(self.inner, text="Geen matches.").grid(row=0, column=0, sticky="w")

    def _select_all(self):
        for v in self.vars.values():
            v.set(True)

    def _clear_all(self):
        for v in self.vars.values():
            v.set(False)

    def _invert(self):
        for v in self.vars.values():
            v.set(not v.get())

    def _save(self):
        visible = {r for r, v in self.vars.items() if v.get()}
        self.master.apply_config(visible, self.var_top.get())
        self.destroy()

# ============================================================
# MAIN WORKBAR (floating button bar)
# ============================================================
class Workbar(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)

        self.state = load_state()
        self.all_tools: list[Path] = scan_tools()

        # default: if no config yet, show a sensible subset
        saved_visible = set(self.state.get("visible_tools", []))
        if not saved_visible:
            # show only a few common ones by default (you can change in config)
            for p in self.all_tools:
                rp = relpath(p)
                if any(k in rp.lower() for k in ["image_debugger", "colour_picker", "input_recorder", "overlay", "mouse"]):
                    saved_visible.add(rp)
        self.visible_tools: set[str] = saved_visible

        self.always_on_top = bool(self.state.get("always_on_top", False))
        self.use_pythonw = tk.BooleanVar(value=bool(self.state.get("use_pythonw", False)))

        # compact floating window feel
        self.resizable(False, False)
        self.attributes("-topmost", self.always_on_top)

        self._build_ui()
        self._rebuild_buttons()

        # save on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        self.container = ttk.Frame(self, padding=8)
        self.container.grid(row=0, column=0, sticky="nsew")

        # top row controls
        ctrl = ttk.Frame(self.container)
        ctrl.grid(row=0, column=0, sticky="ew")
        ctrl.columnconfigure(2, weight=1)

        ttk.Button(ctrl, text="⚙️ Configure", command=self._open_config).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(ctrl, text="🔄 Rescan", command=self._rescan).grid(row=0, column=1, padx=(0, 8))

        ttk.Checkbutton(ctrl, text="🤫 pythonw", variable=self.use_pythonw, command=self._save_state).grid(row=0, column=2, sticky="w")

        self.var_top = tk.BooleanVar(value=self.always_on_top)
        ttk.Checkbutton(ctrl, text="📌 On top", variable=self.var_top, command=self._toggle_top).grid(row=0, column=3, sticky="e")

        # buttons area (wrap)
        self.btn_frame = ttk.Frame(self.container)
        self.btn_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        # status
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self.container, textvariable=self.status).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def _toggle_top(self):
        self.always_on_top = bool(self.var_top.get())
        try:
            self.attributes("-topmost", self.always_on_top)
        except:
            pass
        self._save_state()

    def _open_config(self):
        # refresh list (in case new tools exist)
        self.all_tools = scan_tools()
        ConfigWindow(self, self.all_tools, self.visible_tools, self.always_on_top)

    def _rescan(self):
        self.all_tools = scan_tools()
        # keep only visible entries that still exist
        existing = {relpath(p) for p in self.all_tools}
        self.visible_tools = {r for r in self.visible_tools if r in existing}
        self._rebuild_buttons()
        self._save_state()
        self.status.set(f"🔄 Rescanned: {len(self.all_tools)} tools found.")

    def apply_config(self, visible: set[str], always_on_top: bool):
        self.visible_tools = set(visible)
        self.always_on_top = bool(always_on_top)
        self.var_top.set(self.always_on_top)
        self.attributes("-topmost", self.always_on_top)
        self._rebuild_buttons()
        self._save_state()
        self.status.set(f"✅ Config saved. Buttons: {len(self.visible_tools)}")

    def _tool_by_rel(self, r: str) -> Path | None:
        for p in self.all_tools:
            if relpath(p) == r:
                return p
        return None

    def _rebuild_buttons(self):
        for w in self.btn_frame.winfo_children():
            w.destroy()

        # collect tools in display order: sorted by stem
        selected = []
        for r in self.visible_tools:
            p = self._tool_by_rel(r)
            if p:
                selected.append(p)
        selected.sort(key=lambda p: p.stem.lower())

        if not selected:
            ttk.Label(self.btn_frame, text="Geen buttons geselecteerd. Klik ⚙️ Configure.").grid(row=0, column=0, sticky="w")
            self._fit_window()
            return

        # grid wrap: choose columns based on count
        n = len(selected)
        cols = 6 if n >= 18 else 5 if n >= 12 else 4 if n >= 8 else 3 if n >= 4 else 2
        cols = max(2, cols)

        r = 0
        c = 0
        for p in selected:
            name = p.stem.replace("_", " ")
            b = ttk.Button(
                self.btn_frame,
                text=name,
                width=BTN_MIN_W,
                command=lambda pp=p: self._run_tool(pp),
            )
            b.grid(row=r, column=c, padx=BTN_PADX, pady=BTN_PADY, sticky="ew")

            c += 1
            if c >= cols:
                c = 0
                r += 1

        self._fit_window()

    def _fit_window(self):
        # Let tkinter compute requested size, then apply
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        # keep it compact but readable
        self.geometry(f"{w}x{h}")

    def _run_tool(self, p: Path):
        try:
            spawn(p, use_pythonw=bool(self.use_pythonw.get()), cwd=ROOT)
            tag = "pythonw" if self.use_pythonw.get() else "python"
            self.status.set(f"▶ {tag}: {relpath(p)}")
        except Exception as e:
            messagebox.showerror("Run failed", str(e))
            self.status.set("❌ Run failed.")

        self._save_state()

    def _save_state(self):
        self.state["visible_tools"] = sorted(self.visible_tools)
        self.state["always_on_top"] = bool(self.always_on_top)
        self.state["use_pythonw"] = bool(self.use_pythonw.get())
        save_state(self.state)

    def _on_close(self):
        self._save_state()
        self.destroy()

# ============================================================
if __name__ == "__main__":
    app = Workbar()
    app.mainloop()