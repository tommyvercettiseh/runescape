from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from .main import GREEN, RED, YELLOW, ProfileHubApp
from .services import build_master_profile


class HardenedProfileHubApp(ProfileHubApp):
    """Production entrypoint with exception-safe background callbacks."""

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
            except Exception as exc:  # copy text before Python clears the exception variable
                error_text = f"{type(exc).__name__}: {exc}"
                self.root.after(0, lambda text=error_text: self._safe_build_finished(None, text))
            else:
                self.root.after(0, lambda result=master: self._safe_build_finished(result, None))

        threading.Thread(target=worker, name="profile-builder", daemon=True).start()

    def _safe_build_finished(self, master, error_text):
        if not self.root.winfo_exists():
            return
        self.building = False
        self.build_button.config(state="normal", text="Rebuild selected profile")
        if error_text:
            self.sidebar_status.config(text="● Build failed", fg=RED)
            messagebox.showerror("Profile build failed", error_text)
            return
        self.sidebar_status.config(text="● Profile and runtime export rebuilt", fg=GREEN)
        self.refresh_data()
        messagebox.showinfo(
            "Master Profile",
            f"Profiel gebouwd uit {len(master.get('sources') or [])} sessions.\n"
            f"Runtimeprofiel: {self.paths.runtime_profile}",
        )


def main():
    root = tk.Tk()
    HardenedProfileHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
