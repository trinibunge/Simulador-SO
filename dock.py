import tkinter as tk
from ui.theme import *
from ui.toast import Toast


class Dock:
    def __init__(self, master, state, desktop):
        self.master = master
        self.state = state
        self.desktop = desktop

        self.frame = tk.Frame(master, bg="#f0f4fa", height=84, highlightthickness=1, highlightbackground=BORDER)
        self.frame.pack(side="bottom", fill="x")

        self.inner = tk.Frame(self.frame, bg="#f0f4fa")
        self.inner.pack(anchor="center", pady=10)

        self.buttons = []

    def add_button(self, text, color, command):
        btn = tk.Button(
            self.inner, text=text, bg=PANEL, fg=color, relief="flat",
            font=FONT_BOLD, padx=14, pady=8, command=command,
            activebackground=PANEL_2
        )
        btn.pack(side="left", padx=10)
        self.buttons.append(btn)

    def notify(self, text, color=BLUE):
        Toast(self.master, text, color)