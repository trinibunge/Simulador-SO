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


class _RWState:
    """
    Problema clásico de Lectores-Escritores.
    Varios lectores pueden acceder a la vez; un escritor necesita
    acceso exclusivo (ningún lector ni otro escritor activo).
    """

    def __init__(self):
        self.lock = threading.Lock()         # protege las listas de UI
        self._readers_lock = threading.Lock()  # mutex para _reader_count
        self._write_lock = threading.Lock()    # mutex de escritura
        self._reader_count = 0

        self.record = ENTRIES[0]
        self.history: list[str] = []
        self.active_readers: dict[int, dict] = {}  # id -> {name, state}
        self.active_writer: str | None = None
        self.waiting_writers: dict[int, str] = {}  # id -> name
        self._next_id = 1
        self.running = True

    def add_reader(self, name: str):
        pid = self._next_id
        self._next_id += 1

        def run():
            with self.lock:
                self.active_readers[pid] = {"name": name, "state": "esperando"}

            # Pausa para que la UI muestre "Esperando turno..." antes de intentar entrar
            time.sleep(1.0)

            # Protocolo lector: el primero en llegar bloquea al escritor
            with self._readers_lock:
                self._reader_count += 1
                if self._reader_count == 1:
                    self._write_lock.acquire()

            with self.lock:
                if pid in self.active_readers:
                    self.active_readers[pid]["state"] = "leyendo"

            time.sleep(random.uniform(3.0, 5.0))

            with self.lock:
                self.active_readers.pop(pid, None)

            # Protocolo lector: el último en irse libera al escritor
            with self._readers_lock:
                self._reader_count -= 1
                if self._reader_count == 0:
                    self._write_lock.release()

        threading.Thread(target=run, daemon=True).start()

    def add_writer(self, name: str):
        pid = self._next_id
        self._next_id += 1

        def run():
            with self.lock:
                self.waiting_writers[pid] = name

            # Pausa para que la UI muestre "En cola..." antes de adquirir el lock
            time.sleep(1.0)

            # Espera a que no haya lectores ni otro escritor
            self._write_lock.acquire()

            with self.lock:
                self.waiting_writers.pop(pid, None)
                self.active_writer = name

            time.sleep(random.uniform(3.5, 5.5))
            new_entry = random.choice(ENTRIES)

            with self.lock:
                self.record = new_entry
                ts = time.strftime("%H:%M:%S")
                self.history.append(f"[{ts}] {name}: {new_entry}")
                self.history = self.history[-7:]
                self.active_writer = None

            self._write_lock.release()

        threading.Thread(target=run, daemon=True).start()


