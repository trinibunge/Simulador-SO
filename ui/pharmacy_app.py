import tkinter as tk
import threading
import time
import random
from ui.window_base import WindowBase
from ui.theme import *
from ui.toast import Toast


class PharmacyApp(WindowBase):
    """
    💊 Farmacia del Hospital — Productor-Consumidor real.

    Tres productores (farmacéuticos) producen medicamentos y los meten
    en un buffer acotado (queue.Queue con maxsize=8).
    Tres consumidores (enfermeros) los retiran para los pacientes.

    Si el buffer está LLENO → los productores se bloquean en put().
    Si el buffer está VACÍO → los consumidores se bloquean en get().

    Esto es el patrón clásico de SO con la primitiva de sincronización
    más limpia que existe en Python: queue.Queue ya implementa
    bounded buffer + mutex + condition variables internamente.
    """

    def __init__(self, master, state, x=460, y=160):
        super().__init__(master, "💊 Farmacia", PURPLE, 720, 540, x, y)
        self.state = state
        self.content.configure(bg=PANEL)

        self._producers = []
        self._consumers = []

        # ─── header ───
        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(14, 6))
        tk.Label(head, text="Farmacia — Productor / Consumidor",
                 bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head,
                 text="farmacéuticos producen medicamentos · enfermeros los consumen · "
                      "buffer acotado de 8",
                 bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        # ─── controles ───
        bar = tk.Frame(self.content, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=(8, 8))

        self.btn_start = tk.Button(
            bar, text="▶  Iniciar producción", bg=GREEN, fg="white",
            relief="flat", padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
            command=self.start)
        self.btn_start.pack(side="left", padx=3)

        self.btn_stop = tk.Button(
            bar, text="■  Detener", bg=RED, fg="white",
            relief="flat", padx=12, pady=7, font=FONT_BOLD, cursor="hand2",
            command=self.stop)
        self.btn_stop.pack(side="left", padx=3)

        tk.Frame(bar, bg=PANEL, width=14).pack(side="left")

        tk.Button(bar, text="+ 1 medicamento (manual)", bg=BLUE, fg="white",
                  relief="flat", padx=12, pady=7, font=FONT_BOLD,
                  cursor="hand2", command=self.produce_one).pack(side="left", padx=3)
        tk.Button(bar, text="- 1 medicamento (manual)", bg=ORANGE, fg="white",
                  relief="flat", padx=12, pady=7, font=FONT_BOLD,
                  cursor="hand2", command=self.consume_one).pack(side="left", padx=3)

        # ─── canvas visualización del buffer ───
        self.canvas = tk.Canvas(
            self.content, bg=PANEL, height=240,
            highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=14, pady=(4, 8))

        # ─── stats abajo ───
        self.stats_var = tk.StringVar()
        tk.Label(self.content, textvariable=self.stats_var,
                 bg=PANEL, fg=MUTED, font=FONT_SM, anchor="w"
                 ).pack(fill="x", padx=14, pady=(0, 12))


        self.refresh()

    # ─── hooks ───

    def on_close(self):
        self.state.pharmacy_running = False

    # ─── acciones ───

    def start(self):
        if self.state.pharmacy_running:
            return
        self.state.pharmacy_running = True
        self.state.log("FARMACIA", "Iniciando turno de producción")

        # 2 productores, 3 consumidores: a propósito desbalanceado
        # para que se vea cómo el buffer se llena y los productores se traban.
        for i in range(2):
            t = threading.Thread(target=self._producer_loop,
                                 args=(f"Farmacéutico {i+1}",),
                                 daemon=True)
            t.start()
            self._producers.append(t)

        for i in range(3):
            t = threading.Thread(target=self._consumer_loop,
                                 args=(f"Enfermero {i+1}",),
                                 daemon=True)
            t.start()
            self._consumers.append(t)

        Toast(self.master, "Producción iniciada", GREEN)

    def stop(self):
        self.state.pharmacy_running = False
        Toast(self.master, "Producción detenida", RED)

    def produce_one(self):
        try:
            self.state.pharmacy_queue.put_nowait("💊")
            self.state.pharmacy_stats["producidos"] += 1
            self.state.log("FARMACIA", "Medicamento añadido (manual)")
        except Exception:
            self.state.log("FARMACIA", "Buffer LLENO, no se pudo producir")
            Toast(self.master, "Buffer lleno", ORANGE)

    def consume_one(self):
        try:
            self.state.pharmacy_queue.get_nowait()
            self.state.pharmacy_stats["consumidos"] += 1
            self.state.log("FARMACIA", "Medicamento consumido (manual)")
        except Exception:
            self.state.log("FARMACIA", "Buffer VACÍO, no se pudo consumir")
            Toast(self.master, "Buffer vacío", ORANGE)

    # ─── loops de hilos ───

    def _producer_loop(self, name):
        while self.state.pharmacy_running and self.state.running:
            time.sleep(random.uniform(0.4, 1.2))
            if not self.state.pharmacy_running:
                break
            try:
                # put() bloquea si está lleno: timeout corto para revisar el flag
                self.state.pharmacy_queue.put("💊", timeout=2.0)
                self.state.pharmacy_stats["producidos"] += 1
                self.state.log("FARMACIA", f"{name} produjo un medicamento")
            except Exception:
                self.state.log("FARMACIA", f"{name} esperando (buffer lleno)")

    def _consumer_loop(self, name):
        while self.state.pharmacy_running and self.state.running:
            time.sleep(random.uniform(0.6, 1.5))
            if not self.state.pharmacy_running:
                break
            try:
                self.state.pharmacy_queue.get(timeout=2.0)
                self.state.pharmacy_stats["consumidos"] += 1
                self.state.log("FARMACIA", f"{name} retiró un medicamento")
            except Exception:
                self.state.log("FARMACIA", f"{name} esperando (buffer vacío)")

    # ─── render ───

    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 690
        H = 240

        cap = self.state.PHARMACY_CAPACITY
        size = self.state.pharmacy_queue.qsize()

        # ─── visualización del buffer ───
        c.create_text(20, 16, anchor="nw",
                      text=f"📦  Buffer de medicamentos  ({size}/{cap})",
                      fill=FG, font=FONT_BIG)

        # estado del buffer
        if size == 0:
            badge_t, badge_c = "VACÍO", RED
        elif size >= cap:
            badge_t, badge_c = "LLENO", ORANGE
        else:
            badge_t, badge_c = "OK", GREEN
        c.create_rectangle(W - 90, 14, W - 14, 36,
                           fill=badge_c, outline="")
        c.create_text(W - 52, 25, text=badge_t,
                      fill="white", font=("Aptos", 10, "bold"))

        # slots del buffer
        slot_w = 56
        slot_h = 70
        gap = 8
        total_w = cap * slot_w + (cap - 1) * gap
        start_x = (W - total_w) // 2
        slot_y = 60

        for i in range(cap):
            x0 = start_x + i * (slot_w + gap)
            x1 = x0 + slot_w
            filled = i < size
            bg = "#ddd6fe" if filled else "#f3f4f6"
            bd = "#7c3aed" if filled else "#d1d5db"
            c.create_rectangle(x0, slot_y, x1, slot_y + slot_h,
                               fill=bg, outline=bd, width=2)
            if filled:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2,
                              text="💊", font=("Apple Color Emoji", 24))
            else:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2,
                              text="·", fill=SOFT, font=("Aptos", 20))

        # flechas productor / consumidor
        arrow_y = slot_y + slot_h + 26
        c.create_text(start_x - 8, arrow_y, anchor="e",
                      text="Productores →",
                      fill=GREEN, font=FONT_BOLD)
        c.create_text(start_x + total_w + 8, arrow_y, anchor="w",
                      text="→ Consumidores",
                      fill=BLUE, font=FONT_BOLD)

        # productores y consumidores
        prod_x = 40
        cons_x = W - 40
        actors_y = arrow_y + 20
        c.create_text(prod_x, actors_y, anchor="w",
                      text="👨‍🔬  Farmacéutico 1",
                      fill=FG, font=FONT)
        c.create_text(prod_x, actors_y + 18, anchor="w",
                      text="👨‍🔬  Farmacéutico 2",
                      fill=FG, font=FONT)
        c.create_text(cons_x, actors_y, anchor="e",
                      text="🧑‍⚕️  Enfermero 1", fill=FG, font=FONT)
        c.create_text(cons_x, actors_y + 18, anchor="e",
                      text="🧑‍⚕️  Enfermero 2", fill=FG, font=FONT)
        c.create_text(cons_x, actors_y + 36, anchor="e",
                      text="🧑‍⚕️  Enfermero 3", fill=FG, font=FONT)

        # status
        running = "● corriendo" if self.state.pharmacy_running else "○ detenido"
        running_c = GREEN if self.state.pharmacy_running else SOFT
        c.create_text(20, H - 10, anchor="sw",
                      text=running, fill=running_c, font=FONT_BOLD)

        prod_n = self.state.pharmacy_stats["producidos"]
        cons_n = self.state.pharmacy_stats["consumidos"]
        self.stats_var.set(
            f"Total producidos: {prod_n}    │    "
            f"Total consumidos: {cons_n}    │    "
            f"En buffer ahora: {size}/{cap}"
        )

        if self.alive:
            self.frame.after(200, self.refresh)