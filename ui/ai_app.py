import tkinter as tk
import threading
from ui.window_base import WindowBase
from ui.theme import *
from core.ai_brain import CatacumbaAI
from ui.toast import Toast


class AIApp(WindowBase):
    def __init__(self, master, state, x=480, y=120):
        super().__init__(master, "Oracle", TEAL, 640, 500, x, y)
        self.state = state
        self.ai = CatacumbaAI(state)

        top = tk.Frame(self.content, bg=PANEL)
        top.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            top,
            text="Oracle — IA conversacional",
            bg=PANEL,
            fg=FG,
            font=FONT_BOLD
        ).pack(anchor="w")

        self.status_label = tk.Label(
            top,
            text="Listo",
            bg=PANEL,
            fg=MUTED,
            font=FONT_SM
        )
        self.status_label.pack(anchor="w", pady=(2, 0))

        self.chat = tk.Text(
            self.content,
            bg="#f8fafc",
            fg="#111827",
            font=FONT_MD,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            wrap="word"
        )
        self.chat.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        bottom = tk.Frame(self.content, bg=PANEL)
        bottom.pack(fill="x", padx=12, pady=(0, 12))

        self.entry = tk.Entry(
            bottom,
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            font=FONT_MD,
            relief="flat"
        )
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self.ask)

        self.btn = tk.Button(bottom, text="Ask", bg=TEAL, fg="white", relief="flat", command=self.ask)
        self.btn.pack(side="left", padx=(8, 0))

        self.write_bot("Hola. Soy Oracle. Preguntame lo que quieras.")
        self.entry.focus_set()
        self.lift()

    def write_bot(self, text):
        self.chat.insert(tk.END, f"Oracle: {text}\n\n")
        self.chat.see(tk.END)

    def write_user(self, text):
        self.chat.insert(tk.END, f"Tú: {text}\n")
        self.chat.see(tk.END)

    def ask(self, event=None):
        q = self.entry.get().strip()
        self.entry.delete(0, tk.END)

        if not q:
            return

        self.write_user(q)
        self.status_label.config(text="Pensando...")

        def worker():
            answer = self.ai.think(q)
            self.master.after(0, lambda: self.finish_answer(q, answer))

        threading.Thread(target=worker, daemon=True).start()

    def finish_answer(self, q, answer):
        self.write_bot(answer)
        self.status_label.config(text="Listo")
        self.state.log("AI", f"Pregunta: {q}")
        Toast(self.master, "Respuesta recibida", TEAL)