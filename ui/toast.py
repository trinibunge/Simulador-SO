
import tkinter as tk
from ui.theme import *


class Toast:
    def __init__(self, master, text, color=BLUE, duration=2000):
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry("320x70+920+36")
        self.win.configure(bg=PANEL)

        frame = tk.Frame(self.win, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=True)

        bar = tk.Frame(frame, bg=color, height=4)
        bar.pack(fill="x")

        tk.Label(
            frame,
            text=text,
            bg=PANEL,
            fg=FG,
            font=FONT_MD,
            wraplength=290,
            justify="left"
        ).pack(anchor="w", padx=14, pady=16)

        self.win.after(duration, self.win.destroy)