import tkinter as tk
from ui.theme import *
from PIL import Image, ImageTk


class Dock:
    def __init__(self, master, state, desktop):
        self.master = master
        self.state = state
        self.desktop = desktop

        self.frame = tk.Frame(master, bg="#edf3fa", height=92, highlightthickness=0, bd=0)
        self.frame.pack(side="bottom", fill="x")

        self.inner = tk.Frame(self.frame, bg="#edf3fa", bd=0, highlightthickness=0)
        self.inner.pack(anchor="center", pady=10)

        self.icons = []

    def add_icon(self, title, image_path, command):
        frame = tk.Frame(self.inner, bg="#edf3fa", bd=0, highlightthickness=0)
        frame.pack(side="left", padx=18)

        img = Image.open(image_path).convert("RGBA")
        img = img.resize((44, 44), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        frame.photo = photo

        btn = tk.Button(
            frame,
            image=photo,
            bg="#edf3fa",
            relief="flat",
            bd=0,
            command=command,
            activebackground="#edf3fa",
            highlightthickness=0,
            cursor="hand2",
            padx=0,
            pady=0
        )
        btn.pack()

        self.icons.append(frame)