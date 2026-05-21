import tkinter as tk
from ui.theme import *


class BootScreen:
    def __init__(self, root, on_done):
        self.root = root
        self.on_done = on_done

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.geometry("1280x720+0+0")
        self.win.configure(bg=BG_BOTTOM)

        self.canvas = tk.Canvas(self.win, bg=BG_BOTTOM, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.progress = 0
        self.draw()
        self.animate()

    def draw(self):
        self.canvas.delete("all")
        self.draw_bg()
        self.canvas.create_text(640, 170, text="La Catacumba", fill=FG, font=("Aptos", 32, "bold"))
        self.canvas.create_text(640, 214, text="Sistema operativo ficticio", fill=MUTED, font=("Aptos", 14))

        self.canvas.create_rectangle(340, 330, 940, 360, fill=PANEL_2, outline=BORDER, width=1)
        self.canvas.create_rectangle(340, 330, 340 + 6 * self.progress, 360, fill=BLUE, outline=BLUE)

        self.canvas.create_text(640, 395, text="Iniciando servicios del sistema", fill=FG, font=("Aptos", 11))
        self.canvas.create_text(640, 430, text="Kernel  Scheduler  Monitor  Terminal  Desktop", fill=SOFT, font=("Aptos", 10))

    def draw_bg(self):
        w = 1280
        h = 720
        for y in range(h):
            t = y / h
            c = self.mix(BG_TOP, BG_BOTTOM, t)
            self.canvas.create_line(0, y, w, y, fill=c)

    def mix(self, c1, c2, t):
        def hx(c): return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
        a = hx(c1)
        b = hx(c2)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % c

    def animate(self):
        if self.progress < 100:
            self.progress += 2
            self.draw()
            self.win.after(35, self.animate)
        else:
            self.win.after(200, self.finish)

    def finish(self):
        self.win.destroy()
        self.on_done()