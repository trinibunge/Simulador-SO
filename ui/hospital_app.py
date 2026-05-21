import tkinter as tk
import random
from ui.window_base import WindowBase
from ui.theme import *
from ui.toast import Toast


class HospitalApp(WindowBase):
    BG = "#f8fbff"
    INK = "#102033"
    SOFT_INK = "#5d6b7c"
    SUB_INK = "#8b97a8"
    DIVIDER = "#e1e8f0"

    READY_BORD = "#3b82f6"
    RUN_BORD = "#16a34a"
    BLOCK_BORD = "#ef4444"

    def __init__(self, master, state, x=10, y=40):
        super().__init__(master, "Hospital MS — Panel de Operaciones", BLUE, 980, 740, x, y)
        self.state = state
        self._patient_counter = 0
        self.content.configure(bg=self.BG)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(header, text="Hospital MS", bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Procesos, planificación, recursos compartidos y deadlock",
            bg=self.BG,
            fg=self.SUB_INK,
            font=FONT_ITALIC
        ).pack(anchor="w", pady=(2, 0))

        actions = tk.Frame(self.content, bg=self.BG)
        actions.pack(fill="x", padx=16, pady=(0, 10))

        self._btn(actions, "Admitir paciente", BLUE, self.spawn_random)
        self._btn(actions, "Caso crítico", RED, self.spawn_critical)
        self._btn(actions, "Llegan 8", CYAN, self.spawn_many)
        tk.Frame(actions, bg=self.BG, width=14).pack(side="left")
        self._btn(actions, "Triage llegada", "#475569", lambda: self._set_mode("ROUNDROBIN"))
        self._btn(actions, "Triage gravedad", PURPLE, lambda: self._set_mode("PRIORITY"))
        tk.Frame(actions, bg=self.BG, width=14).pack(side="left")
        self._btn(actions, "Provocar deadlock", RED, self.trigger_deadlock)
        self._btn(actions, "Resolver deadlock", GREEN, self.resolve_deadlock)

        self.summary = tk.Frame(self.content, bg=self.BG)
        self.summary.pack(fill="x", padx=16, pady=(0, 10))

        self.card_wait = self._metric_card(self.summary, "En espera", "0", BLUE)
        self.card_run = self._metric_card(self.summary, "Atendidos", "0", GREEN)
        self.card_block = self._metric_card(self.summary, "Bloqueados", "0", RED)

        area = tk.Frame(self.content, bg=self.BG)
        area.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        self.list_frame = tk.Frame(area, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.list_frame.pack(fill="both", expand=True)

        title = tk.Frame(self.list_frame, bg=PANEL)
        title.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(title, text="Pacientes", bg=PANEL, fg=self.INK, font=FONT_BIG).pack(side="left")
        self.list_count = tk.Label(title, text="", bg=PANEL, fg=MUTED, font=FONT_SM)
        self.list_count.pack(side="right")

        self.list_body = tk.Frame(self.list_frame, bg=PANEL)
        self.list_body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self.res_frame = tk.Frame(self.content, bg=self.BG)
        self.res_frame.pack(fill="x", padx=16, pady=(0, 8))

        head = tk.Frame(self.res_frame, bg=self.BG)
        head.pack(fill="x", pady=(0, 6))
        tk.Label(head, text="Recursos compartidos", bg=self.BG, fg=self.INK, font=FONT_BIG).pack(side="left")
        tk.Label(head, text="un paciente por recurso", bg=self.BG, fg=self.SUB_INK, font=FONT_SM).pack(side="right")

        self.res_cards = tk.Frame(self.res_frame, bg=self.BG)
        self.res_cards.pack(fill="x")

        self.deadlock_frame = tk.Frame(self.content, bg="#fef2f2", highlightthickness=1, highlightbackground="#fca5a5")
        self.deadlock_title = tk.Label(
            self.deadlock_frame,
            text="",
            bg="#fef2f2",
            fg=RED,
            font=FONT_BOLD,
            justify="left",
            anchor="w"
        )
        self.deadlock_title.pack(anchor="w", padx=12, pady=(10, 2))

        self.deadlock_text = tk.Label(
            self.deadlock_frame,
            text="",
            bg="#fef2f2",
            fg=SOFT,
            font=FONT_SM,
            justify="left",
            wraplength=920,
            anchor="w"
        )
        self.deadlock_text.pack(anchor="w", padx=12, pady=(0, 10))

        footer = tk.Frame(self.content, bg=self.BG)
        footer.pack(fill="x", padx=16, pady=(0, 12))
        self.status_var = tk.StringVar(value="")
        tk.Label(
            footer,
            textvariable=self.status_var,
            bg=self.BG,
            fg=self.SOFT_INK,
            font=FONT_SM,
            anchor="w"
        ).pack(fill="x")

    def _btn(self, parent, text, color, cmd):
        b = tk.Button(
            parent,
            text=text,
            bg=color,
            fg="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=FONT_BOLD,
            cursor="hand2",
            activebackground=color,
            activeforeground="white",
            command=cmd
        )
        b.pack(side="left", padx=4)
        return b

    def _metric_card(self, parent, label, value, color):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(side="left", expand=True, fill="x", padx=4)
        tk.Frame(frame, bg=color, height=4).pack(fill="x")
        body = tk.Frame(frame, bg=PANEL)
        body.pack(fill="both", expand=True, padx=14, pady=12)
        tk.Label(body, text=label, bg=PANEL, fg=MUTED, font=FONT_SM).pack(anchor="w")
        val = tk.Label(body, text=value, bg=PANEL, fg=FG, font=("Segoe UI", 20, "bold"))
        val.pack(anchor="w", pady=(2, 0))
        return {"frame": frame, "value": val}

    def _set_mode(self, mode):
        self.state.set_mode(mode)
        Toast(self.master, "Triage actualizado", BLUE)

    def _next_name(self):
        self._patient_counter += 1
        return f"Paciente {self._patient_counter}"

    def spawn_random(self):
        self.state.add_hero(self._next_name(), random.randint(3, 8), random.randint(5, 12))

    def spawn_critical(self):
        self.state.add_hero(self._next_name(), priority=1, burst=8)

    def spawn_many(self):
        for _ in range(8):
            self.spawn_random()

    def trigger_deadlock(self):
        self.state.deadlock_demo = True
        Toast(self.master, "Se activó la demostración de deadlock", RED)

    def resolve_deadlock(self):
        self.state.deadlock_resolve_now = True
        Toast(self.master, "Resolución solicitada", GREEN if self.state.deadlock_active else ORANGE)

    def refresh(self):
        if not self.alive:
            return
        try:
            if not self.frame.winfo_exists():
                return
        except Exception:
            return

        try:
            self._render()
        except Exception:
            pass

        if self.alive:
            self.frame.after(150, self.refresh)

    def _render(self):
        with self.state.lock:
            heroes = list(self.state.heroes.values())
            owners = dict(self.state.resource_owner)
            waiters = {k: list(v) for k, v in self.state.resource_waiters.items()}
            mode = self.state.scheduler_mode
            tick = self.state.clock_tick
            ram_used = len(heroes)
            ram_limit = self.state.ram_limit
            deadlock_on = self.state.deadlock_active

        ready = [h for h in heroes if h.state == "READY"]
        running = [h for h in heroes if h.state == "RUNNING"]
        blocked = [h for h in heroes if h.state == "BLOCKED"]

        self.card_wait["value"].config(text=str(len(ready)))
        self.card_run["value"].config(text=str(len(running)))
        self.card_block["value"].config(text=str(len(blocked)))

        for w in self.list_body.winfo_children():
            w.destroy()

        self.list_count.config(text=f"{len(heroes)} proceso(s)")

        if not heroes:
            tk.Label(
                self.list_body,
                text="No hay pacientes cargados",
                bg=PANEL,
                fg=SOFT,
                font=FONT_ITALIC
            ).pack(anchor="center", pady=28)
        else:
            for h in sorted(heroes, key=lambda x: x.pid):
                self._patient_row(self.list_body, h).pack(fill="x", pady=4)

        for w in self.res_cards.winfo_children():
            w.destroy()

        for key, label in [("QUIROFANO", "Quirófano"), ("CIRUJANO", "Cirujano")]:
            self._resource_card(self.res_cards, label, owners.get(key), waiters.get(key, [])).pack(fill="x", pady=4)

        mode_label = "orden de llegada" if mode == "ROUNDROBIN" else "por gravedad"
        self.status_var.set(
            f"Triage: {mode_label}    │    Pacientes: {ram_used}/{ram_limit}    │    Tick: {tick}"
        )

        cycle = self.state.detect_deadlock()
        if deadlock_on and cycle:
            names = []
            with self.state.lock:
                for pid in cycle:
                    hero = self.state.heroes.get(pid)
                    if hero:
                        names.append(hero.name)

            self.deadlock_frame.pack(fill="x", padx=16, pady=(0, 10))
            self.deadlock_title.config(text="Deadlock detectado")
            if len(names) >= 2:
                self.deadlock_text.config(
                    text=f"Qué pasó: {names[0]} y {names[1]} quedaron esperando recursos entre sí. "
                         f"Uno tiene un recurso y necesita el del otro, así que ninguno puede avanzar."
                )
            else:
                self.deadlock_text.config(
                    text="Qué pasó: dos pacientes quedaron bloqueados mutuamente por recursos compartidos."
                )
        else:
            self.deadlock_frame.pack_forget()

    def _patient_row(self, parent, hero):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)

        left = tk.Frame(frame, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=12, pady=10)

        right = tk.Frame(frame, bg=PANEL)
        right.pack(side="right", padx=12, pady=10)

        state_color = {"READY": BLUE, "RUNNING": GREEN, "BLOCKED": RED}.get(hero.state, SOFT)

        tk.Label(left, text=hero.name, bg=PANEL, fg=FG, font=FONT_BOLD).pack(anchor="w")
        tk.Label(
            left,
            text=f"PID {hero.pid} · prioridad {hero.priority}",
            bg=PANEL,
            fg=MUTED,
            font=FONT_SM
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(right, text=hero.state, bg=PANEL, fg=state_color, font=FONT_BOLD).pack(anchor="e")
        tk.Label(
            right,
            text=f"{hero.cpu_used}/{hero.burst} CPU",
            bg=PANEL,
            fg=MUTED,
            font=FONT_SM
        ).pack(anchor="e", pady=(2, 0))

        if hero.waiting_for:
            extra = f"Esperando: {hero.waiting_for}"
        elif hero.holding:
            extra = "Posee: " + ", ".join(hero.holding)
        else:
            extra = "Sin recursos"

        tk.Label(frame, text=extra, bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w", padx=12, pady=(0, 8))
        return frame

    def _resource_card(self, parent, label, owner, waiters):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        tk.Frame(frame, bg=GREEN if owner is None else ORANGE, height=4).pack(fill="x")

        body = tk.Frame(frame, bg=PANEL)
        body.pack(fill="x", padx=12, pady=10)

        left = tk.Frame(body, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)

        right = tk.Frame(body, bg=PANEL)
        right.pack(side="right")

        tk.Label(left, text=label, bg=PANEL, fg=FG, font=FONT_BOLD).pack(anchor="w")

        if owner is None:
            status = "Libre"
            color = GREEN
        else:
            with self.state.lock:
                hero = self.state.heroes.get(owner)
                owner_name = hero.name if hero else f"PID {owner}"
            status = f"En uso por {owner_name}"
            color = ORANGE

        tk.Label(left, text=status, bg=PANEL, fg=color, font=FONT_SM).pack(anchor="w", pady=(2, 0))

        if waiters:
            names = []
            with self.state.lock:
                for pid in waiters:
                    hero = self.state.heroes.get(pid)
                    if hero:
                        names.append(hero.name)
            wait_text = "Cola: " + ", ".join(names)
        else:
            wait_text = "Sin cola"

        tk.Label(right, text=wait_text, bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="e")
        return frame