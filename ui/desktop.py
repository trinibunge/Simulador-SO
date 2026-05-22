import tkinter as tk
from ui.theme import *
from ui.topbar import TopBar
from ui.dock import Dock
from ui.toast import Toast
from ui.hospital_app import HospitalApp
from ui.readers_app import ReadersApp
from ui.terminal_app import TerminalApp
from ui.log_app import LogApp
from ui.snake_app import SnakeApp
from ui.ai_app import AIApp
from ui.pharmacy_app import PharmacyApp


class Desktop:
    def __init__(self, root, state):
        self.root = root
        self.state = state

        self.root.title("Hospital MS — Merecemos Sobresaliente")
        self.root.configure(bg=BG_BOTTOM)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.bg = tk.Canvas(root, bg=BG_BOTTOM, highlightthickness=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.draw_wallpaper()

        self.topbar = TopBar(root, state, self)
        self.dock = Dock(root, state, self)

        try:
            self.bg.lower(self.topbar.bar)
        except Exception:
            pass
        try:
            self.topbar.bar.lift()
            self.dock.frame.lift()
        except Exception:
            pass

        self.apps = {}
        Toast(self.root, "Bienvenido a Hospital MS", BLUE)

        self.build_dock()

    def _open(self, key, factory):
        existing = self.apps.get(key)
        if existing is not None and existing.alive and existing.frame.winfo_exists():
            existing.lift()
            return existing

        app = factory()
        self.apps[key] = app
        return app

    def shutdown(self):
        try:
            self.state.shutdown()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def draw_wallpaper(self):
        self.bg.delete("all")
        w, h = 1280, 720

        for y in range(h):
            t = y / h
            c = self.mix(BG_TOP, BG_BOTTOM, t)
            self.bg.create_line(0, y, w, y, fill=c)

        for x in range(48, w, 48):
            for y in range(48, h, 48):
                self.bg.create_oval(x - 1, y - 1, x + 1, y + 1,
                                    fill=DESKTOP_GRID, outline="")

        cx, cy = 1060, 560
        v, h2, t = 130, 72, 44
        wm = "#d4dce8"
        self.bg.create_rectangle(cx - t // 2, cy - v, cx + t // 2, cy + v,
                                 fill=wm, outline="")
        self.bg.create_rectangle(cx - h2, cy - t // 2, cx + h2, cy + t // 2,
                                 fill=wm, outline="")

        self.bg.create_text(18, 50, anchor="nw", fill=FG,
                            font=("Segoe UI", 13, "bold"),
                            text="Hospital MS")
        self.bg.create_text(18, 70, anchor="nw", fill=MUTED,
                            font=("Segoe UI", 9),
                            text="Simulador de Sistemas Operativos")

    def mix(self, c1, c2, t):
        def hx(c):
            return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = hx(c1), hx(c2)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % c

    def build_dock(self):
        self.dock.add_icon("Hospital", "assets/icons/hospital.png", self.open_hospital,
                           "Panel principal: procesos, CPUs y recursos compartidos")
        self.dock.add_icon("H. Clínica", "assets/icons/process.png", self.open_readers,
                           "Lectores y Escritores: historia clínica compartida")
        self.dock.add_icon("Recepción", "assets/icons/terminal.png", self.open_terminal,
                           "Terminal de comandos del sistema")
        self.dock.add_icon("Bitácora", "assets/icons/log.png", self.open_log,
                           "Eventos y logs del sistema")
        self.dock.add_icon("Farmacia", "assets/icons/pharmacy.png", self.open_pharmacy,
                           "Productor-Consumidor")
        self.dock.add_icon("Asistente", "assets/icons/ai.png", self.open_ai,
                           "Asistente médico")
        self.dock.add_icon("Snake", "assets/icons/snake.png", self.open_snake,
                           "Mini juego")

    def open_hospital(self):
        self._open("hospital", lambda: HospitalApp(self.root, self.state, 10, 40))

    def open_readers(self):
        self._open("readers", lambda: ReadersApp(self.root, self.state, 80, 60))

    def open_terminal(self):
        self._open("terminal", lambda: TerminalApp(self.root, self.state, 180, 470))

    def open_log(self):
        self._open("log", lambda: LogApp(self.root, self.state, 820, 40))

    def open_pharmacy(self):
        self._open("pharmacy", lambda: PharmacyApp(self.root, self.state, 380, 150))

    def open_ai(self):
        self._open("ai", lambda: AIApp(self.root, self.state, 460, 110))

    def open_snake(self):
        self._open("snake", lambda: SnakeApp(self.root, self.state, 420, 170))