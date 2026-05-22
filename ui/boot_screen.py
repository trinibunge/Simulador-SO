"""
Boot screen del Hospital MS — estilo dmesg / POST.

Muestra el logo, una "terminal de arranque" con mensajes técnicos que van
apareciendo (cargando módulos del kernel, montando recursos, etc.) y una
barra de progreso.  Los mensajes reflejan lo que de hecho ocurre cuando el
HospitalState se construye: primitivas de sincronización adquiridas, el
demonio de logging arrancado, hilos del kernel iniciados.
"""

import math
import os
import time
import tkinter as tk

# ── Paleta del boot ──
BG_TOP       = "#04070d"
BG_BOTTOM    = "#0a1428"
RING_DIM     = "#1a2d45"
ACCENT       = "#2563eb"
ACCENT_LT    = "#3b82f6"
ACCENT_GLOW  = "#60a5fa"

TEXT_MAIN    = "#e6f0ff"
TEXT_SUB     = "#7290b8"
TEXT_DIM     = "#3a557a"
TEXT_GREEN   = "#34d399"   # [ OK ]
TEXT_AMBER   = "#fbbf24"   # info
TEXT_RED     = "#f87171"   # warn (no la usamos pero queda en paleta)
TERM_BG      = "#070d18"
TERM_BORDER  = "#10243f"

WINDOW_W = 1280
WINDOW_H = 720