class ReadersApp(WindowBase):
    BG = "#f8fbff"
    INK = "#102033"

    def __init__(self, master, state, x=80, y=60):
        super().__init__(master, "Historia Clínica — Lectores y Escritores", GREEN, 840, 560, x, y)
        self.rw = _RWState()
        self.content.configure(bg=self.BG)
        self._build_ui()
        self.refresh()
        # Arranca con una enfermera escribiendo para que los lectores tengan que esperar
        self.frame.after(400, self._spawn_writer)

    def _build_ui(self):
        header = tk.Frame(self.content, bg=self.BG)
        header.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(header, text="Historia Clínica", bg=self.BG, fg=self.INK, font=FONT_BIG).pack(anchor="w")
        tk.Label(
            header,
            text="Varios médicos pueden leer a la vez — solo una enfermera puede escribir",
            bg=self.BG, fg=SOFT, font=FONT_SM,
        ).pack(anchor="w", pady=(2, 0))

        btns = tk.Frame(self.content, bg=self.BG)
        btns.pack(fill="x", padx=14, pady=(6, 8))
        self._btn(btns, "Médico llega a leer", GREEN, self._spawn_reader)
        self._btn(btns, "Enfermera llega a escribir", ORANGE, self._spawn_writer)

        body = tk.Frame(self.content, bg=self.BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # ── Columna izquierda: lectores activos ──
        left = tk.Frame(body, bg=self.BG, width=190)
        left.pack_propagate(False)
        left.pack(side="left", fill="y", padx=(0, 10))

        tk.Label(left, text="Leyendo ahora", bg=self.BG, fg=self.INK, font=FONT_BOLD).pack(anchor="w")
        tk.Label(left, text="(pueden ser varios)", bg=self.BG, fg=SOFT, font=FONT_SM).pack(anchor="w", pady=(1, 8))
        self._readers_panel = tk.Frame(left, bg=self.BG)
        self._readers_panel.pack(fill="both", expand=True)

        # ── Centro: el registro ──
        center = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        center.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._center_bar = tk.Frame(center, bg=GREEN, height=4)
        self._center_bar.pack(fill="x")

        inner = tk.Frame(center, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(inner, text="Registro compartido", bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")

        self._status_lbl = tk.Label(
            inner, text="LIBRE", bg="#f0fdf4", fg=GREEN,
            font=("Segoe UI", 10, "bold"), padx=10, pady=4,
        )
        self._status_lbl.pack(anchor="w", pady=(4, 6))

        self._waiter_banner = tk.Label(
            inner, text="", bg=PANEL, fg=ORANGE,
            font=("Segoe UI", 9, "bold"), padx=0, pady=0,
        )
        self._waiter_banner.pack(anchor="w", pady=(0, 8))

        tk.Label(inner, text="Último registro:", bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")
        self._record_lbl = tk.Label(
            inner, text="", bg=PANEL, fg=self.INK,
            font=("Consolas", 10, "bold"), wraplength=300, justify="left",
        )
        self._record_lbl.pack(anchor="w", pady=(3, 14))

        tk.Label(inner, text="Historial de cambios:", bg=PANEL, fg=SOFT, font=FONT_SM).pack(anchor="w")
        self._history_box = tk.Text(
            inner, bg=PANEL_2, fg=MUTED, font=("Consolas", 9),
            relief="flat", highlightthickness=0, state="disabled",
        )
        self._history_box.pack(fill="both", expand=True, pady=(4, 0))

        # ── Columna derecha: escritores esperando ──
        right = tk.Frame(body, bg=self.BG, width=175)
        right.pack_propagate(False)
        right.pack(side="left", fill="y")

        tk.Label(right, text="Esperando escribir", bg=self.BG, fg=self.INK, font=FONT_BOLD).pack(anchor="w")
        tk.Label(right, text="(una a la vez)", bg=self.BG, fg=SOFT, font=FONT_SM).pack(anchor="w", pady=(1, 8))
        self._writers_panel = tk.Frame(right, bg=self.BG)
        self._writers_panel.pack(fill="both", expand=True)

    def _btn(self, parent, text, color, cmd):
        tk.Button(
            parent, text=text, bg=color, fg="white",
            relief="flat", bd=0, padx=12, pady=7,
            font=FONT_BOLD, cursor="hand2",
            activebackground=color, activeforeground="white",
            command=cmd,
        ).pack(side="left", padx=(0, 8))

    def _spawn_reader(self):
        self.rw.add_reader(random.choice(DOCTOR_NAMES))

    def _spawn_writer(self):
        self.rw.add_writer(random.choice(NURSE_NAMES))

    def refresh(self):
        if not self.alive:
            return
        try:
            self._render()
        except Exception:
            pass
        self.frame.after(180, self.refresh)

    def _render(self):
        with self.rw.lock:
            readers = dict(self.rw.active_readers)
            writer = self.rw.active_writer
            waiters = dict(self.rw.waiting_writers)
            record = self.rw.record
            history = list(self.rw.history)

        reading = [r for r in readers.values() if r["state"] == "leyendo"]
        waiting_readers = [r for r in readers.values() if r["state"] == "esperando"]

        # ── Estado central ──
        if writer:
            self._status_lbl.config(text="ESCRIBIENDO", bg="#fef2f2", fg=RED)
            self._center_bar.config(bg=RED)
        elif reading:
            n = len(reading)
            self._status_lbl.config(
                text=f"LEYENDO  ({n} {'médico' if n == 1 else 'médicos'})",
                bg="#f0fdf4", fg=GREEN,
            )
            self._center_bar.config(bg=GREEN)
        else:
            self._status_lbl.config(text="LIBRE", bg="#f8fafc", fg=SOFT)
            self._center_bar.config(bg=BORDER)

        # Banner de enfermeras en espera
        n_wait = len(waiters)
        if n_wait:
            txt = f"⚠  {'1 enfermera esperando' if n_wait == 1 else f'{n_wait} enfermeras esperando'} para escribir"
            self._waiter_banner.config(text=txt)
        else:
            self._waiter_banner.config(text="")

        self._record_lbl.config(text=record)

        self._history_box.config(state="normal")
        self._history_box.delete("1.0", tk.END)
        for line in history:
            self._history_box.insert(tk.END, f"{line}\n")
        self._history_box.see(tk.END)
        self._history_box.config(state="disabled")

        # ── Panel lectores ──
        for w in self._readers_panel.winfo_children():
            w.destroy()
        for info in reading:
            self._card(self._readers_panel, info["name"], "Leyendo...", "#f0fdf4", GREEN)
        for info in waiting_readers:
            self._card(self._readers_panel, info["name"], "Esperando turno...", PANEL_2, SOFT)
        for name in waiters.values():
            self._card(self._readers_panel, name, "Esperando para escribir...", "#fff7ed", ORANGE, border="#fed7aa")
        if not readers and not waiters:
            tk.Label(self._readers_panel, text="Nadie leyendo", bg=self.BG, fg=SOFT,
                     font=FONT_ITALIC).pack(anchor="w")

        # ── Panel escritoras ──
        for w in self._writers_panel.winfo_children():
            w.destroy()
        if writer:
            self._card(self._writers_panel, writer, "Escribiendo...", "#fef2f2", RED,
                       border="#fca5a5")
        for name in waiters.values():
            self._card(self._writers_panel, name, "Esperando su turno....", "#fff7ed", ORANGE,
                       border="#fed7aa")
        if not writer and not waiters:
            tk.Label(self._writers_panel, text="Nadie esperando", bg=self.BG, fg=SOFT,
                     font=FONT_ITALIC).pack(anchor="w")

    def _card(self, parent, name, subtitle, bg, fg, border=None):
        border = border or BORDER
        card = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border)
        card.pack(fill="x", pady=2)
        tk.Label(card, text=name, bg=bg, fg=self.INK, font=FONT_BOLD).pack(anchor="w", padx=8, pady=(5, 0))
        tk.Label(card, text=subtitle, bg=bg, fg=fg, font=FONT_SM).pack(anchor="w", padx=8, pady=(1, 5))
