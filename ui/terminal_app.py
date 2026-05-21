import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *
from core.dscript import DungScriptInterpreter
from ui.snake_app import SnakeApp
from ui.toast import Toast


class TerminalApp(WindowBase):
    def __init__(self, master, state, x=90, y=520):
        super().__init__(master, "Recepción", GREEN, 720, 360, x, y)
        self.state = state
        self.interpreter = DungScriptInterpreter(state)
        self.content.configure(bg=PANEL)

        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(head, text="Terminal de la recepción", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head, text="Escribí AYUDA para ver los comandos", bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        self.output = tk.Text(
            self.content, bg="#0b1220", fg="#dbeafe", insertbackground="#dbeafe",
            font=("Consolas", 11), relief="flat", highlightthickness=0, state="disabled"
        )
        self.output.pack(fill="both", expand=True, padx=12, pady=(8, 6))

        self.entry = tk.Entry(
            self.content, bg="#0b1220", fg="#dbeafe", insertbackground="#dbeafe",
            font=("Consolas", 11), relief="flat", highlightthickness=1, highlightbackground=BORDER
        )
        self.entry.pack(fill="x", padx=12, pady=(0, 12), ipady=6)
        self.entry.bind("<Return>", self.run_cmd)

        self._print("Hospital MS — Recepción\n")
        self._print("Comandos principales:\n")
        self._print("  ADMITIR Juan GRAVEDAD 2 TIEMPO 10\n")
        self._print("  TRIAGE GRAVEDAD\n")
        self._print("  OPERAR 1 QUIROFANO\n")
        self._print("  RECURSOS\n")
        self._print("  DEADLOCK\n")
        self._print("  LISTA\n\n> ")
        self.master.after(50, self.entry.focus_set)

    def _print(self, text):
        self.output.config(state="normal")
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.config(state="disabled")

    def run_cmd(self, event=None):
        if not self.alive:
            return
        cmd = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if not cmd:
            self.entry.focus_set()
            return

        self._print(cmd + "\n")
        result = self.interpreter.execute(cmd)
        if result:
            self._print(result + "\n")
        self._print("> ")
        self.entry.focus_set()

        upper = cmd.upper()
        if upper == "EASTER":
            Toast(self.master, "Snake desbloqueado", GREEN)
            SnakeApp(self.master, self.state, 460, 150)
        elif upper.startswith("DEADLOCK"):
            Toast(self.master, "Deadlock demo lanzada", RED)