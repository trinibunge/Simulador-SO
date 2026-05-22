import tkinter as tk
import math

DARK_BG   = "#070e1a"
DARK_MID  = "#0c1726"
RING_DIM  = "#1a2d45"
ACCENT    = "#2563eb"
ACCENT_LT = "#3b82f6"
TEXT_MAIN = "#dce8f8"
TEXT_SUB  = "#2d4460"
TEXT_DIM  = "#1e3050"

STAGES = ["Kernel", "Planificador", "Monitor", "Terminal", "Escritorio"]


class BootScreen:
    def __init__(self, root, on_done):
        self.root = root
        self.on_done = on_done

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.geometry("1280x720+0+0")
        self.win.configure(bg=DARK_BG)

        self.canvas = tk.Canvas(self.win, bg=DARK_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.progress = 0
        self._draw_static()
        self.draw()
        self.animate()

    def _draw_static(self):
        c = self.canvas
        # gradient background
        for y in range(720):
            t = y / 720
            col = self._mix(DARK_BG, DARK_MID, t)
            c.create_line(0, y, 1280, y, fill=col, tags="bg")
        # dot grid
        for x in range(80, 1280, 80):
            for y in range(60, 720, 80):
                c.create_oval(x - 1, y - 1, x + 1, y + 1,
                              fill="#111e30", outline="", tags="bg")
        # separating line above bar area
        c.create_line(440, 502, 840, 502, fill=TEXT_DIM, tags="bg")

    def draw(self):
        c = self.canvas
        c.delete("dynamic")
        self._draw_ring(c)
        self._draw_cross(c)
        self._draw_text(c)
        self._draw_bar(c)

    def _draw_ring(self, c):
        cx, cy, r = 640, 275, 74
        c.create_oval(cx - r, cy - r, cx + r, cy + r,
                      outline=RING_DIM, width=2, tags="dynamic")
        if self.progress > 0:
            extent = min(359.9, self.progress * 3.6)
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=90, extent=-extent,
                         outline=ACCENT, width=3, style="arc", tags="dynamic")
            angle = math.radians(90 - extent)
            tx = cx + r * math.cos(angle)
            ty = cy - r * math.sin(angle)
            c.create_oval(tx - 4, ty - 4, tx + 4, ty + 4,
                          fill=ACCENT_LT, outline="", tags="dynamic")

    def _draw_cross(self, c):
        cx, cy = 640, 275
        v, h, t = 24, 13, 7
        c.create_rectangle(cx - t // 2, cy - v, cx + t // 2, cy + v,
                           fill=ACCENT, outline="", tags="dynamic")
        c.create_rectangle(cx - h, cy - t // 2, cx + h, cy + t // 2,
                           fill=ACCENT, outline="", tags="dynamic")

    def _draw_text(self, c):
        c.create_text(640, 386, text="HOSPITAL MS",
                      fill=TEXT_MAIN, font=("Segoe UI", 34, "bold"),
                      tags="dynamic")
        c.create_text(640, 424, text="Merecemos Sobresaliente",
                      fill=TEXT_SUB, font=("Segoe UI", 12),
                      tags="dynamic")
        idx = min(int(self.progress / 21), len(STAGES) - 1)
        c.create_text(640, 518, text=f"Iniciando {STAGES[idx]}...",
                      fill=TEXT_DIM, font=("Segoe UI", 10),
                      tags="dynamic")

    def _draw_bar(self, c):
        bw, bh = 400, 2
        bx, by = 440, 500
        c.create_rectangle(bx, by, bx + bw, by + bh,
                           fill="#0e1e30", outline="", tags="dynamic")
        filled = int(bw * self.progress / 100)
        if filled > 0:
            c.create_rectangle(bx, by, bx + filled, by + bh,
                               fill=ACCENT, outline="", tags="dynamic")

    def _mix(self, c1, c2, t):
        def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = hx(c1), hx(c2)
        r = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % r

    def animate(self):
        if self.progress < 100:
            self.progress += 2
            self.draw()
            self.win.after(35, self.animate)
        else:
            self.win.after(300, self.finish)

    def finish(self):
        self.win.destroy()
        self.on_done()
