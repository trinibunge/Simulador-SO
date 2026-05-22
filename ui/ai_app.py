import tkinter as tk
import threading
from ui.window_base import WindowBase
from ui.theme import *
from core.ai_brain import HospitalAI


class AIApp(WindowBase):
    def __init__(self, master, state, x=480, y=120):
        super().__init__(master, "Asistente Médico", TEAL, 650, 520, x, y)
        self.state = state
        self.ai = HospitalAI(state)
        self.thinking = False
        self.content.configure(bg=PANEL)

        top = tk.Frame(self.content, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(14, 8))

        tk.Label(top, text="Asistente Médico", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            top,
            text="Consultá sobre el simulador o sobre Sistemas Operativos",
            bg=PANEL,
            fg=MUTED,
            font=FONT_ITALIC
        ).pack(anchor="w")

        self.chat = tk.Text(
            self.content,
            bg="#f8fafc",
            fg=FG,
            font=FONT_MD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            wrap="word",
            padx=10,
            pady=10
        )
        self.chat.pack(fill="both", expand=True, padx=14, pady=(8, 10))
        self.chat.config(state="disabled")

        bottom = tk.Frame(self.content, bg=PANEL)
        bottom.pack(fill="x", padx=14, pady=(0, 14))

        self.entry = tk.Entry(
            bottom,
            bg="#ffffff",
            fg=FG,
            insertbackground=FG,
            font=FONT_MD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", self.ask)

        self.btn = tk.Button(
            bottom,
            text="Consultar",
            bg=TEAL,
            fg="white",
            relief="flat",
            command=self.ask,
            font=FONT_BOLD,
            padx=14,
            cursor="hand2"
        )
        self.btn.pack(side="left")

        self._write("Asistente: Hola. Preguntame sobre el simulador o sobre Sistemas Operativos.\n\n")
        self.master.after(100, self.focus_input)

    def focus_input(self):
        try:
            self.frame.lift()
        except Exception:
            pass
        try:
            self.entry.focus_set()
            self.entry.icursor(tk.END)
        except Exception:
            pass

    def _write(self, text):
        self.chat.config(state="normal")
        self.chat.insert(tk.END, text)
        self.chat.see(tk.END)
        self.chat.config(state="disabled")

    def set_thinking(self, on):
        self.thinking = on
        self.btn.config(state="disabled" if on else "normal")
        self.entry.config(state="disabled" if on else "normal")
        if not on:
            self.focus_input()

    def ask(self, event=None):
        if self.thinking:
            return

        q = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if not q:
            self.focus_input()
            return

        self._write(f"Vos: {q}\n")
        self.set_thinking(True)

        def worker():
            try:
                answer = self.ai.think(q)
            except Exception as e:
                answer = f"(Error: {e})"

            if self.alive:
                self.master.after(0, lambda: self.finish_answer(answer))

        threading.Thread(target=worker, daemon=True).start()

    def finish_answer(self, answer):
        if not self.alive:
            return
        self._write(f"Asistente: {answer}\n\n")
        self.set_thinking(False)