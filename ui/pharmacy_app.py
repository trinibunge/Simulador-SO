import tkinter as tk
import threading
import time
import random
from ui.window_base import WindowBase
from ui.theme import *
from ui.toast import Toast


class PharmacyApp(WindowBase):
    """
    Farmacia — Productor / Consumidor con procesos reales.

    Cada operación (producir o consumir un medicamento) NO es solo un
    thread silencioso: se registra como un proceso del sistema (kind=app),
    pasa por el scheduler, se BLOQUEA si el buffer está lleno/vacío, y se
    da de alta al terminar. Esto significa que cada productor y consumidor
    aparece en las métricas del sistema con sus tiempos reales de espera,
    CPU y bloqueo.

    La app principal también es un proceso (el "padre"), igual que
    Snake, Wordle o el Asistente Médico.
    """

    APP_NAME = "Farmacia"
    APP_PRIORITY = 7

    def __init__(self, master, state, x=460, y=160):
        super().__init__(master, "Farmacia", PURPLE, 700, 500, x, y)
        self.state = state
        self.content.configure(bg=PANEL)

        # Registrar la VENTANA como proceso padre (igual que Snake/Asistente)
        self._app_paciente = None
        if state is not None:
            self._app_paciente = state.admitir(
                self.APP_NAME,
                priority=self.APP_PRIORITY,
                burst=999_999_999,
                kind="app",
            )

        # Hilos "supervisor" que disparan procesos por operación
        self._producer_threads: list[threading.Thread] = []
        self._consumer_threads: list[threading.Thread] = []
        self._op_counter = 0
        self._op_counter_lock = threading.Lock()

        # ── Header ──
        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(14, 6))
        tk.Label(head, text="Farmacia — Productor / Consumidor",
                 bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head, text="Cada operación es un proceso real del sistema "
                            "(buffer capacidad 8)",
                 bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        # ── Botonera ──
        bar = tk.Frame(self.content, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=(8, 8))

        tk.Button(bar, text="Iniciar", bg=GREEN, fg="white", relief="flat",
                  padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
                  command=self.start).pack(side="left", padx=3)
        tk.Button(bar, text="Detener", bg=RED, fg="white", relief="flat",
                  padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
                  command=self.stop).pack(side="left", padx=3)
        tk.Button(bar, text="+ 1 (producir)", bg=BLUE, fg="white", relief="flat",
                  padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
                  command=self.produce_one).pack(side="left", padx=3)
        tk.Button(bar, text="- 1 (consumir)", bg=ORANGE, fg="white", relief="flat",
                  padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
                  command=self.consume_one).pack(side="left", padx=3)

        # ── Canvas con el buffer ──
        self.canvas = tk.Canvas(self.content, bg=PANEL, height=220,
                                highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=14, pady=(4, 8))

        self.refresh()

    def on_close(self):
        self.state.pharmacy_running = False
        # Dar de alta la ventana padre
        if self._app_paciente is not None:
            try:
                self.state.dar_alta(self._app_paciente.pid)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  Generación de PIDs únicos para operaciones
    # ─────────────────────────────────────────────────────────────────
    def _next_op_id(self) -> int:
        with self._op_counter_lock:
            self._op_counter += 1
            return self._op_counter

    # ─────────────────────────────────────────────────────────────────
    #  Botones manuales — lanzan un proceso corto
    # ─────────────────────────────────────────────────────────────────
    def produce_one(self):
        n = self._next_op_id()
        threading.Thread(
            target=self._produce_as_process,
            args=(f"💊 manual-prod-{n}", 0.3),  # timeout corto: si está lleno, falla
            daemon=True,
        ).start()

    def consume_one(self):
        n = self._next_op_id()
        threading.Thread(
            target=self._consume_as_process,
            args=(f"💊 manual-cons-{n}", 0.3),
            daemon=True,
        ).start()

    # ─────────────────────────────────────────────────────────────────
    #  Producción / consumo automática
    # ─────────────────────────────────────────────────────────────────
    def start(self):
        if self.state.pharmacy_running:
            return
        self.state.pharmacy_running = True
        self.state.log("FARMACIA", "Turno iniciado: 2 farmacéuticos + 3 enfermeros")

        # Supervisores: lanzan procesos a intervalos aleatorios. Cada
        # PROCESO es la operación real, no el supervisor.
        for i in range(2):
            t = threading.Thread(
                target=self._producer_supervisor,
                args=(f"Farm{i+1}",),
                daemon=True,
            )
            t.start()
            self._producer_threads.append(t)

        for i in range(3):
            t = threading.Thread(
                target=self._consumer_supervisor,
                args=(f"Enf{i+1}",),
                daemon=True,
            )
            t.start()
            self._consumer_threads.append(t)

        Toast(self.master, "Producción iniciada", GREEN)

    def stop(self):
        self.state.pharmacy_running = False
        Toast(self.master, "Producción detenida", RED)

    def _producer_supervisor(self, name_prefix: str):
        """No hace I/O — solo dispara procesos a intervalos aleatorios."""
        while self.state.pharmacy_running and self.state.running:
            time.sleep(random.uniform(0.4, 0.8))
            if not self.state.pharmacy_running or not self.state.running:
                break
            n = self._next_op_id()
            op_name = f"💊 {name_prefix}-prod-{n}"
            threading.Thread(
                target=self._produce_as_process,
                args=(op_name, 2.0),
                daemon=True,
            ).start()

    def _consumer_supervisor(self, name_prefix: str):
        while self.state.pharmacy_running and self.state.running:
            time.sleep(random.uniform(0.6, 1.2))
            if not self.state.pharmacy_running or not self.state.running:
                break
            n = self._next_op_id()
            op_name = f"💊 {name_prefix}-cons-{n}"
            threading.Thread(
                target=self._consume_as_process,
                args=(op_name, 2.0),
                daemon=True,
            ).start()

    # ─────────────────────────────────────────────────────────────────
    #  Cada operación = un proceso real
    # ─────────────────────────────────────────────────────────────────
    def _produce_as_process(self, name: str, timeout: float):
        """Una operación de producir = nacer, trabajar, morir."""
        p = self.state.admitir(name, priority=6, burst=3, kind="app")
        if p is None:
            return
        pid = p.pid

        # "Preparar el medicamento" — algo de trabajo de CPU
        time.sleep(random.uniform(0.05, 0.25))

        # Operación instrumentada — puede bloquearse en el buffer
        self.state.pharmacy_put(pid, "💊", timeout=timeout)

        # Pequeña pausa final y alta
        time.sleep(random.uniform(0.03, 0.12))
        try:
            self.state.dar_alta(pid)
        except Exception:
            pass

    def _consume_as_process(self, name: str, timeout: float):
        """Una operación de consumir = nacer, trabajar, morir."""
        p = self.state.admitir(name, priority=6, burst=3, kind="app")
        if p is None:
            return
        pid = p.pid

        time.sleep(random.uniform(0.05, 0.25))
        self.state.pharmacy_get(pid, timeout=timeout)
        time.sleep(random.uniform(0.03, 0.12))
        try:
            self.state.dar_alta(pid)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────
    #  Render
    # ─────────────────────────────────────────────────────────────────
    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 680
        cap = self.state.PHARMACY_CAPACITY

        size = self.state.pharmacy_queue.qsize()

        c.create_text(10, 12, anchor="nw",
                      text=f"Buffer de medicamentos ({size}/{cap})",
                      fill=FG, font=FONT_BIG)

        if size == 0:
            badge_t, badge_c = "VACÍO", RED
        elif size >= cap:
            badge_t, badge_c = "LLENO", ORANGE
        else:
            badge_t, badge_c = "OK", GREEN

        c.create_rectangle(W - 90, 10, W - 14, 32, fill=badge_c, outline="")
        c.create_text(W - 52, 21, text=badge_t, fill="white",
                      font=("Segoe UI", 10, "bold"))

        slot_w = 52
        slot_h = 64
        gap = 8
        total_w = cap * slot_w + (cap - 1) * gap
        start_x = (W - total_w) // 2
        slot_y = 52

        for i in range(cap):
            x0 = start_x + i * (slot_w + gap)
            x1 = x0 + slot_w
            filled = i < size
            bg = "#dbeafe" if filled else "#f3f4f6"
            bd = "#2563eb" if filled else "#d1d5db"
            c.create_rectangle(x0, slot_y, x1, slot_y + slot_h,
                               fill=bg, outline=bd, width=2)
            if filled:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2,
                              text="💊", font=("Segoe UI Emoji", 20))
            else:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2,
                              text="·", fill=SOFT, font=("Segoe UI", 18))

        c.create_text(20, 184, anchor="w", text="Productores →",
                      fill=GREEN, font=FONT_BOLD)
        c.create_text(W - 20, 184, anchor="e", text="→ Consumidores",
                      fill=BLUE, font=FONT_BOLD)

        if self.alive:
            self.frame.after(200, self.refresh)