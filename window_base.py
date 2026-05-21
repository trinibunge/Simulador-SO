import tkinter as tk
from ui.theme import *


class WindowBase:
    def __init__(self, master, title, accent=BLUE, width=520, height=360, x=120, y=80):
        self.master = master
        self.accent = accent
        self.minimized = False
        self.normal_height = height

        self.shadow = tk.Frame(master, bg=SHADOW)
        self.shadow.place(x=x+6, y=y+6, width=width, height=height)

        self.frame = tk.Frame(master, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.frame.place(x=x, y=y, width=width, height=height)

        self.titlebar = tk.Frame(self.frame, bg=TITLE_BG, height=34)
        self.titlebar.pack(fill="x")

        self.color_dot = tk.Canvas(self.titlebar, width=12, height=12, bg=TITLE_BG, highlightthickness=0)
        self.color_dot.create_oval(2, 2, 12, 12, fill=accent, outline=accent)
        self.color_dot.pack(side="left", padx=(12, 6), pady=10)

        self.title_label = tk.Label(self.titlebar, text=title, bg=TITLE_BG, fg=TITLE_FG, font=FONT_TITLE)
        self.title_label.pack(side="left")

        self.controls = tk.Frame(self.titlebar, bg=TITLE_BG)
        self.controls.pack(side="right", padx=8)

        self.btn_close = tk.Button(self.controls, text="×", bg=TITLE_BG, fg=RED, relief="flat", bd=0,
                                   font=("Aptos", 12, "bold"), command=self.close, width=2)
        self.btn_close.pack(side="right", padx=2)

        self.btn_min = tk.Button(self.controls, text="–", bg=TITLE_BG, fg=ORANGE, relief="flat", bd=0,
                                 font=("Aptos", 12, "bold"), command=self.toggle_minimize, width=2)
        self.btn_min.pack(side="right", padx=2)

        self.content = tk.Frame(self.frame, bg=PANEL)
        self.content.pack(fill="both", expand=True)

        self._drag = {"x": 0, "y": 0}
        for w in (self.titlebar, self.title_label, self.color_dot):
            w.bind("<ButtonPress-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)

    def close(self):
        self.frame.destroy()
        self.shadow.destroy()

    def lift(self):
        self.shadow.lift()
        self.frame.lift()

    def toggle_minimize(self):
        if self.minimized:
            self.content.pack(fill="both", expand=True)
            self.frame.place_configure(height=self.normal_height)
            self.shadow.place_configure(height=self.normal_height)
            self.minimized = False
        else:
            self.content.pack_forget()
            self.frame.place_configure(height=34)
            self.shadow.place_configure(height=34)
            self.minimized = True

    def start_move(self, event):
        self._drag["x"] = event.x
        self._drag["y"] = event.y

    def do_move(self, event):
        x = self.frame.winfo_x() + event.x - self._drag["x"]
        y = self.frame.winfo_y() + event.y - self._drag["y"]
        self.frame.place(x=x, y=y)
        self.shadow.place(x=x+6, y=y+6)