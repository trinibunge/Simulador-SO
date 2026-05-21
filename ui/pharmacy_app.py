import tkinter as tk
import threading
import time
import random
from ui.window_base import WindowBase
from ui.theme import *
from ui.toast import Toast


class PharmacyApp(WindowBase):
    def __init__(self, master, state, x=460, y=160):
        super().__init__(master, "Farmacia", PURPLE, 700, 500, x, y)
        self.state = state
        self.content.configure(bg=PANEL)

        self._producers = []
        self._consumers = []

        head = tk.Frame(self.content, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(14, 6))
        tk.Label(head, text="Farmacia — Productor / Consumidor", bg=PANEL, fg=FG, font=FONT_BIG).pack(anchor="w")
        tk.Label(head, text="Buffer acotado de medicamentos (capacidad 8)", bg=PANEL, fg=MUTED, font=FONT_ITALIC).pack(anchor="w")

        bar = tk.Frame(self.content, bg=PANEL)
        bar.pack(fill="x", padx=14, pady=(8, 8))

        tk.Button(bar, text="Iniciar", bg=GREEN, fg="white", relief="flat", padx=12, pady=7,
                  font=FONT_BOLD, cursor="hand2", command=self.start).pack(side="left", padx=3)
        tk.Button(bar, text="Detener", bg=RED, fg="white", relief="flat", padx=12, pady=7,
                  font=FONT_BOLD, cursor="hand2", command=self.stop).pack(side="left", padx=3)
        tk.Button(bar, text="+ 1", bg=BLUE, fg="white", relief="flat", padx=12, pady=7,
                  font=FONT_BOLD, cursor="hand2", command=self.produce_one).pack(side="left", padx=3)
        tk.Button(bar, text="- 1", bg=ORANGE, fg="white", relief="flat", padx=12, pady=7,
                  font=FONT_BOLD, cursor="hand2", command=self.consume_one).pack(side="left", padx=3)

        self.canvas = tk.Canvas(self.content, bg=PANEL, height=220, highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", padx=14, pady=(4, 8))

        self.stats_var = tk.StringVar()
        tk.Label(self.content, textvariable=self.stats_var, bg=PANEL, fg=MUTED, font=FONT_SM, anchor="w").pack(fill="x", padx=14, pady=(0, 12))

        self.refresh()

    def on_close(self):
        self.state.pharmacy_running = False

    def start(self):
        if self.state.pharmacy_running:
            return
        self.state.pharmacy_running = True
        self.state.log("FARMACIA", "Iniciando turno de producción")

        for i in range(2):
            t = threading.Thread(target=self._producer_loop, args=(f"Farmacéutico {i+1}",), daemon=True)
            t.start()
            self._producers.append(t)

        for i in range(3):
            t = threading.Thread(target=self._consumer_loop, args=(f"Enfermero {i+1}",), daemon=True)
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
            self.state.log("FARMACIA", "Buffer lleno")
            Toast(self.master, "Buffer lleno", ORANGE)

    def consume_one(self):
        try:
            self.state.pharmacy_queue.get_nowait()
            self.state.pharmacy_stats["consumidos"] += 1
            self.state.log("FARMACIA", "Medicamento consumido (manual)")
        except Exception:
            self.state.log("FARMACIA", "Buffer vacío")
            Toast(self.master, "Buffer vacío", ORANGE)

    def _producer_loop(self, name):
        while self.state.pharmacy_running and self.state.running:
            time.sleep(random.uniform(0.4, 1.2))
            if not self.state.pharmacy_running:
                break
            try:
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

    def refresh(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        c = self.canvas
        c.delete("all")
        W = c.winfo_width() or 680
        cap = self.state.PHARMACY_CAPACITY
        size = self.state.pharmacy_queue.qsize()

        c.create_text(10, 12, anchor="nw", text=f"Buffer de medicamentos ({size}/{cap})", fill=FG, font=FONT_BIG)

        if size == 0:
            badge_t, badge_c = "VACÍO", RED
        elif size >= cap:
            badge_t, badge_c = "LLENO", ORANGE
        else:
            badge_t, badge_c = "OK", GREEN

        c.create_rectangle(W - 90, 10, W - 14, 32, fill=badge_c, outline="")
        c.create_text(W - 52, 21, text=badge_t, fill="white", font=("Segoe UI", 10, "bold"))

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
            c.create_rectangle(x0, slot_y, x1, slot_y + slot_h, fill=bg, outline=bd, width=2)
            if filled:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2, text="💊", font=("Segoe UI Emoji", 20))
            else:
                c.create_text((x0 + x1) // 2, slot_y + slot_h // 2, text="·", fill=SOFT, font=("Segoe UI", 18))

        c.create_text(20, 184, anchor="w", text="Productores →", fill=GREEN, font=FONT_BOLD)
        c.create_text(W - 20, 184, anchor="e", text="→ Consumidores", fill=BLUE, font=FONT_BOLD)

        self.stats_var.set(
            f"Producidos: {self.state.pharmacy_stats['producidos']}    │    "
            f"Consumidos: {self.state.pharmacy_stats['consumidos']}    │    "
            f"En buffer: {size}/{cap}"
        )

        if self.alive:
            self.frame.after(200, self.refresh)