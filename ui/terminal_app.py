import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *
from core.dscript import ScriptInterpreter
from ui.snake_app import SnakeApp
from ui.toast import Toast

T_BG       = "#0b1220"
T_FG       = "#dbeafe"
T_PROMPT   = "#38bdf8"
T_OUTPUT   = "#94a3b8"
T_OK       = "#4ade80"
T_ERR      = "#f87171"
T_WARN     = "#fbbf24"
T_INFO     = "#67e8f9"
T_FONT     = ("Consolas", 11)
PROMPT_STR = "$ "


class TerminalApp(WindowBase):
    def __init__(self, master, state, x=90, y=520):
        super().__init__(master, "Recepción", GREEN, 720, 420, x, y)
        self.state = state
        self.interpreter = ScriptInterpreter(state)
        self._cmd_history: list[str] = []
        self._hist_idx: int = -1

        # Forzar fondo oscuro en el content del WindowBase
        self.content.configure(bg=T_BG)

        self._build_ui()

        self._print("Hospital MS v1.0 — Terminal de Recepción\n", "info")
        self._print("Escribí AYUDA para ver los comandos disponibles.\n", "output")
        self._print("\n", "output")
        self._new_prompt()
        self.master.after(100, lambda: self.term.focus_set())

    def _build_ui(self):
        # El Text va directo dentro de self.content, sin frame intermedio
        sb = tk.Scrollbar(
            self.content, bg=T_BG, troughcolor="#0d1829",
            activebackground="#1e3a5f", bd=0, highlightthickness=0, width=8
        )
        sb.pack(side="right", fill="y")

        self.term = tk.Text(
            self.content,
            bg=T_BG, fg=T_FG,
            insertbackground=T_PROMPT,
            selectbackground="#1e3a5f",
            selectforeground=T_FG,
            font=T_FONT,
            relief="flat",
            highlightthickness=0,
            wrap="word",
            undo=False,
            yscrollcommand=sb.set,
            padx=14, pady=10,
            spacing3=2,
            cursor="xterm",
        )
        self.term.pack(side="left", fill="both", expand=True)
        sb.config(command=self.term.yview)

        for name, fg in (
            ("prompt", T_PROMPT), ("output", T_OUTPUT), ("ok", T_OK),
            ("err", T_ERR), ("warn", T_WARN), ("info", T_INFO),
        ):
            self.term.tag_config(name, foreground=fg)

        self.term.bind("<Return>",    self._on_enter)
        self.term.bind("<BackSpace>", self._on_backspace)
        self.term.bind("<Home>",      self._on_home)
        self.term.bind("<Up>",        self._on_hist_up)
        self.term.bind("<Down>",      self._on_hist_down)
        self.term.bind("<Control-l>", self._on_ctrl_l)
        self.term.bind("<Control-c>", self._on_ctrl_c)
        self.term.bind("<KeyPress>",  self._guard)

    def _new_prompt(self):
        self._print(PROMPT_STR, "prompt")
        # gravity "left": el mark no se mueve cuando se inserta texto después
        self.term.mark_set("input_start", "end-1c")
        self.term.mark_gravity("input_start", "left")
        self.term.mark_set("insert", "end")
        self.term.see("end")

    def _print(self, text: str, tag: str = "output"):
        self.term.insert("end", text, tag)
        self.term.see("end")

    def _get_input(self) -> str:
        return self.term.get("input_start", "end-1c")

    def _set_input(self, text: str):
        self.term.delete("input_start", "end")
        self.term.insert("end", text)
        self.term.mark_set("insert", "end")
        self.term.see("end")

    def _before_input(self) -> bool:
        return self.term.compare("insert", "<", "input_start")

    def _guard(self, event):
        if event.char and not (event.state & 0x4):
            if self._before_input():
                self.term.mark_set("insert", "end")

    def _on_backspace(self, event):
        if self.term.compare("insert", "<=", "input_start"):
            return "break"

    def _on_home(self, event):
        self.term.mark_set("insert", "input_start")
        return "break"

    def _on_hist_up(self, event):
        if not self._cmd_history:
            return "break"
        self._hist_idx = min(self._hist_idx + 1, len(self._cmd_history) - 1)
        self._set_input(self._cmd_history[self._hist_idx])
        return "break"

    def _on_hist_down(self, event):
        if self._hist_idx <= 0:
            self._hist_idx = -1
            self._set_input("")
        else:
            self._hist_idx -= 1
            self._set_input(self._cmd_history[self._hist_idx])
        return "break"

    def _on_ctrl_l(self, event):
        self.term.delete("1.0", "end")
        self._new_prompt()
        return "break"

    def _on_ctrl_c(self, event):
        try:
            self.term.index("sel.first")
        except tk.TclError:
            self._print("^C\n", "warn")
            self._new_prompt()
        return "break"

    def _on_enter(self, event):
        if not self.alive:
            return "break"

        cmd = self._get_input().strip()
        self._hist_idx = -1

        if cmd and (not self._cmd_history or self._cmd_history[0] != cmd):
            self._cmd_history.insert(0, cmd)

        self.term.mark_set("insert", "end")
        self._print("\n")

        if not cmd:
            self._new_prompt()
            return "break"

        if cmd.upper() == "CLEAR":
            self.term.delete("1.0", "end")
            self._new_prompt()
            return "break"

        result = self.interpreter.execute(cmd)
        if result:
            self._print(result + "\n", self._tag_for(result))

        self._new_prompt()

        cmd_up = cmd.upper()
        if cmd_up == "EASTER":
            Toast(self.master, "Snake desbloqueado", GREEN)
            SnakeApp(self.master, self.state, 460, 150)
        elif cmd_up.startswith("DEADLOCK"):
            Toast(self.master, "Deadlock demo lanzada", RED)

        return "break"

    @staticmethod
    def _tag_for(text: str) -> str:
        low = text.lower()
        if any(w in low for w in ("error", "fallo", "no se pudo", "inválido", "no encontrado")):
            return "err"
        if any(w in low for w in ("advertencia", "atención", "deadlock", "bloqueado")):
            return "warn"
        if any(w in low for w in ("admitido", "operación iniciada", "listo", "ok", "éxito")):
            return "ok"
        return "output"