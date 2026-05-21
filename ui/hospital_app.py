import tkinter as tk
import random
from ui.window_base import WindowBase
from ui.theme import *
from ui.toast import Toast


class HospitalApp(WindowBase):
    """
    Simulador de SO con metáfora de hospital.
    Diseño refinado: paleta clínica, jerarquía visual clara,
    tarjetas con sombra suave, badges de gravedad.
    """

    # ─── paleta interna específica ───
    BG          = "#f7fafc"
    INK         = "#0f1e35"
    SOFT_INK    = "#5c6b7f"
    SUB_INK     = "#8b97a8"
    DIVIDER     = "#e1e8f0"

    # estados
    READY_BG    = "#eff6ff"
    READY_BORD  = "#3b82f6"
    READY_HEAD  = "#2563eb"

    RUN_BG      = "#dcfce7"
    RUN_BORD    = "#16a34a"
    RUN_HEAD    = "#15803d"
    DOCTOR_IDLE = "#f1f5f9"

    BLOCK_BG    = "#fef2f2"
    BLOCK_BORD  = "#ef4444"
    BLOCK_HEAD  = "#b91c1c"

    RES_FREE_BG = "#ecfdf5"
    RES_FREE_BD = "#10b981"
    RES_BUSY_BG = "#fffbeb"
    RES_BUSY_BD = "#f59e0b"

    # badges por gravedad
    def severity(self, prio):
        if prio <= 2:  return ("🚨", "CRÍTICO",  "#dc2626", "#fee2e2")
        if prio <= 5:  return ("🤕", "GRAVE",    "#ea580c", "#ffedd5")
        return         ("🤒", "LEVE",     "#16a34a", "#dcfce7")

    def __init__(self, master, state, x=10, y=40):
        super().__init__(master, "🏥  Hospital MS — Merecemos Sobresaliente",
                         BLUE, 800, 625, x, y)
        self.state = state
        self._patient_counter = 0
        self._blink = 0
        # forzar fondo blanco del content
        self.content.configure(bg=self.BG)

        # ─── header con leyenda ───
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=14, pady=(14, 6))

        tk.Label(header, text="Panel de operaciones",
                 bg=self.BG, fg=self.INK, font=FONT_BIG
                 ).pack(side="left")
        tk.Label(header,
                 text="  ·  pacientes = procesos  ·  doctores = CPUs  "
                      "·  quirófano + cirujano = recursos compartidos",
                 bg=self.BG, fg=self.SUB_INK, font=FONT_ITALIC
                 ).pack(side="left")

        # ─── barra de acciones (fila 1: pacientes y scheduling) ───
        bar = tk.Frame(self.content, bg=self.BG)
        bar.pack(fill="x", padx=14, pady=(0, 4))

        self._mk_btn(bar, "➕  Admitir paciente",   BLUE,    self.spawn_random)
        self._mk_btn(bar, "🚨  Caso crítico",        RED,     self.spawn_critical)
        self._mk_btn(bar, "👥  Llegan 8",            CYAN,    self.spawn_many)

        self._sep(bar)

        tk.Label(bar, text="Ordenar por:", bg=self.BG, fg=self.SOFT_INK,
                 font=FONT).pack(side="left", padx=(0, 6))
        self._mk_btn(bar, "Orden de llegada",   "#475569",  lambda: self._set_mode("ROUNDROBIN"))
        self._mk_btn(bar, "Por gravedad",       PURPLE,     lambda: self._set_mode("PRIORITY"))

        # ─── barra de acciones (fila 2: deadlock) ───
        bar2 = tk.Frame(self.content, bg=self.BG)
        bar2.pack(fill="x", padx=14, pady=(0, 10))

        self._mk_btn(bar2, "⚠️  Provocar deadlock",  RED,    self.trigger_deadlock)
        self._mk_btn(bar2, "✅  Resolver deadlock",  GREEN,  self.resolve_deadlock)

        # ─── canvas principal ───
        self.canvas = tk.Canvas(
            self.content, bg=self.BG,
            highlightthickness=0, bd=0
        )
        self.canvas.pack(fill="both", expand=True, padx=14, pady=(0, 4))

        # ─── pie de status ───
        footer = tk.Frame(self.content, bg=self.BG)
        footer.pack(fill="x", padx=14, pady=(2, 10))
        self.status_var = tk.StringVar(value="")
        tk.Label(footer, textvariable=self.status_var,
                 bg=self.BG, fg=self.SOFT_INK, font=FONT_SM, anchor="w"
                 ).pack(fill="x")

        self.refresh()

    # ─── helpers UI ───

    def _sep(self, parent):
        tk.Frame(parent, bg=self.BG, width=16).pack(side="left")

    def _mk_btn(self, parent, text, color, cmd):
        b = tk.Button(parent, text=text, bg=color, fg="white",
                      relief="flat", bd=0, padx=12, pady=7,
                      font=FONT_BOLD, cursor="hand2",
                      activebackground=color, activeforeground="white",
                      command=cmd)
        b.pack(side="left", padx=3)
        return b

    def _set_mode(self, mode):
        self.state.set_mode(mode)
        label = "orden de llegada" if mode == "ROUNDROBIN" else "por gravedad"
        Toast(self.master, f"Atendiendo {label}", BLUE)

    def _next_name(self):
        self._patient_counter += 1
        return f"Paciente {self._patient_counter}"

    # ─── acciones ───

    def spawn_random(self):
        prio = random.randint(3, 8)
        burst = random.randint(5, 12)
        self.state.add_hero(self._next_name(), prio, burst)

    def spawn_critical(self):
        self.state.add_hero(self._next_name(), priority=1, burst=8)

    def spawn_many(self):
        for _ in range(8):
            self.spawn_random()

    def trigger_deadlock(self):
        self.state.deadlock_demo = True
        Toast(self.master,
              "Dos pacientes pelearán por Quirófano + Cirujano", RED)

    def resolve_deadlock(self):
        self.state.deadlock_resolve_now = True
        if self.state.deadlock_active:
            Toast(self.master, "Derivando paciente menos grave...", GREEN)
        else:
            Toast(self.master, "Resolución programada (esperando deadlock)", "#64748b")

    # ─── render ───

    def refresh(self):
        if not self.alive:
            return
        try:
            if not self.frame.winfo_exists():
                return
        except Exception:
            return

        try:
            self._do_refresh()
        except Exception:
            pass

        if self.alive:
            self.frame.after(120, self.refresh)

    def _do_refresh(self):
        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 960
        H = c.winfo_height() or 540

        with self.state.lock:
            heroes = list(self.state.heroes.values())
            owners = dict(self.state.resource_owner)
            waiters = {k: list(v) for k, v in self.state.resource_waiters.items()}
            mode = self.state.scheduler_mode
            num_cpus = self.state.num_cpus
            tick = self.state.clock_tick
            ram_used = len(heroes)
            ram_limit = self.state.ram_limit
            deadlock_on = self.state.deadlock_active

        ready   = [h for h in heroes if h.state == "READY"]
        running = [h for h in heroes if h.state == "RUNNING"]
        blocked = [h for h in heroes if h.state == "BLOCKED"]

        if mode == "PRIORITY":
            ready.sort(key=lambda h: h.priority)

        # ─── 3 columnas ───
        gap = 12
        col_w = (W - 2 * gap) // 3
        col_x = [0, col_w + gap, 2 * (col_w + gap)]

        # tarjeta-contenedor por columna (fondo blanco con borde suave)
        for x in col_x:
            self._card_bg(c, x, 0, col_w, H - 200)

        # headers
        self._col_header(c, col_x[0], 0, col_w,
                         "🪑", "SALA DE ESPERA",
                         f"{len(ready)} en espera", self.READY_HEAD)
        self._col_header(c, col_x[1], 0, col_w,
                         "👨‍⚕️", "CONSULTORIOS",
                         f"{len(running)}/{num_cpus} ocupados", self.RUN_HEAD)
        self._col_header(c, col_x[2], 0, col_w,
                         "⏸️", "ESPERANDO RECURSO",
                         f"{len(blocked)} bloqueados", self.BLOCK_HEAD)

        # ─── columna 1: sala de espera ───
        y = 64
        for h in ready[:10]:
            self._patient_card(c, col_x[0] + 10, y, col_w - 20, h,
                               accent=self.READY_BORD)
            y += 44
        if len(ready) > 10:
            c.create_text(col_x[0] + col_w // 2, y + 4,
                          text=f"+ {len(ready) - 10} pacientes más",
                          fill=self.SUB_INK, font=FONT_ITALIC)
        if not ready:
            c.create_text(col_x[0] + col_w // 2, 100,
                          text="(sala vacía)",
                          fill=self.SUB_INK, font=FONT_ITALIC)

        # ─── columna 2: consultorios ───
        ry = 64
        room_h = 100
        for i in range(num_cpus):
            self._consultorio(c, col_x[1] + 10, ry, col_w - 20, room_h,
                              i + 1,
                              running[i] if i < len(running) else None)
            ry += room_h + 10

        # ─── columna 3: bloqueados ───
        y = 64
        for h in blocked[:10]:
            extra = f"esperando {self._res_label(h.waiting_for)}" if h.waiting_for else ""
            self._patient_card(c, col_x[2] + 10, y, col_w - 20, h,
                               accent=self.BLOCK_BORD, sub=extra)
            y += 44
        if not blocked:
            c.create_text(col_x[2] + col_w // 2, 100,
                          text="(nadie bloqueado)",
                          fill=self.SUB_INK, font=FONT_ITALIC)

        # ─── sección recursos ───
        section_y = H - 180
        c.create_text(0, section_y - 12, anchor="nw",
                      text="🔒  RECURSOS COMPARTIDOS",
                      fill=self.INK, font=FONT_BIG)
        c.create_text(W, section_y - 12, anchor="ne",
                      text="cada recurso lo usa un paciente a la vez (mutex)",
                      fill=self.SUB_INK, font=FONT_ITALIC)

        res_meta = {
            "QUIROFANO": ("🏥", "Quirófano"),
            "CIRUJANO":  ("👨‍⚕️", "Cirujano especialista"),
        }
        n_res = max(len(owners), 1)
        res_gap = 12
        res_w = (W - (n_res - 1) * res_gap) // n_res
        for i, (res_key, owner) in enumerate(owners.items()):
            icon, label = res_meta.get(res_key, ("🔒", res_key))
            x0 = i * (res_w + res_gap)
            self._resource_card(c, x0, section_y + 18,
                                res_w, H - section_y - 24,
                                icon, label, res_key, owner,
                                waiters[res_key])

        # ─── cartel deadlock ───
        if deadlock_on:
            self._blink = (self._blink + 1) % 10
            self._deadlock_banner(c, W, H)

        # ─── status bar ───
        mode_label = "orden de llegada" if mode == "ROUNDROBIN" else "por gravedad"
        self.status_var.set(
            f"Atención: {mode_label}    │    "
            f"Pacientes: {ram_used}/{ram_limit}    │    "
            f"Tick: {tick}"
        )

    # ─── primitivas de dibujo ───

    def _card_bg(self, c, x, y, w, h):
        # sombra suave
        c.create_rectangle(x + 2, y + 4, x + w + 2, y + h + 4,
                           fill="#dde6f1", outline="")
        c.create_rectangle(x, y, x + w, y + h,
                           fill=PANEL, outline=self.DIVIDER, width=1)

    def _col_header(self, c, x, y, w, icon, title, sub, color):
        c.create_rectangle(x, y, x + w, y + 50, fill=color, outline="")
        c.create_text(x + 14, y + 16, anchor="w",
                      text=icon, font=("Apple Color Emoji", 16))
        c.create_text(x + 40, y + 12, anchor="nw",
                      text=title, fill="white", font=FONT_BIG)
        c.create_text(x + 40, y + 30, anchor="nw",
                      text=sub, fill="#dbeafe", font=FONT_SM)

    def _patient_card(self, c, x, y, w, hero, accent, sub=None):
        # tarjeta blanca con barra lateral del color del estado
        c.create_rectangle(x, y, x + w, y + 38,
                           fill="white", outline=self.DIVIDER)
        c.create_rectangle(x, y, x + 4, y + 38, fill=accent, outline="")

        icon, sev_label, sev_fg, sev_bg = self.severity(hero.priority)

        # icono paciente
        c.create_text(x + 22, y + 19, text=icon,
                      font=("Apple Color Emoji", 18))
        # nombre
        c.create_text(x + 42, y + 9, anchor="nw",
                      text=hero.name, fill=self.INK, font=FONT_BOLD)
        # subtítulo: gravedad o estado de espera
        sub_text = sub if sub else f"gravedad {hero.priority}"
        c.create_text(x + 42, y + 22, anchor="nw",
                      text=sub_text, fill=self.SOFT_INK, font=FONT_SM)

        # badge de gravedad a la derecha
        badge_w = 64
        bx0 = x + w - badge_w - 8
        bx1 = x + w - 8
        c.create_rectangle(bx0, y + 10, bx1, y + 28,
                           fill=sev_bg, outline=sev_fg, width=1)
        c.create_text((bx0 + bx1) // 2, y + 19,
                      text=sev_label, fill=sev_fg, font=("Aptos", 8, "bold"))

    def _consultorio(self, c, x, y, w, h, num, hero):
        # contenedor
        c.create_rectangle(x, y, x + w, y + h,
                           fill=self.RUN_BG if hero else self.DOCTOR_IDLE,
                           outline=self.RUN_BORD if hero else self.DIVIDER,
                           width=1)
        # cinta de número arriba
        c.create_rectangle(x, y, x + w, y + 22,
                           fill=self.RUN_HEAD if hero else "#cbd5e1",
                           outline="")
        c.create_text(x + 10, y + 11, anchor="w",
                      text=f"Consultorio #{num}",
                      fill="white", font=("Aptos", 9, "bold"))

        if hero:
            # icono grande
            icon, _, _, _ = self.severity(hero.priority)
            c.create_text(x + 30, y + 56,
                          text=icon, font=("Apple Color Emoji", 26))
            # nombre
            c.create_text(x + 60, y + 38, anchor="nw",
                          text=hero.name, fill="#064e3b", font=FONT_BOLD)
            c.create_text(x + 60, y + 52, anchor="nw",
                          text=f"gravedad {hero.priority}",
                          fill="#166534", font=FONT_SM)
            # barra de atención
            pb_x0 = x + 60
            pb_x1 = x + w - 12
            pb_y  = y + 76
            c.create_rectangle(pb_x0, pb_y, pb_x1, pb_y + 8,
                               fill="#bbf7d0", outline="")
            frac = hero.cpu_used / max(hero.burst, 1)
            c.create_rectangle(pb_x0, pb_y,
                               pb_x0 + (pb_x1 - pb_x0) * frac,
                               pb_y + 8,
                               fill="#16a34a", outline="")
            c.create_text(pb_x1, pb_y + 20, anchor="e",
                          text=f"{hero.cpu_used}/{hero.burst}",
                          fill="#166534", font=FONT_SM)
        else:
            c.create_text(x + w // 2, y + h // 2 + 4,
                          text="💤  Doctor libre",
                          fill=self.SUB_INK, font=FONT_ITALIC)

    def _resource_card(self, c, x, y, w, h, icon, label, key, owner, waiters):
        free = owner is None
        bg = self.RES_FREE_BG if free else self.RES_BUSY_BG
        bd = self.RES_FREE_BD if free else self.RES_BUSY_BD
        # sombra
        c.create_rectangle(x + 2, y + 4, x + w + 2, y + h + 4,
                           fill="#dde6f1", outline="")
        c.create_rectangle(x, y, x + w, y + h,
                           fill=bg, outline=bd, width=2)
        # icono
        c.create_text(x + 18, y + 22, anchor="nw",
                      text=icon, font=("Apple Color Emoji", 24))
        # título
        c.create_text(x + 62, y + 16, anchor="nw",
                      text=label, fill=self.INK, font=FONT_BIG)

        # status
        if free:
            status_text = "✅  LIBRE"
            status_color = "#15803d"
        else:
            owner_name = ""
            with self.state.lock:
                hh = self.state.heroes.get(owner)
                if hh:
                    owner_name = hh.name
            status_text = f"🔴  EN USO  ·  {owner_name or f'PID {owner}'}"
            status_color = "#b45309"
        c.create_text(x + 62, y + 42, anchor="nw",
                      text=status_text,
                      fill=status_color, font=FONT_BOLD)

        # cola
        if waiters:
            names = []
            with self.state.lock:
                for p in waiters:
                    hh = self.state.heroes.get(p)
                    if hh:
                        names.append(hh.name)
            wait_text = "⏳  Cola: " + ", ".join(names)
        else:
            wait_text = "⏳  Sin cola"
        c.create_text(x + 18, y + h - 18, anchor="w",
                      text=wait_text, fill=self.SOFT_INK, font=FONT_SM)

    def _deadlock_banner(self, c, W, H):
        color = "#dc2626" if self._blink < 5 else "#991b1b"
        box_w = 540
        box_h = 130
        bx = (W - box_w) // 2
        by = (H - box_h) // 2
        # sombra fuerte
        c.create_rectangle(bx - 6, by - 6, bx + box_w + 6, by + box_h + 6,
                           fill="#1f2937", outline="")
        c.create_rectangle(bx, by, bx + box_w, by + box_h,
                           fill=color, outline="white", width=3)
        c.create_text(bx + box_w // 2, by + 32,
                      text="⚠️  DEADLOCK DETECTADO",
                      fill="white", font=FONT_DISPLAY)
        c.create_text(bx + box_w // 2, by + 64,
                      text="Dos pacientes se bloquean mutuamente",
                      fill="#fee2e2", font=FONT_MD)
        c.create_text(bx + box_w // 2, by + 92,
                      text="Tocá 'Resolver deadlock' o esperá 10 segundos",
                      fill="#fecaca", font=FONT_ITALIC)

    def _res_label(self, key):
        return {"QUIROFANO": "Quirófano",
                "CIRUJANO":  "Cirujano"}.get(key, key)