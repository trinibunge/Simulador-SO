import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *


class ProcessApp(WindowBase):
    """
    📋 Historia Clínica del Hospital.
    Muestra el listado actual de pacientes (procesos) en formato ficha.
    """

    def __init__(self, master, state, x=720, y=70):
        super().__init__(master, "📋 Historia Clínica", BLUE, 540, 420, x, y)
        self.state = state
        self.content.configure(bg=PANEL)

        # header
        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(12, 6))
        tk.Label(head, text="Pacientes en el sistema",
                 bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head,
                 text="vista de todos los procesos (pacientes) que el SO está manejando",
                 bg=PANEL, fg=MUTED, font=FONT_ITALIC
                 ).pack(anchor="w")

        self.text = tk.Text(
            self.content, bg=PANEL_2, fg=FG, insertbackground=FG,
            font=("Consolas", 10), relief="flat",
            highlightthickness=1, highlightbackground=BORDER
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.refresh()

    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, " PID   PACIENTE         GRAV.  ESTADO     ATENCIÓN  RECURSOS\n")
        self.text.insert(tk.END, " " + "─" * 64 + "\n")
        for h in sorted(self.state.get_heroes(), key=lambda x: x.pid):
            held = ",".join(h.holding) or "-"
            wait = f" → {h.waiting_for}" if h.waiting_for else ""
            estado = {
                "READY":   "sala-esp.",
                "RUNNING": "atendido ",
                "BLOCKED": "bloqueado",
            }.get(h.state, h.state)
            self.text.insert(
                tk.END,
                f" {h.pid:<4}  {h.name:<15}  {h.priority:<4}   "
                f"{estado:<10} {h.cpu_used}/{h.burst:<6}  {held}{wait}\n"
            )

        self.text.insert(tk.END, "\n")
        modo = ("orden de llegada" if self.state.scheduler_mode == "ROUNDROBIN"
                else "por gravedad")
        self.text.insert(tk.END, f" Triage     : {modo}\n")
        self.text.insert(tk.END, f" Doctores   : {self.state.num_cpus}\n")
        self.text.insert(tk.END, f" Capacidad  : {len(self.state.get_heroes())}/{self.state.ram_limit}\n")

        if self.alive:
            self.frame.after(500, self.refresh)