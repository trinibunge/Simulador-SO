import os
import time
import locale
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
from ui.metrics_app import MetricsApp


class Desktop:
    def __init__(self, root, state):
        self.root = root
        self.state = state

        self.root.title("Hospital MS — Merecemos Sobresaliente")
        self.root.configure(bg=BG_BOTTOM)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        # Asegurar ícono de métricas (se genera al vuelo si no existe)
        self._metrics_icon_path = self._ensure_metrics_icon()

        self.bg = tk.Canvas(root, bg=BG_BOTTOM, highlightthickness=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        # Forzar locale español para fecha (puede no estar disponible — no crítico)
        for loc in ("es_AR.UTF-8", "es_ES.UTF-8", "es_UY.UTF-8", "Spanish_Argentina"):
            try:
                locale.setlocale(locale.LC_TIME, loc)
                break
            except locale.Error:
                continue

        self.topbar = TopBar(root, state, self)
        self.dock = Dock(root, state, self)

        self.apps = {}
        Toast(self.root, "Bienvenido a Hospital MS", BLUE)

        self.build_dock()

        try:
            self.bg.lower(self.topbar.bar)
        except Exception:
            pass
        try:
            self.topbar.bar.lift()
            self.dock.frame.lift()
        except Exception:
            pass

        self.start_wallpaper_refresh()

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

    def start_wallpaper_refresh(self):
        """Redibuja el wallpaper cada 2s para que los stats estén vivos."""
        if not self.root.winfo_exists():
            return
        try:
            self.draw_wallpaper()
            # Mantener topbar/dock por encima del canvas redibujado
            try:
                self.topbar.bar.lift()
            except Exception:
                pass
            try:
                self.dock.frame.lift()
            except Exception:
                pass
        except Exception:
            pass
        self.root.after(2000, self.start_wallpaper_refresh)

    def draw_wallpaper(self):
        self.bg.delete("all")
        w, h = 1280, 720

        # Gradiente vertical
        for y in range(0, h, 2):  # cada 2px para acelerar
            t = y / h
            c = self.mix(BG_TOP, BG_BOTTOM, t)
            self.bg.create_rectangle(0, y, w, y + 2, fill=c, outline=c)

        # Grilla de puntos
        for x in range(48, w, 48):
            for y in range(48, h, 48):
                self.bg.create_oval(x - 1, y - 1, x + 1, y + 1,
                                    fill=DESKTOP_GRID, outline="")

        # Cruz médica de marca de agua (esquina inferior derecha)
        cx, cy = 1060, 540
        v, h2, t = 130, 72, 44
        wm = "#d4dce8"
        self.bg.create_rectangle(cx - t // 2, cy - v, cx + t // 2, cy + v,
                                 fill=wm, outline="")
        self.bg.create_rectangle(cx - h2, cy - t // 2, cx + h2, cy + t // 2,
                                 fill=wm, outline="")

        # Título principal
        self.bg.create_text(28, 60, anchor="nw", fill=FG,
                            font=("Segoe UI", 22, "bold"),
                            text="Hospital MS")
        self.bg.create_text(28, 94, anchor="nw", fill=MUTED,
                            font=("Segoe UI", 11),
                            text="Tercera y cuarta parte del obligatorio de Sistemas Operativos")

       
        try:
            now_str = time.strftime("%A %d de %B · %H:%M").capitalize()
        except Exception:
            now_str = time.strftime("%H:%M")
        self.bg.create_text(28, 124, anchor="nw", fill=SOFT,
                            font=("Segoe UI", 10, "italic"),
                            text=now_str)

        # Widgets en vivo
        self._draw_stats_widget(28, 165, 320, 200)
        self._draw_announcements(28, 390, 320, 250)

        # Hint inferior
        self.bg.create_text(640, 660, anchor="center", fill=MUTED,
                            font=("Segoe UI", 10, "italic"),
                            text="↓ Abrí las apps del Hospital desde el dock ↓")

    def _draw_stats_widget(self, x, y, w, h):
        """Tarjeta con stats en vivo del hospital."""
        self.bg.create_rectangle(x, y, x + w, y + h,
                                 fill=PANEL, outline=BORDER, width=1)
        self.bg.create_rectangle(x, y, x + w, y + 3,
                                 fill=BLUE, outline="")

        self.bg.create_text(x + 14, y + 18, anchor="nw", fill=FG,
                            font=("Segoe UI", 11, "bold"),
                            text="Estado del hospital")
        self.bg.create_text(x + 14, y + 36, anchor="nw", fill=SOFT,
                            font=("Segoe UI", 9, "italic"),
                            text="datos en vivo del kernel")

        # Datos reales
        try:
            with self.state.lock:
                pacientes_all = list(self.state.pacientes.values())
                n_done = len(self.state.completed_history)
            n_patient = sum(1 for p in pacientes_all if getattr(p, "kind", "patient") == "patient")
            n_apps = sum(1 for p in pacientes_all if getattr(p, "kind", "patient") == "app")
            n_running = sum(1 for p in pacientes_all if p.state == "RUNNING")
        except Exception:
            n_patient = n_apps = n_running = n_done = 0

        rows = [
            ("👤  Pacientes vivos", str(n_patient), BLUE),
            ("🖥️  Apps abiertas", str(n_apps), PURPLE),
            ("⚕️  En atención", str(n_running), GREEN),
            ("📋  Atendidos hoy", str(n_done), MUTED),
        ]
        for i, (label, val, color) in enumerate(rows):
            row_y = y + 70 + i * 30
            self.bg.create_text(x + 14, row_y, anchor="nw", fill=SOFT,
                                font=("Segoe UI", 10), text=label)
            self.bg.create_text(x + w - 14, row_y, anchor="ne", fill=color,
                                font=("Segoe UI", 12, "bold"), text=val)

    def _draw_announcements(self, x, y, w, h):
        """Tarjeta de avisos del hospital, estilo memo."""
        self.bg.create_rectangle(x, y, x + w, y + h,
                                 fill="#fffbeb", outline="#fde68a", width=1)
        self.bg.create_rectangle(x, y, x + w, y + 3, fill=GOLD, outline="")

        self.bg.create_text(x + 14, y + 18, anchor="nw", fill=FG,
                            font=("Segoe UI", 11, "bold"),
                            text="Avisos de guardia")

        notes = [
            ("📌", "¡Juegue al Snake mientras decide que hacer!"),
            ("⚕️", "Solo un paciente puede usar el Quirófano (y el Cirujano) a la vez."),
            ("⚠️", "Si dos pacientes se traban por recursos cruzados, deadlock detectado."),
            ("📋", "Toda actividad queda registrada en la Bitácora del sistema."),
        ]
        for i, (emoji, text) in enumerate(notes):
            row_y = y + 55 + i * 46
            self.bg.create_text(x + 14, row_y, anchor="nw", fill=GOLD,
                                font=("Segoe UI", 14), text=emoji)
            self.bg.create_text(x + 46, row_y + 2, anchor="nw", fill=FG,
                                font=("Segoe UI", 10),
                                text=text, width=w - 60)

    def mix(self, c1, c2, t):
        def hx(c):
            return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = hx(c1), hx(c2)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % c


    def _ensure_metrics_icon(self):
        """
        Genera assets/icons/metrics.png si no existe, dibujando 3 barras
        ascendentes sobre fondo púrpura. Devuelve el path final a usar.
        """
        path = "assets/icons/metrics.png"
        if os.path.exists(path):
            return path

        try:
            from PIL import Image, ImageDraw
            os.makedirs(os.path.dirname(path), exist_ok=True)
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
    
            try:
                draw.rounded_rectangle((4, 4, size - 4, size - 4),
                                       radius=12, fill=(109, 40, 217, 255))
            except AttributeError:
            
                draw.rectangle((4, 4, size - 4, size - 4),
                               fill=(109, 40, 217, 255))
        
            bar_w = 9
            gap = 5
            base_x = 14
            base_y = size - 14
            for i, h in enumerate([16, 24, 32]):
                x0 = base_x + i * (bar_w + gap)
                draw.rectangle((x0, base_y - h, x0 + bar_w, base_y),
                               fill=(255, 255, 255, 240))
            img.save(path)
            return path
        except Exception:
            
            return "assets/icons/hospital.png"

    # ─────────────────────────────────────────────────────────────────
    #  Dock
    # ─────────────────────────────────────────────────────────────────

    def build_dock(self):
        self.dock.add_icon("Hospital", "assets/icons/hospital.png", self.open_hospital,
                           "Panel principal: procesos, CPUs y recursos compartidos")
        self.dock.add_icon("H. Clínica", "assets/icons/process.png", self.open_readers,
                           "Lectores y Escritores: historia clínica compartida")
        self.dock.add_icon("Recepción", "assets/icons/terminal.png", self.open_terminal,
                           "Terminal de comandos del sistema")
        self.dock.add_icon("Bitácora", "assets/icons/log.png", self.open_log,
                           "Eventos y logs del sistema (proceso aparte vía IPC)")
        self.dock.add_icon("Farmacia", "assets/icons/pharmacy.png", self.open_pharmacy,
                           "Productor-Consumidor con buffer acotado")
        self.dock.add_icon("Métricas", self._metrics_icon_path, self.open_metrics,
                           "Estadísticas reales de scheduling")
        self.dock.add_icon("Asistente", "assets/icons/ai.png", self.open_ai,
                           "Asistente médico (corre como proceso)")
        self.dock.add_icon("Snake", "assets/icons/snake.png", self.open_snake,
                           "Juego Snake (corre como proceso)")

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

    def open_metrics(self):
        self._open("metrics", lambda: MetricsApp(self.root, self.state, 200, 100))

    def open_ai(self):
        self._open("ai", lambda: AIApp(self.root, self.state, 460, 110))

    def open_snake(self):
        self._open("snake", lambda: SnakeApp(self.root, self.state, 420, 170))