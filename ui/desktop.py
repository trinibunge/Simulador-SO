import os
import time
import locale
import tkinter as tk

from ui.theme import *
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
from ui.wordle_app import WordleApp


class Desktop:
    def __init__(self, root, state):
        self.root = root
        self.state = state

        self.root.title("Parte 3 obligatorio de Sistemas Operativos - Equipo: Bunge y López - Hospital MS (Merecemos sobresaliente)")
        self.root.configure(bg=BG_BOTTOM)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self._metrics_icon_path = self._ensure_metrics_icon()
        self._wordle_icon_path = self._ensure_wordle_icon()

        self.bg = tk.Canvas(root, bg=BG_BOTTOM, highlightthickness=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)

        for loc in ("es_AR.UTF-8", "es_ES.UTF-8", "es_UY.UTF-8", "Spanish_Argentina"):
            try:
                locale.setlocale(locale.LC_TIME, loc)
                break
            except locale.Error:
                continue

        # IMPORTANT: el topbar lo dejamos por compat con state.clock_tick, pero
        # ocultamos su texto principal porque el usuario lo encontró "poco aesthetic".
        # Para no romper imports y bindings, simplemente no lo packeamos.
        self.topbar = None

        self.dock = Dock(root, state, self)

        # Cachés de los widgets "en vivo" del wallpaper, para no destruir/recrear
        # cada 500ms (eso causaría parpadeo). Solo actualizamos los .config().
        self._stats_widgets = None
        self._wallpaper_drawn = False

        self.apps = {}
        Toast(self.root, "Bienvenido a Hospital MS", BLUE)

        self.build_dock()

        try:
            self.dock.frame.lift()
        except Exception:
            pass

        # Dos timers:
        #  - Wallpaper completo: cada 60s (no necesita redibujarse seguido)
        #  - Widget de stats: cada 500ms (los números deben sentirse vivos)
        self.draw_wallpaper()
        self.start_stats_refresh()
        self.start_clock_refresh()

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

    # ─────────────────────────────────────────────────────────────────
    #  Refrescos en vivo
    # ─────────────────────────────────────────────────────────────────

    def start_stats_refresh(self):
        """Actualiza solo los números del widget de stats — cada 500ms."""
        if not self.root.winfo_exists():
            return
        try:
            self._update_stats_values()
        except Exception:
            pass
        self.root.after(500, self.start_stats_refresh)

    def start_clock_refresh(self):
        """Actualiza el reloj/fecha del wallpaper — cada 30s."""
        if not self.root.winfo_exists():
            return
        try:
            self._update_clock()
        except Exception:
            pass
        self.root.after(30000, self.start_clock_refresh)

    # ─────────────────────────────────────────────────────────────────
    #  Wallpaper (se dibuja UNA vez, después solo se actualizan números)
    # ─────────────────────────────────────────────────────────────────

    def draw_wallpaper(self):
        self.bg.delete("all")
        w, h = 1280, 720

        # Gradiente vertical
        for y in range(0, h, 2):
            t = y / h
            c = self.mix(BG_TOP, BG_BOTTOM, t)
            self.bg.create_rectangle(0, y, w, y + 2, fill=c, outline=c)

        # Grilla de puntos
        for x in range(48, w, 48):
            for y in range(48, h, 48):
                self.bg.create_oval(x - 1, y - 1, x + 1, y + 1,
                                    fill=DESKTOP_GRID, outline="")

        # Cruz médica de marca de agua
        cx, cy = 1060, 540
        v, h2, t = 130, 72, 44
        wm = "#d4dce8"
        self.bg.create_rectangle(cx - t // 2, cy - v, cx + t // 2, cy + v,
                                 fill=wm, outline="")
        self.bg.create_rectangle(cx - h2, cy - t // 2, cx + h2, cy + t // 2,
                                 fill=wm, outline="")

        # Título principal — saludo de bienvenida
        self.bg.create_text(28, 60, anchor="nw", fill=FG,
                            font=("Segoe UI", 22, "bold"),
                            text="¡Bienvenido al Hospital MS!")
        self.bg.create_text(28, 108, anchor="nw", fill=MUTED,
                            font=("Segoe UI", 11),
                            text="Este simulador resuelve la parte 3 del obligatorio de Sistemas Operativos.")

        # Reloj/fecha — guardamos el id para actualizarlo después sin redibujar todo
        self._clock_id = self.bg.create_text(
            28, 138, anchor="nw", fill=SOFT,
            font=("Segoe UI", 10, "italic"),
            text=self._format_now(),
        )

        # Widgets
        self._build_stats_widget(28, 178, 320, 160)
        self._build_announcements(28, 360, 320, 260)

        # Créditos abajo a la derecha — un poco más grandes para que se lean
        self.bg.create_text(
            1252, 638, anchor="se", fill=MUTED,
            font=("Segoe UI", 11, "italic"),
            text="Realizado por: Trinidad Bunge y Maximiliano López",
        )

        # Hint inferior
        self.bg.create_text(640, 660, anchor="center", fill=MUTED,
                            font=("Segoe UI", 10, "italic"),
                            text="↓ Abrí las apps del Hospital desde el dock ↓")

        # Mantener dock arriba
        try:
            self.dock.frame.lift()
        except Exception:
            pass

        self._wallpaper_drawn = True

    def _format_now(self):
        try:
            return time.strftime("%A %d de %B · %H:%M").capitalize()
        except Exception:
            return time.strftime("%H:%M")

    def _update_clock(self):
        if self._wallpaper_drawn and hasattr(self, "_clock_id"):
            try:
                self.bg.itemconfig(self._clock_id, text=self._format_now())
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  Widget: Estado del hospital
    # ─────────────────────────────────────────────────────────────────

    def _build_stats_widget(self, x, y, w, h):
        """
        Dibuja el frame del widget UNA vez y guarda los IDs de los
        textos de valor, para actualizarlos en vivo sin redibujar.
        """
        # marco
        self.bg.create_rectangle(x, y, x + w, y + h,
                                 fill=PANEL, outline=BORDER, width=1)
        self.bg.create_rectangle(x, y, x + w, y + 3, fill=BLUE, outline="")

        # título
        self.bg.create_text(x + 18, y + 22, anchor="nw", fill=FG,
                            font=("Segoe UI", 12, "bold"),
                            text="Estado del hospital")

        # separador sutil bajo el título
        self.bg.create_line(x + 18, y + 52, x + w - 18, y + 52,
                            fill=BORDER_SOFT)

        # 2 filas, bien espaciadas y centradas verticalmente en el panel
        rows = [
            ("👤", "Pacientes en cuidado:", BLUE),
            ("📋", "Dados de alta:",   GREEN),
        ]
        value_ids = []
        # repartir las 2 filas en el alto disponible bajo el separador
        avail_top = y + 70
        avail_bot = y + h - 18
        row_h = (avail_bot - avail_top) // len(rows)
        for i, (emoji, label, color) in enumerate(rows):
            row_y = avail_top + i * row_h + row_h // 2
            # emoji
            self.bg.create_text(x + 24, row_y, anchor="w", fill=color,
                                font=("Segoe UI Emoji", 18), text=emoji)
            # label
            self.bg.create_text(x + 60, row_y, anchor="w", fill=MUTED,
                                font=("Segoe UI", 11), text=label)
            # valor a la derecha, grande
            value_id = self.bg.create_text(
                x + w - 22, row_y, anchor="e", fill=color,
                font=("Segoe UI", 22, "bold"), text="—",
            )
            value_ids.append(value_id)

        self._stats_widgets = {
            "patients": value_ids[0],
            "done":     value_ids[1],
        }
        self._update_stats_values()

    def _update_stats_values(self):
        """Lee el estado real y actualiza solo los números del widget."""
        if not self._stats_widgets:
            return
        try:
            with self.state.lock:
                pacientes_all = list(self.state.pacientes.values())
                n_done = len(self.state.completed_history)
            n_patient = sum(1 for p in pacientes_all
                            if getattr(p, "kind", "patient") == "patient")
        except Exception:
            n_patient = n_done = 0

        try:
            self.bg.itemconfig(self._stats_widgets["patients"], text=str(n_patient))
            self.bg.itemconfig(self._stats_widgets["done"],     text=str(n_done))
        except Exception:
            pass

    def _build_announcements(self, x, y, w, h):
        """Tarjeta de avisos, estilo memo."""
        self.bg.create_rectangle(x, y, x + w, y + h,
                                 fill="#fffbeb", outline="#fde68a", width=1)
        self.bg.create_rectangle(x, y, x + w, y + 3, fill=GOLD, outline="")

        self.bg.create_text(x + 14, y + 18, anchor="nw", fill=FG,
                            font=("Segoe UI", 11, "bold"),
                            text="Estimado/a Doctor/a, recuerde que:")

    
        notes = [
            ("🎮", "Puede jugar al Snake o Wordle si no está atendiendo ningún paciente."),
            ("⚕️", "Solo un paciente puede usar el Quirófano (y el Cirujano) a la vez."),
            ("⚠️", "Si dos pacientes se traban por recursos cruzados, deadlock detectado."),
            ("📋", "Toda actividad queda registrada en la Bitácora del sistema."),
        ]
        for i, (emoji, text) in enumerate(notes):
            row_y = y + 55 + i * 48
            self.bg.create_text(x + 14, row_y, anchor="nw", fill=GOLD,
                                font=("Segoe UI Emoji", 14), text=emoji)
            self.bg.create_text(x + 46, row_y + 2, anchor="nw", fill=FG,
                                font=("Segoe UI", 10),
                                text=text, width=w - 60)

    # ─────────────────────────────────────────────────────────────────
    #  Misc
    # ─────────────────────────────────────────────────────────────────

    def mix(self, c1, c2, t):
        def hx(c):
            return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = hx(c1), hx(c2)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % c

    def _ensure_metrics_icon(self):
        """Genera assets/icons/metrics.png si no existe."""
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

    def _ensure_wordle_icon(self):
        """Genera assets/icons/wordle.png si no existe — mini grilla estilo Wordle."""
        path = "assets/icons/wordle.png"
        if os.path.exists(path):
            return path
        try:
            from PIL import Image, ImageDraw
            os.makedirs(os.path.dirname(path), exist_ok=True)
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Fondo blanco con borde gris
            try:
                draw.rounded_rectangle((4, 4, size - 4, size - 4),
                                       radius=12, fill=(255, 255, 255, 255),
                                       outline=(210, 210, 210, 255), width=2)
            except AttributeError:
                draw.rectangle((4, 4, size - 4, size - 4),
                               fill=(255, 255, 255, 255))
            # 5 tiles miniatura: verde verde amarillo vacío vacío
            tile_size = 9
            gap = 2
            total_w = 5 * tile_size + 4 * gap
            base_x = (size - total_w) // 2
            base_y = (size - tile_size) // 2 + 2
            tiles = [
                ((106, 170, 100, 255), (106, 170, 100, 255)),  # verde
                ((106, 170, 100, 255), (106, 170, 100, 255)),  # verde
                ((201, 180, 88, 255),  (201, 180, 88, 255)),   # amarillo
                ((255, 255, 255, 255), (180, 180, 180, 255)),  # vacío
                ((255, 255, 255, 255), (180, 180, 180, 255)),  # vacío
            ]
            for i, (fill, outline) in enumerate(tiles):
                x0 = base_x + i * (tile_size + gap)
                draw.rectangle((x0, base_y, x0 + tile_size, base_y + tile_size),
                               fill=fill, outline=outline)
            # Línea decorativa arriba simulando otra fila
            draw.rectangle((base_x, base_y - 14, base_x + total_w, base_y - 11),
                           fill=(106, 170, 100, 255))
            img.save(path)
            return path
        except Exception:
            return "assets/icons/snake.png"

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
                           "Asistente médico")
        self.dock.add_icon("Snake", "assets/icons/snake.png", self.open_snake,
                           "Juego Snake")
        self.dock.add_icon("Wordle", self._wordle_icon_path, self.open_wordle,
                           "Wordle en español")

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

    def open_wordle(self):
        self._open("wordle", lambda: WordleApp(self.root, self.state, 440, 120))