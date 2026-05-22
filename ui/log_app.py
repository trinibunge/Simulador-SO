import tkinter as tk
import queue
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
        tk.Label(
            head,
            text="Logs persistidos por el demonio de logging (proceso separado)",
            bg=PANEL, fg=MUTED, font=FONT_ITALIC
        ).pack(anchor="w")

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

        # Drenar la cola local (alimentada por el bridge desde el proceso del daemon)
        try:
            while True:
                msg = self.state.logs.get_nowait()
                self.text.insert(tk.END, msg + "\n")
        except queue.Empty:
            pass
        except Exception:
            pass
        self.text.see(tk.END)

        if self.alive:
            self.frame.after(150, self.refresh)