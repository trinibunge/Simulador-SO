import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *
from core.dscript import DungScriptInterpreter
from ui.snake_app import SnakeApp
from ui.toast import Toast


class TerminalApp(WindowBase):
    def __init__(self, master, state, x=90, y=520):
        super().__init__(master, "💻 Terminal", GREEN, 650, 320, x, y)
        self.state = state
        self.interpreter = DungScriptInterpreter(state)

        self.output = tk.Text(self.content, bg="#05070a", fg=FG, insertbackground=FG,
                              font=FONT_MD, relief="flat", highlightthickness=0)
        self.output.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        self.entry = tk.Entry(self.content, bg=PANEL_2, fg=FG, insertbackground=FG,
                              font=FONT_MD, relief="flat")
        self.entry.pack(fill="x", padx=10, pady=(0, 10))
        self.entry.bind("<Return>", self.run_cmd)

        self.output.insert(tk.END, "La Catacumba OS terminal lista.\n")
        self.output.insert(tk.END, "Ejemplos:\n")
        self.output.insert(tk.END, "  SPAWN heroe1 PRIORITY 1\n")
        self.output.insert(tk.END, "  SPAWN guardia PRIORITY 4\n")
        self.output.insert(tk.END, "  SCHEDULE PRIORITY\n")
        self.output.insert(tk.END, "  MEMDUMP\n\n")
        self.output.insert(tk.END, "> ")

    def run_cmd(self, event=None):
        cmd = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if not cmd:
            return

        self.output.insert(tk.END, cmd + "\n")
        result = self.interpreter.execute(cmd)
        if result:
            self.output.insert(tk.END, result + "\n")
        self.output.insert(tk.END, "> ")
        self.output.see(tk.END)

        upper = cmd.upper()
        if upper == "EASTER":
            Toast(self.master, "Snake.exe desbloqueado", GREEN)
            SnakeApp(self.master, self.state, 460, 150)
        elif upper == "CHAOS":
            Toast(self.master, "Modo caos activado", ORANGE)
        elif upper == "DEADLOCK":
            Toast(self.master, "Deadlock demo activada", RED)