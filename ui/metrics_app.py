import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *
from core.metrics import compute_metrics, list_alive, list_recent_completed


class MetricsApp(WindowBase):
    """
    Panel de métricas en vivo del scheduler.

    TODAS las cifras vienen de acumuladores reales: cada transición de
    estado de cada Paciente actualiza ready_acc/running_acc/blocked_acc.
    Esto NO promedia números inventados — es lo que de hecho pasó.

    Layout:
      - 4 KPI cards: Throughput, CPU utilization, Espera promedio, Respuesta promedio
      - Subfila: total de procesos vivos / terminados / modo de scheduling
      - Tabla 1: procesos vivos (incluye apps, marcadas con 🖥️)
      - Tabla 2: últimos 8 procesos terminados (pacientes Y apps)
    """

    BG = "#f8fbff"
    INK = "#102033"

    def __init__(self, master, state, x=120, y=80):
        super().__init__(master, "📊 Métricas del Sistema", PURPLE, 760, 600, x, y)
        self.state = state
        self.content.configure(bg=self.BG)

        self._alive_rows = {}
        self._done_rows = {}

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(header, text="Métricas del Sistema",
                 bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Estadísticas reales de scheduling sobre todos los procesos (pacientes y apps)",
            bg=self.BG, fg=SOFT, font=FONT_SM
        ).pack(anchor="w", pady=(2, 0))

        # KPI cards
        kpis = tk.Frame(self.content, bg=self.BG)
        kpis.pack(fill="x", padx=14, pady=(10, 4))

        self.kpi_thr = self._kpi(kpis, "Throughput", "—", "proc/s", BLUE)
        self.kpi_cpu = self._kpi(kpis, "CPU utilization", "—", "%", GREEN)
        self.kpi_wait = self._kpi(kpis, "Espera promedio", "—", "ms", ORANGE)
        self.kpi_resp = self._kpi(kpis, "Respuesta prom.", "—", "ms", PURPLE)

        sub = tk.Frame(self.content, bg=self.BG)
        sub.pack(fill="x", padx=14, pady=(4, 8))
        self.sub_alive = tk.Label(sub, text="—", bg=self.BG, fg=self.INK, font=FONT_BOLD)
        self.sub_alive.pack(side="left")
        tk.Label(sub, text="   ·   ", bg=self.BG, fg=SOFT, font=FONT_SM).pack(side="left")
        self.sub_done = tk.Label(sub, text="—", bg=self.BG, fg=self.INK, font=FONT_BOLD)
        self.sub_done.pack(side="left")
        tk.Label(sub, text="   ·   ", bg=self.BG, fg=SOFT, font=FONT_SM).pack(side="left")
        self.sub_turn = tk.Label(sub, text="—", bg=self.BG, fg=MUTED, font=FONT_SM)
        self.sub_turn.pack(side="left")
        self.sub_mode = tk.Label(sub, text="—", bg=self.BG, fg=BLUE, font=FONT_BOLD)
        self.sub_mode.pack(side="right")

        # Tabla de procesos vivos
        self._alive_section = self._table_section(
            self.content, "Procesos vivos", BLUE,
            cols=[
                ("PID", 6), ("Nombre", 18), ("Tipo", 9), ("Prio", 5),
                ("Estado", 9), ("CPU", 9), ("Espera", 9), ("Vida", 9),
            ]
        )

        # Tabla de procesos terminados (incluye apps cerradas)
        self._done_section = self._table_section(
            self.content, "Últimos procesos terminados", GREEN,
            cols=[
                ("PID", 6), ("Nombre", 16), ("Tipo", 9), ("Prio", 5),
                ("CPU", 9), ("Espera", 9), ("Respuesta", 10), ("Turnaround", 11),
            ]
        )

    def _kpi(self, parent, label, value, unit, color):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(side="left", expand=True, fill="x", padx=3)
        tk.Frame(frame, bg=color, height=4).pack(fill="x")
        body = tk.Frame(frame, bg=PANEL)
        body.pack(fill="both", expand=True, padx=10, pady=8)
        tk.Label(body, text=label, bg=PANEL, fg=MUTED, font=FONT_SM).pack(anchor="w")
        val = tk.Label(body, text=value, bg=PANEL, fg=self.INK, font=("Segoe UI", 16, "bold"))
        val.pack(anchor="w", pady=(2, 0))
        tk.Label(body, text=unit, bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")
        return {"value": val}

    def _table_section(self, parent, title, color, cols):
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        frame.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        tk.Frame(frame, bg=color, height=3).pack(fill="x")

        head = tk.Frame(frame, bg=PANEL)
        head.pack(fill="x", padx=10, pady=(6, 4))
        tk.Label(head, text=title, bg=PANEL, fg=self.INK, font=FONT_BOLD).pack(side="left")
        count = tk.Label(head, text="", bg=PANEL, fg=MUTED, font=FONT_SM)
        count.pack(side="right")

        col_head = tk.Frame(frame, bg=PANEL_3)
        col_head.pack(fill="x", padx=10)
        for name, width in cols:
            tk.Label(col_head, text=name, bg=PANEL_3, fg=MUTED,
                     font=("Segoe UI", 8, "bold"),
                     width=width, anchor="w").pack(side="left")

        body = tk.Frame(frame, bg=PANEL)
        body.pack(fill="both", expand=True, padx=10, pady=(2, 8))

        return {"frame": frame, "body": body, "count": count, "cols": cols}

    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return
        try:
            self._render()
        except Exception:
            pass
        if self.alive:
            self.frame.after(400, self.refresh)

    def _render(self):
        m = compute_metrics(self.state)

        self.kpi_thr["value"].config(text=f"{m.throughput:.2f}")
        self.kpi_cpu["value"].config(text=f"{m.cpu_utilization*100:.1f}")
        self.kpi_wait["value"].config(text=f"{m.avg_waiting_time*1000:.0f}")
        self.kpi_resp["value"].config(text=f"{m.avg_response_time*1000:.0f}")

        self.sub_alive.config(
            text=f"🟢 Vivos: {m.n_alive} (pacientes {m.n_alive_patients} · apps {m.n_alive_apps})"
        )
        self.sub_done.config(
            text=f"✓ Terminados: {m.n_completed} (pacientes {m.n_completed_patients} · apps {m.n_completed_apps})"
        )
        self.sub_turn.config(
            text=f"Turnaround prom.: {m.avg_turnaround_time*1000:.0f}ms"
        )
        mode_label = "Llegada (RR)" if m.scheduler_mode == "ROUNDROBIN" else "Gravedad"
        self.sub_mode.config(text=f"Modo: {mode_label}")

        self._sync_alive_rows(list_alive(self.state))
        self._sync_done_rows(list_recent_completed(self.state, limit=8))

    def _sync_alive_rows(self, snaps):
        body = self._alive_section["body"]
        current_pids = {s.pid for s in snaps}

        for pid in list(self._alive_rows):
            if pid not in current_pids:
                self._alive_rows.pop(pid)["frame"].destroy()

        for s in snaps:
            if s.pid not in self._alive_rows:
                self._alive_rows[s.pid] = self._make_row(
                    body, self._alive_section["cols"],
                    self._alive_row_values(s),
                    bg=PANEL_2 if s.kind == "app" else PANEL,
                )
            else:
                self._update_row(
                    self._alive_rows[s.pid],
                    self._alive_section["cols"],
                    self._alive_row_values(s),
                    bg=PANEL_2 if s.kind == "app" else PANEL,
                )

        # reordenar por PID
        for s in snaps:
            self._alive_rows[s.pid]["frame"].pack_forget()
        for s in snaps:
            self._alive_rows[s.pid]["frame"].pack(fill="x", pady=1)

        self._alive_section["count"].config(text=f"{len(snaps)} proceso(s)")

    def _alive_row_values(self, s):
        kind_label = "🖥️ app" if s.kind == "app" else "patient"
        return [
            str(s.pid),
            s.name[:18],
            kind_label,
            str(s.priority),
            s.state,
            f"{s.cpu_time*1000:.0f}ms",
            f"{s.waiting_time*1000:.0f}ms",
            f"{s.turnaround_time*1000:.0f}ms",
        ]

    def _sync_done_rows(self, snaps):
        body = self._done_section["body"]
        current_pids = {s.pid for s in snaps}

        for pid in list(self._done_rows):
            if pid not in current_pids:
                self._done_rows.pop(pid)["frame"].destroy()

        for s in snaps:
            if s.pid not in self._done_rows:
                self._done_rows[s.pid] = self._make_row(
                    body, self._done_section["cols"],
                    self._done_row_values(s),
                    bg=PANEL_2 if s.kind == "app" else PANEL,
                )
            else:
                self._update_row(
                    self._done_rows[s.pid],
                    self._done_section["cols"],
                    self._done_row_values(s),
                    bg=PANEL_2 if s.kind == "app" else PANEL,
                )

        # snaps ya viene ordenado: más reciente primero
        for s in snaps:
            self._done_rows[s.pid]["frame"].pack_forget()
        for s in snaps:
            self._done_rows[s.pid]["frame"].pack(fill="x", pady=1)

        self._done_section["count"].config(text=f"últimos {len(snaps)}")

    def _done_row_values(self, s):
        kind_label = "🖥️ app" if s.kind == "app" else "patient"
        return [
            str(s.pid),
            s.name[:16],
            kind_label,
            str(s.priority),
            f"{s.cpu_time*1000:.0f}ms",
            f"{s.waiting_time*1000:.0f}ms",
            f"{s.response_time*1000:.0f}ms",
            f"{s.turnaround_time*1000:.0f}ms",
        ]

    def _make_row(self, parent, cols, values, bg):
        frame = tk.Frame(parent, bg=bg)
        labels = []
        for (name, width), val in zip(cols, values):
            l = tk.Label(frame, text=val, bg=bg, fg=self.INK,
                         font=FONT_SM, width=width, anchor="w")
            l.pack(side="left")
            labels.append(l)
        return {"frame": frame, "labels": labels}

    def _update_row(self, refs, cols, values, bg):
        try:
            refs["frame"].config(bg=bg)
            for l, val in zip(refs["labels"], values):
                l.config(text=val, bg=bg)
        except Exception:
            pass