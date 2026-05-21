import tkinter as tk
from ui.theme import *
from ui.topbar import TopBar
from ui.dock import Dock
from ui.toast import Toast
from ui.icons import make_icon
from ui.dungeon_app import DungeonApp
from ui.process_app import ProcessApp
from ui.terminal_app import TerminalApp
from ui.log_app import LogApp
from ui.snake_app import SnakeApp


class Desktop:
    def __init__(self, root, state):
        self.root = root
        self.state = state

        self.root.title("La Catacumba")
        self.root.configure(bg=BG_BOTTOM)

        self.canvas = tk.Canvas(root, bg=BG_BOTTOM, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.draw_wallpaper()
        self.create_icons()

        self.topbar = TopBar(root, state, self)
        self.dock = Dock(root, state, self)
        self.build_dock()

        Toast(self.root, "Bienvenido a La Catacumba", BLUE)

        self.open_dungeon()
        self.open_process()

    def draw_wallpaper(self):
        self.canvas.delete("all")
        w, h = 1280, 720
        for y in range(h):
            t = y / h
            c = self.mix(BG_TOP, BG_BOTTOM, t)
            self.canvas.create_line(0, y, w, y, fill=c)

        for x in range(0, w, 90):
            self.canvas.create_line(x, 0, x, h, fill=DESKTOP_GRID)
        for y in range(0, h, 90):
            self.canvas.create_line(0, y, w, y, fill=DESKTOP_GRID)

        self.canvas.create_text(58, 52, anchor="nw", fill=FG, font=("Aptos", 28, "bold"), text="La Catacumba")
        self.canvas.create_text(60, 92, anchor="nw", fill=MUTED, font=("Aptos", 12),
                                text="Sistema operativo ficticio para demo")

    def mix(self, c1, c2, t):
        def hx(c): return tuple(int(c[i:i+2], 16) for i in (1, 3, 5))
        a = hx(c1)
        b = hx(c2)
        c = tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))
        return "#%02x%02x%02x" % c

    def create_icons(self):
        box = tk.Frame(self.root, bg=BG_BOTTOM)
        box.place(x=60, y=170)

        items = [
            ("Dungeon", BLUE, self.open_dungeon),
            ("Procesos", PURPLE, self.open_process),
            ("Terminal", GREEN, self.open_terminal),
            ("Logs", TEAL, self.open_log),
            ("Snake", ORANGE, self.open_snake),
        ]

        for i, (title, color, cmd) in enumerate(items):
            icon = make_icon(box, title, color, cmd)
            icon.grid(row=i // 2, column=i % 2, padx=36, pady=28)

    def build_dock(self):
        self.dock.add_button("Dungeon", BLUE, self.open_dungeon)
        self.dock.add_button("Procesos", PURPLE, self.open_process)
        self.dock.add_button("Terminal", GREEN, self.open_terminal)
        self.dock.add_button("Logs", TEAL, self.open_log)
        self.dock.add_button("Snake", ORANGE, self.open_snake)

    def open_dungeon(self):
        if hasattr(self, "dungeon") and self.dungeon.frame.winfo_exists():
            self.dungeon.lift()
            return
        self.dungeon = DungeonApp(self.root, self.state, 260, 120)

    def open_process(self):
        if hasattr(self, "process") and self.process.frame.winfo_exists():
            self.process.lift()
            return
        self.process = ProcessApp(self.root, self.state, 760, 120)

    def open_terminal(self):
        if hasattr(self, "terminal") and self.terminal.frame.winfo_exists():
            self.terminal.lift()
            return
        self.terminal = TerminalApp(self.root, self.state, 180, 500)

    def open_log(self):
        if hasattr(self, "log") and self.log.frame.winfo_exists():
            self.log.lift()
            return
        self.log = LogApp(self.root, self.state, 880, 500)

    def open_snake(self):
        if hasattr(self, "snake") and self.snake.frame.winfo_exists():
            self.snake.lift()
            return
        self.snake = SnakeApp(self.root, self.state, 420, 170)