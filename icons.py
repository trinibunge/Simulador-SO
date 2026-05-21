import tkinter as tk
from ui.theme import *


def make_icon(parent, title, color, command):
    frame = tk.Frame(parent, bg=parent["bg"])
    btn = tk.Button(
        frame, text="⬤", font=("Aptos", 22, "bold"),
        bg=PANEL, fg=color, relief="flat", bd=0,
        width=2, height=1, command=command,
        activebackground=PANEL_2, activeforeground=color
    )
    btn.pack(pady=(0, 6))
    label = tk.Label(frame, text=title, bg=parent["bg"], fg=FG, font=FONT_SM)
    label.pack()
    return frame