import tkinter as tk
import threading
import random
import time
from ui.window_base import WindowBase
from ui.theme import *

DOCTOR_NAMES = [
    "Dr. García", "Dra. López", "Dr. Martín", "Dra. Torres",
    "Dr. Ramírez", "Dra. Vega", "Dr. Ruiz", "Dra. Castro",
    "Dr. Sosa",   "Dra. Reyes",
]
NURSE_NAMES = [
    "Enf. Díaz", "Enf. Mora", "Enf. Silva",
    "Enf. Perez", "Enf. Gómez", "Enf. Cruz",
]
ENTRIES = [
    "Temp: 36.8°C · PA: 120/80 · FC: 72 bpm · Sin novedades",
    "Temp: 37.2°C · PA: 130/85 · FC: 88 bpm · Observación",
    "Temp: 36.5°C · PA: 118/76 · FC: 65 bpm · Alta próxima",
    "Temp: 38.1°C · PA: 145/92 · FC: 95 bpm · Medicación ajustada",
    "Temp: 36.9°C · PA: 122/78 · FC: 70 bpm · Estable",
    "Temp: 37.5°C · PA: 135/88 · FC: 80 bpm · En observación",
]


class ReadersApp(WindowBase):
    """
    Historia Clínica — Lectores y Escritores con procesos reales.

    Cada lector y cada escritor que llega es un proceso del sistema:
    se registra (admitir), pasa a BLOCKED mientras espera el lock,
    pasa a READY cuando lo obtiene, hace su trabajo (sleep que
    representa la lectura/escritura) y se da de alta. Toda la
    sincronización (Courtois) está en core/state.py — esta ventana
    es solo la cara visible.
    """

    APP_NAME = "Historia Clínica"
    APP_PRIORITY = 7

    BG = "#f8fbff"
    INK = "#102033"

    def __init__(self, master, state, x=80, y=60):
        super().__init__(
            master, "Historia Clínica — Lectores y Escritores",
            GREEN, 880, 580, x, y,
        )
        self.state = state
        self.content.configure(bg=self.BG)

        # Registrar la VENTANA como proceso padre
        self._app_paciente = None
        if state is not None:
            self._app_paciente = state.admitir(
                self.APP_NAME,
                priority=self.APP_PRIORITY,
                burst=999_999_999,
                kind="app",
            )

        # Caches de cards para evitar flicker
        self._reader_cards: dict[int, dict] = {}
        self._writer_waiting_cards: dict[int, dict] = {}
        self._active_writer_card: dict | None = None
        self._readers_empty_lbl: tk.Label | None = None
        self._writers_empty_lbl: tk.Label | None = None

        self._build_ui()
        self.refresh()
        # Arranca con una enfermera escribiendo para mostrar la espera
        self.frame.after(400, self._spawn_writer)

    def on_close(self):
        if self._app_paciente is not None:
            try:
                self.state.dar_alta(self._app_paciente.pid)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  UI
    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(header, text="Historia Clínica",
                 bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Cada lector y escritor es un proceso real del sistema · "
                 "varios médicos pueden leer a la vez · solo una enfermera "
                 "puede escribir",
            bg=self.BG, fg=SOFT, font=FONT_SM,
        ).pack(anchor="w", pady=(2, 0))

        btns = tk.Frame(self.content, bg=self.BG)
        btns.pack(fill="x", padx=16, pady=(8, 10))
        self._btn(btns, "👨‍⚕️  Médico llega a leer", GREEN, self._spawn_reader)
        self._btn(btns, "👩‍⚕️  Enfermera llega a escribir", ORANGE,
                  self._spawn_writer)

        body = tk.Frame(self.content, bg=self.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # ── izquierda: lectores ──
        left = tk.Frame(body, bg=self.BG, width=210)
        left.pack_propagate(False)
        left.pack(side="left", fill="y", padx=(0, 12))
        self._column_header(left, "Leyendo ahora", "pueden ser varios", GREEN)
        self._readers_panel = tk.Frame(left, bg=self.BG)
        self._readers_panel.pack(fill="both", expand=True, pady=(8, 0))

        # ── derecha: escritoras ──
        right = tk.Frame(body, bg=self.BG, width=210)
        right.pack_propagate(False)
        right.pack(side="right", fill="y", padx=(12, 0))
        self._column_header(right, "Escribiendo / en cola",
                            "una a la vez", ORANGE)
        self._writers_panel = tk.Frame(right, bg=self.BG)
        self._writers_panel.pack(fill="both", expand=True, pady=(8, 0))

        # ── centro: registro ──
        center = tk.Frame(body, bg=PANEL,
                          highlightthickness=1, highlightbackground=BORDER)
        center.pack(side="left", fill="both", expand=True)

        self._center_bar = tk.Frame(center, bg=GREEN, height=4)
        self._center_bar.pack(fill="x")

        inner = tk.Frame(center, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(inner, text="REGISTRO COMPARTIDO",
                 bg=PANEL, fg=SOFT, font=("Segoe UI", 9, "bold")
                 ).pack(anchor="w")

        self._status_lbl = tk.Label(
            inner, text="LIBRE",
            bg="#f0fdf4", fg=GREEN,
            font=("Segoe UI", 10, "bold"),
            padx=12, pady=5,
        )
        self._status_lbl.pack(anchor="w", pady=(6, 10))

        tk.Label(inner, text="Último registro",
                 bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")
        self._record_lbl = tk.Label(
            inner, text="", bg=PANEL, fg=self.INK,
            font=("Consolas", 10, "bold"),
            wraplength=330, justify="left",
        )
        self._record_lbl.pack(anchor="w", pady=(4, 14))

        tk.Label(inner, text="Historial de cambios",
                 bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")
        self._history_box = tk.Text(
            inner, bg=PANEL_2, fg=MUTED, font=("Consolas", 9),
            relief="flat", highlightthickness=1,
            highlightbackground=BORDER_SOFT,
            state="disabled", height=8,
        )
        self._history_box.pack(fill="both", expand=True, pady=(4, 0))

    def _column_header(self, parent, title, subtitle, accent):
        h = tk.Frame(parent, bg=self.BG)
        h.pack(fill="x")
        bar = tk.Frame(h, bg=accent, width=3)
        bar.pack(side="left", fill="y", padx=(0, 8))
        body = tk.Frame(h, bg=self.BG)
        body.pack(side="left", fill="x", expand=True)
        tk.Label(body, text=title, bg=self.BG, fg=self.INK,
                 font=FONT_BOLD).pack(anchor="w")
        tk.Label(body, text=subtitle, bg=self.BG, fg=SOFT,
                 font=FONT_SM).pack(anchor="w", pady=(1, 0))

    def _btn(self, parent, text, color, cmd):
        tk.Button(
            parent, text=text, bg=color, fg="white",
            relief="flat", bd=0, padx=14, pady=8,
            font=FONT_BOLD, cursor="hand2",
            activebackground=color, activeforeground="white",
            command=cmd,
        ).pack(side="left", padx=(0, 8))

    # ─────────────────────────────────────────────────────────────────
    #  Acciones — cada llegada lanza un PROCESO
    # ─────────────────────────────────────────────────────────────────
    def _spawn_reader(self):
        name = random.choice(DOCTOR_NAMES)
        threading.Thread(target=self._reader_process,
                         args=(name,), daemon=True).start()

    def _spawn_writer(self):
        name = random.choice(NURSE_NAMES)
        threading.Thread(target=self._writer_process,
                         args=(name,), daemon=True).start()

    def _reader_process(self, name: str):
        """Un lector = un proceso completo: nace, espera lock, lee, muere."""
        p = self.state.admitir(f"📖 {name}", priority=6, burst=4, kind="app")
        if p is None:
            return
        pid = p.pid

        # Pequeña pausa de "llegada" antes de pedir el lock
        time.sleep(1.0)

        # Pide acceso de lectura (puede bloquearse si hay escritor)
        if self.state.historia_start_read(pid):
            # Tiempo de consulta
            time.sleep(random.uniform(3.0, 5.0))
            self.state.historia_end_read(pid)

        try:
            self.state.dar_alta(pid)
        except Exception:
            pass

    def _writer_process(self, name: str):
        """Un escritor = un proceso completo: nace, espera exclusivo, escribe, muere."""
        p = self.state.admitir(f"📝 {name}", priority=5, burst=5, kind="app")
        if p is None:
            return
        pid = p.pid

        time.sleep(1.0)

        if self.state.historia_start_write(pid):
            # Tiempo de escritura
            time.sleep(random.uniform(3.5, 5.5))
            new_entry = random.choice(ENTRIES)
            self.state.historia_end_write(pid, new_entry)

        try:
            self.state.dar_alta(pid)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  Refresh loop
    # ─────────────────────────────────────────────────────────────────
    def refresh(self):
        if not self.alive:
            return
        try:
            self._render()
        except Exception:
            pass
        if self.alive:
            self.frame.after(180, self.refresh)

    def _render(self):
        # Snapshot bajo el lock central del state
        with self.state.lock:
            active_readers = dict(self.state.historia_active_readers)
            active_writer = self.state.historia_active_writer
            waiting_writers = dict(self.state.historia_waiting_writers)
            record = self.state.historia_record
            history = list(self.state.historia_history)

        # ── Estado central ──
        if active_writer:
            self._status_lbl.config(text=f"ESCRIBIENDO · {active_writer}",
                                    bg="#fef2f2", fg=RED)
            self._center_bar.config(bg=RED)
        elif active_readers:
            n = len(active_readers)
            self._status_lbl.config(
                text=f"LEYENDO · {n} {'médico' if n == 1 else 'médicos'}",
                bg="#f0fdf4", fg=GREEN,
            )
            self._center_bar.config(bg=GREEN)
        else:
            self._status_lbl.config(text="LIBRE", bg="#f1f5f9", fg=SOFT)
            self._center_bar.config(bg=BORDER)

        self._record_lbl.config(text=record or "(sin registro)")

        self._history_box.config(state="normal")
        self._history_box.delete("1.0", tk.END)
        for line in history:
            self._history_box.insert(tk.END, f"{line}\n")
        self._history_box.see(tk.END)
        self._history_box.config(state="disabled")

        # ── paneles izq/der ──
        # Para los lectores también mostramos los que están esperando
        # (waiting): los identificamos como procesos en BLOCKED cuyo
        # nombre arranca con "📖" y que no están en active_readers.
        all_readers = self._collect_pending_readers(active_readers)
        self._sync_reader_cards(all_readers)
        self._sync_writer_cards(active_writer, waiting_writers)

    def _collect_pending_readers(self, active_readers: dict) -> dict:
        """
        Devuelve un dict pid→{name, state} con los lectores ACTIVOS y los
        que están ESPERANDO (procesos cuyo nombre arranca con "📖" y que
        están en BLOCKED, no incluidos ya en active_readers).
        """
        result = {pid: {"name": name, "state": "leyendo"}
                  for pid, name in active_readers.items()}

        with self.state.lock:
            for pid, p in self.state.pacientes.items():
                if (p.kind == "app"
                        and p.name.startswith("📖 ")
                        and p.state == "BLOCKED"
                        and pid not in result):
                    # Quitar el emoji para mostrar nombre limpio
                    display_name = p.name[2:].strip()
                    result[pid] = {"name": display_name, "state": "esperando"}
        return result

    # ─────────────────────────────────────────────────────────────────
    #  Cards (sin flicker)
    # ─────────────────────────────────────────────────────────────────
    def _sync_reader_cards(self, readers: dict):
        current_pids = set(readers.keys())

        for pid in list(self._reader_cards.keys()):
            if pid not in current_pids:
                try:
                    self._reader_cards[pid]["frame"].destroy()
                except Exception:
                    pass
                del self._reader_cards[pid]

        for pid, info in readers.items():
            name = info["name"]
            is_reading = info["state"] == "leyendo"
            if is_reading:
                bg, accent = "#f0fdf4", GREEN
                subtitle, sub_color = "Leyendo...", GREEN
                border = "#bbf7d0"
            else:
                bg, accent = PANEL_2, SOFT
                subtitle, sub_color = "Esperando turno...", SOFT
                border = BORDER

            if pid not in self._reader_cards:
                self._reader_cards[pid] = self._build_card(
                    self._readers_panel, name, subtitle, bg, sub_color,
                    border, accent,
                )
            else:
                self._update_card(self._reader_cards[pid], name, subtitle,
                                  bg, sub_color, border, accent)

        order = sorted(self._reader_cards.keys(),
                       key=lambda p: (0 if readers[p]["state"] == "leyendo"
                                      else 1, p))
        for pid in order:
            self._reader_cards[pid]["frame"].pack_forget()
        for pid in order:
            self._reader_cards[pid]["frame"].pack(fill="x", pady=3)

        self._toggle_empty_label("readers", len(readers) == 0,
                                  "Nadie consultando")

    def _sync_writer_cards(self, active_writer: str | None, waiters: dict):
        # activa
        if active_writer is None:
            if self._active_writer_card is not None:
                try:
                    self._active_writer_card["frame"].destroy()
                except Exception:
                    pass
                self._active_writer_card = None
        else:
            display = active_writer.replace("📝 ", "")
            if self._active_writer_card is None:
                self._active_writer_card = self._build_card(
                    self._writers_panel, display, "Escribiendo...",
                    "#fef2f2", RED, "#fca5a5", RED,
                )
            else:
                self._update_card(self._active_writer_card, display,
                                  "Escribiendo...", "#fef2f2", RED,
                                  "#fca5a5", RED)

        # en espera
        current_pids = set(waiters.keys())
        for pid in list(self._writer_waiting_cards.keys()):
            if pid not in current_pids:
                try:
                    self._writer_waiting_cards[pid]["frame"].destroy()
                except Exception:
                    pass
                del self._writer_waiting_cards[pid]

        for pid, name in waiters.items():
            display = name.replace("📝 ", "")
            if pid not in self._writer_waiting_cards:
                self._writer_waiting_cards[pid] = self._build_card(
                    self._writers_panel, display, "Esperando su turno...",
                    "#fff7ed", ORANGE, "#fed7aa", ORANGE,
                )
            else:
                self._update_card(self._writer_waiting_cards[pid], display,
                                  "Esperando su turno...", "#fff7ed", ORANGE,
                                  "#fed7aa", ORANGE)

        if self._active_writer_card is not None:
            self._active_writer_card["frame"].pack_forget()
            self._active_writer_card["frame"].pack(fill="x", pady=3)
        for pid in sorted(self._writer_waiting_cards.keys()):
            self._writer_waiting_cards[pid]["frame"].pack_forget()
            self._writer_waiting_cards[pid]["frame"].pack(fill="x", pady=3)

        empty = active_writer is None and not waiters
        self._toggle_empty_label("writers", empty, "Nadie en cola")

    def _toggle_empty_label(self, which: str, show: bool, text: str):
        attr = f"_{which}_empty_lbl"
        panel = self._readers_panel if which == "readers" else self._writers_panel
        current = getattr(self, attr)
        if show:
            if current is None or not current.winfo_exists():
                lbl = tk.Label(panel, text=text, bg=self.BG, fg=SOFT,
                               font=FONT_ITALIC)
                lbl.pack(anchor="w", pady=10)
                setattr(self, attr, lbl)
        else:
            if current is not None:
                try:
                    current.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

    def _build_card(self, parent, name, subtitle, bg, sub_color, border, accent):
        frame = tk.Frame(parent, bg=bg,
                         highlightthickness=1, highlightbackground=border)
        bar = tk.Frame(frame, bg=accent, width=3)
        bar.pack(side="left", fill="y")
        body = tk.Frame(frame, bg=bg)
        body.pack(side="left", fill="both", expand=True, padx=10, pady=7)
        name_lbl = tk.Label(body, text=name, bg=bg, fg=self.INK,
                            font=FONT_BOLD)
        name_lbl.pack(anchor="w")
        sub_lbl = tk.Label(body, text=subtitle, bg=bg, fg=sub_color,
                           font=FONT_SM)
        sub_lbl.pack(anchor="w", pady=(2, 0))
        return {
            "frame": frame, "bar": bar, "body": body,
            "name_lbl": name_lbl, "sub_lbl": sub_lbl,
        }

    def _update_card(self, refs, name, subtitle, bg, sub_color, border, accent):
        try:
            refs["frame"].config(bg=bg, highlightbackground=border)
            refs["bar"].config(bg=accent)
            refs["body"].config(bg=bg)
            refs["name_lbl"].config(text=name, bg=bg)
            refs["sub_lbl"].config(text=subtitle, bg=bg, fg=sub_color)
        except Exception:
            pass