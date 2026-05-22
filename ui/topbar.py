import tkinter as tk
from ui.theme import *


class TopBar:
    def __init__(self, master, state, desktop):
        self.master = master
        self.state = state
        self.desktop = desktop

        self.bar = tk.Frame(master, bg=PANEL, height=34, highlightthickness=1, highlightbackground=BORDER)
        self.bar.pack(side="top", fill="x")

        self.left = tk.Label(self.bar, text="Hospital MS", bg=PANEL, fg=FG, font=FONT_BOLD)
        self.left.pack(side="left", padx=14)

        self.mid = tk.Label(self.bar, text="Sistema listo", bg=PANEL, fg=MUTED, font=FONT_SM)
        self.mid.pack(side="left", padx=12)

        self.right = tk.Label(self.bar, text="00:00", bg=PANEL, fg=BLUE, font=FONT_BOLD)
        self.right.pack(side="right", padx=14)

        self.refresh()

    def refresh(self):
        self.right.config(text=f"{self.state.clock_tick:02d}:{(self.state.clock_tick * 3) % 60:02d}")
        self.mid.config(text=f"Procesos: {len(self.state.get_pacientes())}  |  {self.state.scheduler_mode}")
        self.bar.after(300, self.refresh)