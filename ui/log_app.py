import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *


class LogApp(WindowBase):
    def __init__(self, master, state, x=820, y=40):
        super().__init__(master, "Bitácora de Guardia", GOLD, 440, 625, x, y)
        self.state = state
        self.content.configure(bg=PANEL)

        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(head, text="Eventos del sistema", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head, text="Ingresos, scheduling, recursos y deadlocks", bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        self.text = tk.Text(
            self.content, bg="#0b1220", fg="#dbeafe",
            insertbackground=FG, font=("Consolas", 10),
            relief="flat", highlightthickness=0
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.refresh()

    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        try:
            while not self.state.logs.empty():
                self.text.insert(tk.END, self.state.logs.get_nowait() + "\n")
        except Exception:
            pass
        self.text.see(tk.END)

        if self.alive:
            self.frame.after(150, self.refresh)