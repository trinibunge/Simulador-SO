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

LOG_TAG = "HISTORIA"


class _RWState:
    """
    Problema clásico de Lectores-Escritores.

    Varios lectores pueden acceder a la vez; un escritor necesita
    acceso EXCLUSIVO (ningún lector ni otro escritor activo).

    Cada evento relevante se reporta a la bitácora del sistema vía
    hospital_state.log(LOG_TAG, ...), para que la Bitácora muestre la
    "narrativa" completa de qué ocurre con la historia clínica.
    """

    def __init__(self, hospital_state=None):
        self.hospital_state = hospital_state

        # Lock interno: protege solo las estructuras de presentación
        # (active_readers, active_writer, waiting_writers, history).
        self.lock = threading.Lock()

        # Locks del protocolo Readers-Writers (Courtois 1971):
        # _write_lock: lo toma el escritor o el PRIMER lector.
        # _readers_lock: protege el contador de lectores.
        self._readers_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._reader_count = 0

        self.record = ENTRIES[0]
        self.history: list[str] = []
        self.active_readers: dict[int, dict] = {}
        self.active_writer: str | None = None
        self.waiting_writers: dict[int, str] = {}
        self._next_id = 1
        self.running = True

    def _log(self, msg: str):
        """Envía un evento a la bitácora del Hospital, si hay state conectado."""
        if self.hospital_state is not None:
            try:
                self.hospital_state.log(LOG_TAG, msg)
            except Exception:
                # nunca fallar por culpa del logging
                pass

    # ─────────────────────────────────────────────────────────────────
    #  Lector
    # ─────────────────────────────────────────────────────────────────
    def add_reader(self, name: str):
        pid = self._next_id
        self._next_id += 1

        def run():
            with self.lock:
                self.active_readers[pid] = {"name": name, "state": "esperando"}
            self._log(f"{name} llega a consultar la historia clínica")

            # pequeña pausa para que la UI muestre "Esperando turno..."
            time.sleep(1.0)

            # Protocolo lector: el primero en llegar bloquea al escritor.
            # IMPORTANTE: el acquire del write_lock va DENTRO del _readers_lock
            # para que los lectores siguientes queden en cola si el primero
            # todavía está esperando a un escritor.
            t0 = time.time()
            with self._readers_lock:
                self._reader_count += 1
                if self._reader_count == 1:
                    if not self._write_lock.acquire(blocking=False):
                        self._log(f"{name} debe esperar: una enfermera está escribiendo")
                        self._write_lock.acquire()  # ahora sí, bloquea
            waited = time.time() - t0

            with self.lock:
                if pid in self.active_readers:
                    self.active_readers[pid]["state"] = "leyendo"

            n = self._reader_count
            if waited > 1.05:  # >1s significa que esperó (descontando el sleep inicial)
                self._log(f"{name} comienza a leer tras esperar "
                          f"{waited - 1.0:.1f}s (lectores activos: {n})")
            else:
                self._log(f"{name} comienza a leer (lectores activos: {n})")

            # tiempo de consulta
            time.sleep(random.uniform(3.0, 5.0))

            with self.lock:
                self.active_readers.pop(pid, None)
            self._log(f"{name} termina su consulta")

            # Protocolo lector: el último en irse libera al escritor.
            with self._readers_lock:
                self._reader_count -= 1
                if self._reader_count == 0:
                    self._write_lock.release()
                    self._log("Último lector se retira: historia clínica "
                              "disponible para escritura")

        threading.Thread(target=run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────
    #  Escritor
    # ─────────────────────────────────────────────────────────────────
    def add_writer(self, name: str):
        pid = self._next_id
        self._next_id += 1

        def run():
            with self.lock:
                self.waiting_writers[pid] = name
            self._log(f"{name} llega a actualizar la historia clínica")

            # pequeña pausa para que la UI muestre "En cola..."
            time.sleep(1.0)

            # Esperar a que no haya lectores ni otro escritor
            t0 = time.time()
            if not self._write_lock.acquire(blocking=False):
                self._log(f"{name} debe esperar: hay lectores o un escritor activo")
                self._write_lock.acquire()  # bloqueante
            waited = time.time() - t0

            with self.lock:
                self.waiting_writers.pop(pid, None)
                self.active_writer = name

            if waited > 0.05:
                self._log(f"{name} obtiene acceso EXCLUSIVO tras esperar {waited:.1f}s")
            else:
                self._log(f"{name} obtiene acceso EXCLUSIVO y comienza a escribir")

            # tiempo de escritura
            time.sleep(random.uniform(3.5, 5.5))
            new_entry = random.choice(ENTRIES)

            with self.lock:
                self.record = new_entry
                ts = time.strftime("%H:%M:%S")
                self.history.append(f"[{ts}] {name}: {new_entry}")
                self.history = self.history[-7:]
                self.active_writer = None

            self._log(f"{name} termina la actualización: {new_entry}")
            self._write_lock.release()

        threading.Thread(target=run, daemon=True).start()


# ═════════════════════════════════════════════════════════════════════
#  UI
# ═════════════════════════════════════════════════════════════════════

class ReadersApp(WindowBase):
    BG = "#f8fbff"
    INK = "#102033"

    def __init__(self, master, state, x=80, y=60):
        super().__init__(master, "Historia Clínica — Lectores y Escritores",
                         GREEN, 880, 580, x, y)
        self.state = state
        self.rw = _RWState(state)
        self.content.configure(bg=self.BG)

        # Caches de cards para evitar flicker (no destruir/recrear cada frame)
        self._reader_cards: dict[int, dict] = {}            # pid -> refs
        self._writer_waiting_cards: dict[int, dict] = {}    # pid -> refs
        self._active_writer_card: dict | None = None        # un solo card
        self._readers_empty_lbl: tk.Label | None = None
        self._writers_empty_lbl: tk.Label | None = None

        self._build_ui()
        self.refresh()
        # Arranca con una enfermera escribiendo para que los lectores tengan que esperar
        self.frame.after(400, self._spawn_writer)

    # ─────────────────────────────────────────────────────────────────
    #  Construcción de la UI
    # ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # encabezado
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(header, text="Historia Clínica",
                 bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Varios médicos pueden leer a la vez · solo una enfermera puede escribir",
            bg=self.BG, fg=SOFT, font=FONT_SM,
        ).pack(anchor="w", pady=(2, 0))

        # botonera
        btns = tk.Frame(self.content, bg=self.BG)
        btns.pack(fill="x", padx=16, pady=(8, 10))
        self._btn(btns, "👨‍⚕️  Médico llega a leer", GREEN, self._spawn_reader)
        self._btn(btns, "👩‍⚕️  Enfermera llega a escribir", ORANGE, self._spawn_writer)

        # cuerpo: 3 columnas
        body = tk.Frame(self.content, bg=self.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # ── columna izquierda: lectores ──
        left = tk.Frame(body, bg=self.BG, width=210)
        left.pack_propagate(False)
        left.pack(side="left", fill="y", padx=(0, 12))
        self._column_header(left, "Leyendo ahora", "pueden ser varios", GREEN)
        self._readers_panel = tk.Frame(left, bg=self.BG)
        self._readers_panel.pack(fill="both", expand=True, pady=(8, 0))

        # ── columna derecha: escritoras ──
        # IMPORTANTE: packed ANTES que el center con expand=True, sino el center
        # se come todo el espacio y la derecha queda fuera de la ventana.
        right = tk.Frame(body, bg=self.BG, width=210)
        right.pack_propagate(False)
        right.pack(side="right", fill="y", padx=(12, 0))
        self._column_header(right, "Escribiendo / en cola", "una a la vez", ORANGE)
        self._writers_panel = tk.Frame(right, bg=self.BG)
        self._writers_panel.pack(fill="both", expand=True, pady=(8, 0))

        # ── columna central: registro ──
        center = tk.Frame(body, bg=PANEL,
                          highlightthickness=1, highlightbackground=BORDER)
        center.pack(side="left", fill="both", expand=True)

        self._center_bar = tk.Frame(center, bg=GREEN, height=4)
        self._center_bar.pack(fill="x")

        inner = tk.Frame(center, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=16, pady=14)

        tk.Label(inner, text="REGISTRO COMPARTIDO",
                 bg=PANEL, fg=SOFT, font=("Segoe UI", 9, "bold")).pack(anchor="w")

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
            relief="flat", highlightthickness=1, highlightbackground=BORDER_SOFT,
            state="disabled", height=8,
        )
        self._history_box.pack(fill="both", expand=True, pady=(4, 0))

    def _column_header(self, parent, title, subtitle, accent):
        """Encabezado de columna con barra de color a la izquierda."""
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
    #  Acciones
    # ─────────────────────────────────────────────────────────────────
    def _spawn_reader(self):
        self.rw.add_reader(random.choice(DOCTOR_NAMES))

    def _spawn_writer(self):
        self.rw.add_writer(random.choice(NURSE_NAMES))

    # ─────────────────────────────────────────────────────────────────
    #  Loop de refresh
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
        with self.rw.lock:
            readers = dict(self.rw.active_readers)
            writer = self.rw.active_writer
            waiters = dict(self.rw.waiting_writers)
            record = self.rw.record
            history = list(self.rw.history)

        reading = [(pid, info) for pid, info in readers.items()
                   if info["state"] == "leyendo"]

        # ── Estado central ──
        if writer:
            self._status_lbl.config(text=f"ESCRIBIENDO · {writer}",
                                    bg="#fef2f2", fg=RED)
            self._center_bar.config(bg=RED)
        elif reading:
            n = len(reading)
            self._status_lbl.config(
                text=f"LEYENDO · {n} {'médico' if n == 1 else 'médicos'}",
                bg="#f0fdf4", fg=GREEN,
            )
            self._center_bar.config(bg=GREEN)
        else:
            self._status_lbl.config(text="LIBRE", bg="#f1f5f9", fg=SOFT)
            self._center_bar.config(bg=BORDER)

        self._record_lbl.config(text=record or "(sin registro)")

        # historial
        self._history_box.config(state="normal")
        self._history_box.delete("1.0", tk.END)
        for line in history:
            self._history_box.insert(tk.END, f"{line}\n")
        self._history_box.see(tk.END)
        self._history_box.config(state="disabled")

        # ── Panel lectores ──
        self._sync_reader_cards(readers)

        # ── Panel escritoras ──
        self._sync_writer_cards(writer, waiters)

    # ─────────────────────────────────────────────────────────────────
    #  Sincronización de cards (cache, sin destruir/recrear)
    # ─────────────────────────────────────────────────────────────────
    def _sync_reader_cards(self, readers: dict):
        current_pids = set(readers.keys())

        # 1) eliminar cards de readers que ya no están
        for pid in list(self._reader_cards.keys()):
            if pid not in current_pids:
                try:
                    self._reader_cards[pid]["frame"].destroy()
                except Exception:
                    pass
                del self._reader_cards[pid]

        # 2) crear / actualizar
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
                    self._readers_panel, name, subtitle, bg, sub_color, border, accent
                )
            else:
                self._update_card(self._reader_cards[pid], name, subtitle,
                                  bg, sub_color, border, accent)

        # 3) reordenar: leyendo primero, esperando después
        order = sorted(self._reader_cards.keys(),
                       key=lambda p: (0 if readers[p]["state"] == "leyendo" else 1, p))
        for pid in order:
            self._reader_cards[pid]["frame"].pack_forget()
        for pid in order:
            self._reader_cards[pid]["frame"].pack(fill="x", pady=3)

        # 4) empty state
        self._toggle_empty_label("readers", len(readers) == 0,
                                  "Nadie consultando")

    def _sync_writer_cards(self, active_writer: str | None, waiters: dict):
        # ── escritora activa (puede haber una sola) ──
        if active_writer is None:
            if self._active_writer_card is not None:
                try:
                    self._active_writer_card["frame"].destroy()
                except Exception:
                    pass
                self._active_writer_card = None
        else:
            if self._active_writer_card is None:
                self._active_writer_card = self._build_card(
                    self._writers_panel, active_writer, "Escribiendo...",
                    "#fef2f2", RED, "#fca5a5", RED
                )
            else:
                self._update_card(self._active_writer_card, active_writer,
                                  "Escribiendo...", "#fef2f2", RED,
                                  "#fca5a5", RED)

        # ── escritoras en espera ──
        current_pids = set(waiters.keys())
        for pid in list(self._writer_waiting_cards.keys()):
            if pid not in current_pids:
                try:
                    self._writer_waiting_cards[pid]["frame"].destroy()
                except Exception:
                    pass
                del self._writer_waiting_cards[pid]

        for pid, name in waiters.items():
            if pid not in self._writer_waiting_cards:
                self._writer_waiting_cards[pid] = self._build_card(
                    self._writers_panel, name, "Esperando su turno...",
                    "#fff7ed", ORANGE, "#fed7aa", ORANGE
                )
            else:
                self._update_card(self._writer_waiting_cards[pid], name,
                                  "Esperando su turno...", "#fff7ed", ORANGE,
                                  "#fed7aa", ORANGE)

        # reempacado: activa arriba, luego espera por pid
        if self._active_writer_card is not None:
            self._active_writer_card["frame"].pack_forget()
            self._active_writer_card["frame"].pack(fill="x", pady=3)
        for pid in sorted(self._writer_waiting_cards.keys()):
            self._writer_waiting_cards[pid]["frame"].pack_forget()
            self._writer_waiting_cards[pid]["frame"].pack(fill="x", pady=3)

        # empty state
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

    # ─────────────────────────────────────────────────────────────────
    #  Card helpers
    # ─────────────────────────────────────────────────────────────────
    def _build_card(self, parent, name, subtitle, bg, sub_color, border, accent):
        """Card con barra de color a la izquierda + nombre + subtítulo."""
        frame = tk.Frame(parent, bg=bg,
                         highlightthickness=1, highlightbackground=border)
        # barra de color a la izquierda
        bar = tk.Frame(frame, bg=accent, width=3)
        bar.pack(side="left", fill="y")
        # cuerpo
        body = tk.Frame(frame, bg=bg)
        body.pack(side="left", fill="both", expand=True, padx=10, pady=7)
        name_lbl = tk.Label(body, text=name, bg=bg, fg=self.INK, font=FONT_BOLD)
        name_lbl.pack(anchor="w")
        sub_lbl = tk.Label(body, text=subtitle, bg=bg, fg=sub_color,
                           font=FONT_SM)
        sub_lbl.pack(anchor="w", pady=(2, 0))
        return {
            "frame": frame, "bar": bar, "body": body,
            "name_lbl": name_lbl, "sub_lbl": sub_lbl,
        }

    def _update_card(self, refs, name, subtitle, bg, sub_color, border, accent):
        """Actualiza una card existente in-place (sin destruir, sin flicker)."""
        try:
            refs["frame"].config(bg=bg, highlightbackground=border)
            refs["bar"].config(bg=accent)
            refs["body"].config(bg=bg)
            refs["name_lbl"].config(text=name, bg=bg)
            refs["sub_lbl"].config(text=subtitle, bg=bg, fg=sub_color)
        except Exception:
            pass