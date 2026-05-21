import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *


class LogApp(WindowBase):
    def __init__(self, master, state, x=1220, y=70):
        super().__init__(master, "📜 Kernel Log", GOLD, 430, 300, x, y)
        self.state = state

        self.text = tk.Text(self.content, bg="#0b0f16", fg=FG, insertbackground=FG,
                            font=FONT, relief="flat", highlightthickness=0)
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh()

    def refresh(self):
        if not self.frame.winfo_exists():
            return

        while not self.state.logs.empty():
            self.text.insert(tk.END, self.state.logs.get() + "\n")
            self.text.see(tk.END)

        self.frame.after(150, self.refresh)