class BootScreen:
    """
    Pantalla de boot estilo dmesg.

    - logo HOSPITAL MS arriba (cruz + texto)
    - "terminal" central con líneas que aparecen secuencialmente
    - barra de progreso al pie
    - duración total ~3.5s

    Si se le pasa `state`, los mensajes incluyen datos reales (PID del
    demonio de logging, número de CPUs, etc.).
    """

    LINE_DELAY_MS = 90    # tiempo entre líneas
    HOLD_AT_END_MS = 600  # pausa al final, antes de soltar el callback

    def __init__(self, root, on_done, state=None):
        self.root = root
        self.on_done = on_done
        self.state = state
        self.t0 = time.time()

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.geometry(f"{WINDOW_W}x{WINDOW_H}+0+0")
        self.win.configure(bg=BG_BOTTOM)

        self.canvas = tk.Canvas(self.win, bg=BG_BOTTOM, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # ── elementos persistentes ──
        self._term_text_ids: list = []     # ids del canvas para mover/scrollear
        self._line_count = 0               # número de líneas actualmente visibles
        self._stage = ""
        self._stage_id = None
        self._bar_filled_id = None
        self._bar_w = 480
        self._progress = 0
        self._heart_phase = 0.0

        # ── secuencia de mensajes ──
        self._messages = self._build_messages()
        self._msg_idx = 0
        self._done = False

        self._draw_background()
        self._draw_logo()
        self._draw_terminal_frame()
        self._draw_footer()

        # arranca el desfile
        self.win.after(150, self._next_message)
        self._animate_heart()

    # ─────────────────────────────────────────────────────────────────
    #  Construcción de la lista de mensajes
    # ─────────────────────────────────────────────────────────────────

    def _build_messages(self):
        """
        Cada mensaje es (texto_principal, status_tag).
        Si status_tag es None, no se muestra status a la derecha.
        Tags válidos: "OK", "INFO", "WAIT", None.
        """
        # Si tengo state, uso datos reales del kernel
        num_cpus = getattr(self.state, "num_cpus", 1) if self.state else 1
        ram = getattr(self.state, "ram_limit", 12) if self.state else 12
        log_pid = "—"
        try:
            if self.state and getattr(self.state, "log_process", None):
                log_pid = str(self.state.log_process.pid)
        except Exception:
            pass

        return [
            ("Hospital MS Operating System v1.0", None),
            ("Copyright (c) 2026 — Maximiliano López & Trinidad Bunge", None),
            ("", None),
            ("CPU                : 1 doctor de guardia  (simulado)", "OK"),
            (f"Memory             : {ram} camas disponibles", "OK"),
            ("Arch               : python-{}+tk".format(self._py_ver()), "OK"),
            ("", None),
            ("Initializing kernel data structures", "OK"),
            ("Loading synchronization primitives:", None),
            ("  + RLock acquired for global state", "OK"),
            (f"  + Semaphore(N={num_cpus}) ready for CPU pool", "OK"),
            ("  + Lock(QUIROFANO), Lock(CIRUJANO) created", "OK"),
            ("  + Condition variable bound to ready queue", "OK"),
            ("", None),
            (f"Forking logd daemon (PID={log_pid})", "OK"),
            ("  + IPC channel up (multiprocessing.Queue)", "OK"),
            ("  + journal: ./hospital.log", "OK"),
            ("", None),
            ("Starting kernel threads:", None),
            ("  + scheduler            (Round Robin + Priority)", "OK"),
            ("  + deadlock_detector    (DFS / wait-for graph)", "OK"),
            ("", None),
            ("Mounting shared resources:", None),
            ("  + /dev/quirofano", "OK"),
            ("  + /dev/cirujano", "OK"),
            ("", None),
            ("Loading subsystems:", None),
            ("  + farmacia       (producer / consumer)", "OK"),
            ("  + recepcion      (command interpreter)", "OK"),
            ("  + bitacora       (live event log)", "OK"),
            ("", None),
            ("Hospital MS ready.  Welcome.", "OK"),
        ]

    def _py_ver(self):
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}"

    # ─────────────────────────────────────────────────────────────────
    #  Fondo
    # ─────────────────────────────────────────────────────────────────

    def _draw_background(self):
        c = self.canvas
        # gradient
        for y in range(WINDOW_H):
            t = y / WINDOW_H
            col = self._mix(BG_TOP, BG_BOTTOM, t)
            c.create_line(0, y, WINDOW_W, y, fill=col, tags="bg")
        # punto-grilla sutil
        for x in range(40, WINDOW_W, 40):
            for y in range(40, WINDOW_H, 40):
                c.create_oval(x - 1, y - 1, x + 1, y + 1,
                              fill="#0e1a2c", outline="", tags="bg")

    # ─────────────────────────────────────────────────────────────────
    #  Logo y cruz médica
    # ─────────────────────────────────────────────────────────────────

    def _draw_logo(self):
        c = self.canvas
        cx, cy = 640, 90

        # anillo de fondo (estático)
        r = 28
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      outline=ACCENT_LT, width=2, tags="logo_ring")

        # cruz médica chiquita centrada en (cx, cy)
        v, h, t = 14, 8, 5
        c.create_rectangle(cx - t // 2, cy - v, cx + t // 2, cy + v,
                           fill=ACCENT_LT, outline="", tags="logo_cross")
        c.create_rectangle(cx - h, cy - t // 2, cx + h, cy + t // 2,
                           fill=ACCENT_LT, outline="", tags="logo_cross")

        # texto del logo a la derecha
        c.create_text(cx + 50, cy - 6, anchor="w",
                      text="HOSPITAL MS",
                      fill=TEXT_MAIN, font=("Segoe UI", 26, "bold"),
                      tags="logo_text")
        c.create_text(cx + 50, cy + 18, anchor="w",
                      text="Sistema Operativo · Merecemos Sobresaliente",
                      fill=TEXT_SUB, font=("Segoe UI", 11),
                      tags="logo_text")

    def _animate_heart(self):
        """Pequeño 'pulso' del anillo del logo, como un latido."""
        if self._done:
            return
        c = self.canvas
        self._heart_phase += 0.10
        scale = 1.0 + 0.06 * math.sin(self._heart_phase)
        r = 28 * scale
        cx, cy = 640, 90
        c.coords("logo_ring", cx - r, cy - r, cx + r, cy + r)
        # color del anillo cicla suave entre dos tonos
        blend = (math.sin(self._heart_phase * 0.7) + 1) * 0.5
        col = self._mix(ACCENT, ACCENT_GLOW, blend)
        c.itemconfig("logo_ring", outline=col)
        self.win.after(40, self._animate_heart)

    # ─────────────────────────────────────────────────────────────────
    #  Terminal de boot
    # ─────────────────────────────────────────────────────────────────

    TERM_X = 290
    TERM_Y = 175
    TERM_W = 700
    TERM_H = 410
    LINE_H = 19
    MAX_VISIBLE_LINES = 19

    def _draw_terminal_frame(self):
        c = self.canvas
        x0, y0 = self.TERM_X, self.TERM_Y
        x1, y1 = x0 + self.TERM_W, y0 + self.TERM_H

        # marco
        c.create_rectangle(x0, y0, x1, y1,
                           fill=TERM_BG, outline=TERM_BORDER, width=1,
                           tags="term_frame")

        # barra superior estilo terminal
        c.create_rectangle(x0, y0, x1, y0 + 24,
                           fill="#0d1a2c", outline=TERM_BORDER, width=1,
                           tags="term_frame")
        # 3 puntos a la izquierda
        for i, col in enumerate(["#f87171", "#fbbf24", "#34d399"]):
            cx_ = x0 + 14 + i * 14
            cy_ = y0 + 12
            c.create_oval(cx_ - 4, cy_ - 4, cx_ + 4, cy_ + 4,
                          fill=col, outline="", tags="term_frame")
        # título
        c.create_text(x0 + self.TERM_W // 2, y0 + 12,
                      text="kernel@hospital-ms:~  $ dmesg --boot",
                      fill=TEXT_SUB, font=("Consolas", 10),
                      tags="term_frame")

    def _term_origin_y(self):
        # primera línea: justo debajo de la barra superior + padding
        return self.TERM_Y + 24 + 12

    def _add_line(self, text, status):
        """Agrega una línea a la terminal. Maneja scroll si se desborda."""
        c = self.canvas

        # Si llegamos al límite visible, scrolleamos todo hacia arriba
        if self._line_count >= self.MAX_VISIBLE_LINES:
            for tid in self._term_text_ids:
                c.move(tid, 0, -self.LINE_H)
            top_y = self._term_origin_y() - self.LINE_H * 0.5
            keep = []
            for tid in self._term_text_ids:
                try:
                    coords = c.coords(tid)
                    ty = coords[1] if len(coords) > 1 else 0
                except Exception:
                    ty = 0
                if ty < top_y:
                    c.delete(tid)
                else:
                    keep.append(tid)
            self._term_text_ids = keep
            self._line_count -= 1

        # posición de la nueva línea
        y = self._term_origin_y() + self._line_count * self.LINE_H
        self._line_count += 1
        x_text = self.TERM_X + 16
        x_status = self.TERM_X + self.TERM_W - 16

        # timestamp estilo dmesg
        ts = time.time() - self.t0
        ts_str = f"[{ts:7.3f}]"

        # cuerpo
        full = f"{ts_str}  {text}" if text else ""
        tid_text = c.create_text(
            x_text, y, anchor="w",
            text=full,
            fill=TEXT_MAIN if text else TEXT_DIM,
            font=("Consolas", 10),
        )
        self._term_text_ids.append(tid_text)

        # status a la derecha
        if status:
            color, label = {
                "OK":   (TEXT_GREEN, "[  OK  ]"),
                "INFO": (TEXT_AMBER, "[ INFO ]"),
                "WAIT": (TEXT_AMBER, "[ WAIT ]"),
            }.get(status, (TEXT_SUB, f"[ {status} ]"))
            tid_status = c.create_text(
                x_status, y, anchor="e",
                text=label,
                fill=color,
                font=("Consolas", 10, "bold"),
            )
            self._term_text_ids.append(tid_status)

    # ─────────────────────────────────────────────────────────────────
    #  Footer: barra de progreso + texto de etapa
    # ─────────────────────────────────────────────────────────────────

    def _draw_footer(self):
        c = self.canvas
        # barra
        bx = (WINDOW_W - self._bar_w) // 2
        by = 635
        c.create_rectangle(bx, by, bx + self._bar_w, by + 3,
                           fill="#0c1a2e", outline="", tags="bar_track")
        self._bar_filled_id = c.create_rectangle(
            bx, by, bx, by + 3, fill=ACCENT_LT, outline="", tags="bar_fill"
        )
        # etapa
        self._stage_id = c.create_text(
            WINDOW_W // 2, 660,
            text="Iniciando kernel...",
            fill=TEXT_SUB, font=("Segoe UI", 10),
            tags="stage",
        )
        # pie
        c.create_text(
            WINDOW_W // 2, 690,
            text="presione cualquier instante  ·  el sistema lo hará por usted",
            fill=TEXT_DIM, font=("Segoe UI", 9, "italic"),
        )

    def _update_progress(self, ratio: float, stage: str):
        ratio = max(0.0, min(1.0, ratio))
        c = self.canvas
        bx = (WINDOW_W - self._bar_w) // 2
        by = 635
        filled = int(self._bar_w * ratio)
        c.coords(self._bar_filled_id, bx, by, bx + filled, by + 3)
        if stage != self._stage:
            self._stage = stage
            c.itemconfig(self._stage_id, text=stage)

    # ─────────────────────────────────────────────────────────────────
    #  Loop de mensajes
    # ─────────────────────────────────────────────────────────────────

    def _stage_for(self, idx: int) -> str:
        # mapeo idx -> texto de etapa, fácil de leer al pie
        if idx < 4:
            return "Detectando hardware..."
        if idx < 8:
            return "Inicializando primitivas de sincronización..."
        if idx < 14:
            return "Arrancando demonio de logging..."
        if idx < 18:
            return "Levantando hilos del kernel..."
        if idx < 22:
            return "Montando recursos compartidos..."
        if idx < 29:
            return "Cargando subsistemas..."
        return "Sistema operativo listo."

    def _next_message(self):
        if self._msg_idx >= len(self._messages):
            self._update_progress(1.0, self._stage_for(self._msg_idx))
            self.win.after(self.HOLD_AT_END_MS, self._finish)
            return

        text, status = self._messages[self._msg_idx]
        self._add_line(text, status)

        self._msg_idx += 1
        ratio = self._msg_idx / max(1, len(self._messages))
        self._update_progress(ratio, self._stage_for(self._msg_idx))

        # variar un poco el delay para que no sea robótico
        # las líneas vacías son rápidas; las que tienen status, un poco más lentas
        delay = self.LINE_DELAY_MS
        if status:
            delay += 35
        if text == "":
            delay = 50

        self.win.after(delay, self._next_message)

    # ─────────────────────────────────────────────────────────────────
    #  Final
    # ─────────────────────────────────────────────────────────────────

    def _finish(self):
        if self._done:
            return
        self._done = True
        # mini fade-out: oscurecer el canvas
        self._fade_out(steps=10, step=0)

    def _fade_out(self, steps: int, step: int):
        if step >= steps:
            try:
                self.win.destroy()
            except Exception:
                pass
            self.on_done()
            return
        # superponer un overlay negro semitransparente "fake"
        alpha = (step + 1) / steps
        try:
            self.win.attributes("-alpha", max(0.0, 1.0 - alpha))
        except Exception:
            pass
        self.win.after(35, lambda: self._fade_out(steps, step + 1))

    # ─────────────────────────────────────────────────────────────────
    #  Util
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _mix(c1, c2, t):
        def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = hx(c1), hx(c2)
        r = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % r