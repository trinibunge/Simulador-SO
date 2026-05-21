import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *


class ProcessApp(WindowBase):
    def __init__(self, master, state, x=720, y=70):
        super().__init__(master, "📊 Process Monitor", BLUE, 470, 360, x, y)
        self.state = state

        self.text = tk.Text(self.content, bg=PANEL_2, fg=FG, insertbackground=FG,
                            font=FONT, relief="flat", highlightthickness=0)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh()

    def refresh(self):
        if not self.frame.winfo_exists():
            return

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, " PID   NAME            PRI   STATE\n")
        self.text.insert(tk.END, " ─────────────────────────────────────\n")
        for h in sorted(self.state.get_heroes(), key=lambda x: x.pid):
            self.text.insert(tk.END, f" {h.pid:<4}  {h.name:<14}  {h.priority:<4}  {h.state}\n")

        self.text.insert(tk.END, "\n")
        self.text.insert(tk.END, f" Scheduler : {self.state.scheduler_mode}\n")
        self.text.insert(tk.END, f" Chaos     : {self.state.chaos_mode}\n")
        self.text.insert(tk.END, f" RAM       : {len(self.state.get_heroes())}/{self.state.ram_limit}\n")

        self.frame.after(600, self.refresh)