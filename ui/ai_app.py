import tkinter as tk
import threading
from ui.window_base import WindowBase
from ui.theme import *
from core.ai_brain import HospitalAI
from ui.toast import Toast


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
        tk.Label(top, text="Consultá sobre el simulador o sobre Sistemas Operativos", bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        row = tk.Frame(top, bg=PANEL)
        row.pack(fill="x", pady=(6, 0))
        self.status_label = tk.Label(row, text="● Disponible", bg=PANEL, fg=GREEN, font=FONT_BOLD)
        self.status_label.pack(side="left")

        tk.Button(row, text="Limpiar", bg=PANEL_2, fg=FG, relief="flat",
                  command=self.clear_chat, font=FONT, padx=10, pady=4, cursor="hand2").pack(side="right")

        self.chat = tk.Text(
            self.content, bg="#f8fafc", fg=FG, font=FONT_MD,
            relief="flat", highlightthickness=1, highlightbackground=BORDER,
            wrap="word", padx=10, pady=10
        )
        self.chat.pack(fill="both", expand=True, padx=14, pady=(8, 10))
        self.chat.config(state="disabled")

        bottom = tk.Frame(self.content, bg=PANEL)
        bottom.pack(fill="x", padx=14, pady=(0, 14))

        self.entry = tk.Entry(
            bottom, bg="#ffffff", fg=FG, insertbackground=FG,
            font=FONT_MD, relief="flat",
            highlightthickness=1, highlightbackground=BORDER
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", self.ask)

        self.btn = tk.Button(bottom, text="Consultar", bg=TEAL, fg="white",
                             relief="flat", command=self.ask,
                             font=FONT_BOLD, padx=14, cursor="hand2")
        self.btn.pack(side="left")

        self.write_bot("Hola. Preguntame sobre el simulador o sobre Sistemas Operativos.")
        self.master.after(50, self.entry.focus_set)

    def _append(self, text):
        self.chat.config(state="normal")
        self.chat.insert(tk.END, text)
        self.chat.see(tk.END)
        self.chat.config(state="disabled")

    def write_bot(self, text):
        self._append(f"Asistente: {text}\n\n")

    def write_user(self, text):
        self._append(f"Vos: {text}\n")

    def clear_chat(self):
        self.chat.config(state="normal")
        self.chat.delete("1.0", tk.END)
        self.chat.config(state="disabled")
        self.ai.memory.clear()
        self.write_bot("Conversación reiniciada.")

    def set_thinking(self, on):
        self.thinking = on
        if not self.alive:
            return
        if on:
            self.status_label.config(text="● Consultando...", fg=ORANGE)
        else:
            self.status_label.config(text="● Disponible", fg=GREEN)
        self.btn.config(state="disabled" if on else "normal")
        self.entry.config(state="disabled" if on else "normal")
        if not on:
            self.entry.focus_set()

    def ask(self, event=None):
        if self.thinking:
            return
        q = self.entry.get().strip()
        self.entry.delete(0, tk.END)
        if not q:
            return

        self.write_user(q)
        self.set_thinking(True)

        def worker():
            try:
                answer = self.ai.think(q)
            except Exception as e:
                answer = f"(Error: {e})"
            if self.alive:
                self.master.after(0, lambda: self.finish_answer(q, answer))

        threading.Thread(target=worker, daemon=True).start()

    def finish_answer(self, q, answer):
        if not self.alive:
            return
        self.write_bot(answer or "(sin respuesta)")
        self.set_thinking(False)
        if self.state:
            self.state.log("ASIST", f"Consulta: {q}")
        try:
            Toast(self.master, "Respuesta recibida", TEAL)
        except Exception:
            pass