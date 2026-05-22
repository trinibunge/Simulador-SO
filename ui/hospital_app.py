import tkinter as tk
import random
import time
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
        super().__init__(master, "Hospital MS — Panel de Operaciones", BLUE, 820, 580, x, y)
        self.state = state
        self._row_cache = {}   # pid -> widget refs dict
        self._res_cache = {}   # resource key -> widget refs dict
        self.content.configure(bg=self.BG)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(header, text="Hospital MS", bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Procesos, planificación, recursos compartidos y deadlock",
            bg=self.BG,
            fg=self.SUB_INK,
            font=FONT_SM
        ).pack(anchor="w", pady=(1, 0))

        actions = tk.Frame(self.content, bg=self.BG)
        actions.pack(fill="x", padx=12, pady=(0, 6))

        self._btn(actions, "Admitir paciente", BLUE, self.spawn_random)
        self._btn(actions, "Caso crítico", RED, self.spawn_critical)
        self._btn(actions, "Llegan 8", CYAN, self.spawn_many)
        tk.Frame(actions, bg=self.BG, width=14).pack(side="left")
        tk.Label(actions, text="Ordenar por:", bg=self.BG, fg=self.SOFT_INK, font=FONT_SM).pack(side="left", padx=(0, 4))
        self._btn(actions, "Llegada", "#475569", lambda: self._set_mode("ROUNDROBIN"))
        self._btn(actions, "Gravedad", PURPLE, lambda: self._set_mode("PRIORITY"))
        tk.Frame(actions, bg=self.BG, width=14).pack(side="left")
        self._btn(actions, "Provocar deadlock", RED, self.trigger_deadlock)

        self.summary = tk.Frame(self.content, bg=self.BG)
        self.summary.pack(fill="x", padx=12, pady=(0, 6))

        self.card_wait = self._metric_card(self.summary, "En espera", "0", BLUE)
        self.card_run = self._metric_card(self.summary, "Atendidos", "0", GREEN)
        self.card_block = self._metric_card(self.summary, "Bloqueados", "0", RED)

        self.deadlock_container = tk.Frame(self.content, bg=self.BG)
        self.deadlock_container.pack(fill="x", padx=12)

        self.deadlock_frame = tk.Frame(self.deadlock_container, bg="#fef2f2", highlightthickness=1, highlightbackground="#fca5a5")
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
        self.deadlock_text.pack(anchor="w", padx=12, pady=(0, 6))

        self._btn_resolve = tk.Button(
            self.deadlock_frame,
            text="Resolver deadlock",
            bg=GREEN,
            fg="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            font=FONT_BOLD,
            cursor="hand2",
            activebackground=GREEN,
            activeforeground="white",
            command=self.resolve_deadlock
        )
        self._btn_resolve.pack(anchor="w", padx=12, pady=(0, 10))

        footer = tk.Frame(self.content, bg=self.BG)
        footer.pack(fill="x", padx=12, pady=(2, 4))
        self.status_var = tk.StringVar(value="")
        tk.Label(
            footer,
            textvariable=self.status_var,
            bg=self.BG,
            fg=self.SOFT_INK,
            font=FONT_SM,
            anchor="w"
        ).pack(fill="x")

        body = tk.Frame(self.content, bg=self.BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        left_col = tk.Frame(body, bg=self.BG, width=220)
        left_col.pack_propagate(False)
        left_col.pack(side="left", fill="y", padx=(0, 8))

        res_head = tk.Frame(left_col, bg=self.BG)
        res_head.pack(fill="x", pady=(0, 6))
        tk.Label(res_head, text="Recursos compartidos", bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(res_head, text="un paciente por recurso", bg=self.BG, fg=self.SUB_INK, font=FONT_SM).pack(anchor="w")

        self.res_cards = tk.Frame(left_col, bg=self.BG)
        self.res_cards.pack(fill="x")

        right_col = tk.Frame(body, bg=self.BG)
        right_col.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(right_col, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.list_frame.pack(fill="both", expand=True)

        title = tk.Frame(self.list_frame, bg=PANEL)
        title.pack(fill="x", padx=14, pady=(12, 8))
        tk.Label(title, text="Pacientes", bg=PANEL, fg=self.INK, font=FONT_BIG).pack(side="left")
        self.list_count = tk.Label(title, text="", bg=PANEL, fg=MUTED, font=FONT_SM)
        self.list_count.pack(side="right")

        scroll_area = tk.Frame(self.list_frame, bg=PANEL)
        scroll_area.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        self._list_canvas = tk.Canvas(scroll_area, bg=PANEL, highlightthickness=0)
        self._list_scrollbar = tk.Scrollbar(scroll_area, orient="vertical", command=self._list_canvas.yview)
        self._list_canvas.configure(yscrollcommand=self._list_scrollbar.set)
        self._list_scrollbar.pack(side="right", fill="y")
        self._list_canvas.pack(side="left", fill="both", expand=True)

        self.list_body = tk.Frame(self._list_canvas, bg=PANEL)
        self._list_window = self._list_canvas.create_window((0, 0), window=self.list_body, anchor="nw")

        self.list_body.bind("<Configure>", lambda _: self._list_canvas.configure(
            scrollregion=self._list_canvas.bbox("all")
        ))
        self._list_canvas.bind("<Configure>", lambda e: self._list_canvas.itemconfig(
            self._list_window, width=e.width
        ))

        self._empty_lbl = tk.Label(
            self.list_body, text="No hay pacientes cargados",
            bg=PANEL, fg=SOFT, font=FONT_ITALIC
        )

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
        body.pack(fill="both", expand=True, padx=10, pady=8)
        tk.Label(body, text=label, bg=PANEL, fg=MUTED, font=FONT_SM).pack(anchor="w")
        val = tk.Label(body, text=value, bg=PANEL, fg=FG, font=("Segoe UI", 16, "bold"))
        val.pack(anchor="w", pady=(2, 0))
        return {"frame": frame, "value": val}

    def _set_mode(self, mode):
        self.state.set_mode(mode)
        Toast(self.master, "Orden actualizado", BLUE)

    def _next_name(self):
        return f"Paciente {self.state.pid_counter}"

    def spawn_random(self):
        self.state.admitir(self._next_name(), random.randint(3, 8), random.randint(5, 12))

    def spawn_critical(self):
        self.state.admitir(self._next_name(), priority=1, burst=8)

    def spawn_many(self):
        for _ in range(8):
            self.spawn_random()

    def trigger_deadlock(self):
        self.state.deadlock_demo = True
        Toast(self.master, "Se activó la demostración de deadlock", RED)

    def resolve_deadlock(self):
        if not self.state.deadlock_active:
            return
        self.state.deadlock_resolve_now = True
        Toast(self.master, "Resolución solicitada", GREEN)

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
            pacientes = list(self.state.pacientes.values())
            owners = dict(self.state.resource_owner)
            mode = self.state.scheduler_mode
            tick = self.state.clock_tick
            ram_used = len(pacientes)
            ram_limit = self.state.ram_limit
            deadlock_on = self.state.deadlock_active
            deadlock_since = self.state.deadlock_since

        ready = [p for p in pacientes if p.state == "READY"]
        running = [p for p in pacientes if p.state == "RUNNING"]
        blocked = [p for p in pacientes if p.state == "BLOCKED"]

        self.card_wait["value"].config(text=str(len(ready)))
        self.card_run["value"].config(text=str(len(running)))
        self.card_block["value"].config(text=str(len(blocked)))

        # --- lista de pacientes: actualizar en lugar, sin destruir/recrear ---
        current_pids = {p.pid for p in pacientes}
        for pid in list(self._row_cache):
            if pid not in current_pids:
                self._row_cache.pop(pid)["frame"].destroy()

        self.list_count.config(text=f"{len(pacientes)} proceso(s)")

        if not pacientes:
            if not self._empty_lbl.winfo_ismapped():
                self._empty_lbl.pack(anchor="center", pady=28)
        else:
            if self._empty_lbl.winfo_ismapped():
                self._empty_lbl.pack_forget()
            sort_key = (lambda x: (x.priority, x.pid)) if mode == "PRIORITY" else (lambda x: x.pid)
            pacientes_ordenados = sorted(pacientes, key=sort_key)
            for p in pacientes_ordenados:
                if p.pid not in self._row_cache:
                    refs = self._build_row(self.list_body, p)
                    self._row_cache[p.pid] = refs
                else:
                    self._update_row(self._row_cache[p.pid], p)
            # re-empaquetar en orden correcto
            for p in pacientes_ordenados:
                self._row_cache[p.pid]["frame"].pack_forget()
            for p in pacientes_ordenados:
                self._row_cache[p.pid]["frame"].pack(fill="x", pady=3)

        # --- resource cards: update in place ---
        for key, label in [("QUIROFANO", "Quirófano"), ("CIRUJANO", "Cirujano")]:
            owner = owners.get(key)
            if key not in self._res_cache:
                refs = self._build_res_card(self.res_cards, label, owner)
                refs["frame"].pack(fill="x", pady=4)
                self._res_cache[key] = refs
            else:
                self._update_res_card(self._res_cache[key], owner)

        mode_label = "orden de llegada" if mode == "ROUNDROBIN" else "por gravedad"
        self.status_var.set(
            f"Triage: {mode_label}    │    Pacientes: {ram_used}/{ram_limit}    │    Tick: {tick}"
        )

        cycle = self.state.detect_deadlock()
        if deadlock_on and cycle:
            names = []
            with self.state.lock:
                for pid in cycle:
                    paciente = self.state.pacientes.get(pid)
                    if paciente:
                        names.append(paciente.name)

            remaining = None
            if deadlock_since is not None:
                remaining = max(0, 10 - int(time.time() - deadlock_since))

            if not self.deadlock_frame.winfo_ismapped():
                self.deadlock_frame.pack(fill="x", pady=(0, 8))

            countdown = f" — se resuelve automáticamente en {remaining}s" if remaining is not None else ""
            self.deadlock_title.config(text=f"Deadlock detectado{countdown}")

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
            if self.deadlock_frame.winfo_ismapped():
                self.deadlock_frame.pack_forget()

    # --- patient row helpers ---

    def _extra_text(self, paciente):
        if paciente.waiting_for:
            return f"Esperando: {paciente.waiting_for}"
        elif paciente.holding:
            return "Posee: " + ", ".join(paciente.holding)
        return "Sin recursos"

    def _state_colors(self, state):
        bg  = {"READY": "#dbeafe", "RUNNING": "#dcfce7", "BLOCKED": "#fee2e2"}.get(state, "#f1f5f9")
        fg  = {"READY": BLUE,      "RUNNING": GREEN,     "BLOCKED": RED      }.get(state, SOFT)
        return bg, fg

    def _build_row(self, parent, paciente):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)

        # right ANTES que left para que expand=True no lo aplaste
        right = tk.Frame(frame, bg=PANEL)
        right.pack(side="right", padx=10, pady=7)
        left = tk.Frame(frame, bg=PANEL)
        left.pack(side="left", fill="x", expand=True, padx=10, pady=7)

        sbg, sfg = self._state_colors(paciente.state)

        tk.Label(left, text=paciente.name, bg=PANEL, fg=FG, font=FONT_BOLD).pack(anchor="w")
        pid_lbl = tk.Label(left, text=f"ID {paciente.pid} · gravedad {paciente.priority}", bg=PANEL, fg=MUTED, font=FONT_SM)
        pid_lbl.pack(anchor="w", pady=(1, 0))

        state_lbl = tk.Label(right, text=f" {paciente.state} ", bg=sbg, fg=sfg,
                             font=("Segoe UI", 9, "bold"), padx=4, pady=1)
        state_lbl.pack(anchor="e")
        cpu_lbl = tk.Label(right, text=f"{paciente.cpu_used}/{paciente.burst} CPU", bg=PANEL, fg=MUTED, font=FONT_SM)
        cpu_lbl.pack(anchor="e", pady=(2, 0))

        extra_lbl = tk.Label(frame, text=self._extra_text(paciente), bg=PANEL, fg=SOFT, font=FONT_SM)
        extra_lbl.pack(anchor="w", padx=10, pady=(0, 6))

        return {"frame": frame, "pid_lbl": pid_lbl, "state_lbl": state_lbl, "cpu_lbl": cpu_lbl, "extra_lbl": extra_lbl}

    def _update_row(self, refs, paciente):
        sbg, sfg = self._state_colors(paciente.state)
        refs["state_lbl"].config(text=f" {paciente.state} ", bg=sbg, fg=sfg)
        refs["cpu_lbl"].config(text=f"{paciente.cpu_used}/{paciente.burst} CPU")
        refs["pid_lbl"].config(text=f"ID {paciente.pid} · gravedad {paciente.priority}")
        refs["extra_lbl"].config(text=self._extra_text(paciente))

    # --- resource card helpers ---

    def _res_status(self, owner):
        if owner is None:
            return "Libre", GREEN
        with self.state.lock:
            paciente = self.state.pacientes.get(owner)
            name = paciente.name if paciente else f"PID {owner}"
        return f"En uso por {name}", ORANGE

    def _build_res_card(self, parent, label, owner):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        bar = tk.Frame(frame, bg=GREEN if owner is None else ORANGE, height=4)
        bar.pack(fill="x")

        body = tk.Frame(frame, bg=PANEL)
        body.pack(fill="x", padx=10, pady=8)
        left = tk.Frame(body, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(left, text=label, bg=PANEL, fg=FG, font=FONT_BOLD).pack(anchor="w")
        status, color = self._res_status(owner)
        status_lbl = tk.Label(left, text=status, bg=PANEL, fg=color, font=FONT_SM)
        status_lbl.pack(anchor="w", pady=(2, 0))

        return {"frame": frame, "bar": bar, "status_lbl": status_lbl}

    def _update_res_card(self, refs, owner):
        status, color = self._res_status(owner)
        refs["status_lbl"].config(text=status, fg=color)
        refs["bar"].config(bg=GREEN if owner is None else ORANGE)
