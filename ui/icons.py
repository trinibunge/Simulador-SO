import tkinter as tk
from ui.theme import *


def make_icon(parent, title, image_path, command):
    frame = tk.Frame(parent, bg=parent["bg"])

    img = tk.PhotoImage(file=image_path)
    frame.image = img  # mantener referencia viva

    btn = tk.Button(
        frame,
        image=img,
        bg=parent["bg"],
        relief="flat",
        bd=0,
        command=command,
        activebackground=parent["bg"],
        highlightthickness=0,
        cursor="hand2"
    )
    btn.pack()

    label = tk.Label(frame, text=title, bg=parent["bg"], fg=FG, font=FONT_SM)
    label.pack(pady=(6, 0))

    return frame