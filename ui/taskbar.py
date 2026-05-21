import tkinter as tk
from ui.theme import *
from ui.toast import Toast


class Taskbar:
    def __init__(self, master, state, desktop):
        self.master = master
        self.state = state
        self.desktop = desktop

        self.bar = tk.Frame(master, bg=PANEL, height=46, highlightthickness=1, highlightbackground=BORDER)
        self.bar.pack(side="bottom", fill="x")

        self.start_btn = tk.Button(
            self.bar, text="☰ Inicio", bg=TITLE_BG, fg=FG,
            font=FONT_BOLD, relief="flat", command=self.toggle_menu,
            activebackground=BORDER, activeforeground=FG
        )
        self.start_btn.pack(side="left", padx=8, pady=7)

        self.quick = tk.Frame(self.bar, bg=PANEL)
        self.quick.pack(side="left", padx=8)

        self.status = tk.Label(self.bar, text="Hospital MS listo", bg=PANEL, fg=MUTED, font=FONT)
        self.status.pack(side="left", padx=12)

        self.clock = tk.Label(self.bar, text="00:00", bg=PANEL, fg=CYAN, font=FONT_BOLD)
        self.clock.pack(side="right", padx=14)

        self.power_btn = tk.Button(
            self.bar, text="⏻", bg=PANEL, fg=RED, font=("Consolas", 12, "bold"),
            relief="flat", command=self.fake_power
        )
        self.power_btn.pack(side="right", padx=6)

        self.menu = None
        self.menu_open = False

        self.refresh()

    def fake_power(self):
        Toast(self.master, "Apagado simulado. Hospital MS sigue corriendo en tu imaginación.", RED)

    def toggle_menu(self):
        if self.menu_open:
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self):
        if self.menu:
            return
        self.menu_open = True
        self.menu = tk.Frame(self.master, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.menu.place(x=10, y=self.master.winfo_height()-320, width=280, height=280)

        tk.Label(self.menu, text="HOSPITAL MS", bg=PANEL, fg=PURPLE, font=FONT_BOLD).pack(pady=(10, 6))

        items = [
            ("🗺️ Dungeon View", self.desktop.open_dungeon),
            ("📊 Process Monitor", self.desktop.open_process),
            ("💻 Terminal", self.desktop.open_terminal),
            ("📜 Kernel Log", self.desktop.open_log),
            ("🥚 Snake.exe", self.desktop.open_snake),
        ]
        for label, action in items:
            tk.Button(
                self.menu, text=label, command=action,
                bg=PANEL_2, fg=FG, relief="flat", font=FONT, anchor="w"
            ).pack(fill="x", padx=12, pady=4)

        tk.Button(
            self.menu, text="Cerrar menú", command=self.hide_menu,
            bg=TITLE_BG, fg=YELLOW, relief="flat", font=FONT_BOLD
        ).pack(fill="x", padx=12, pady=(8, 6))

    def hide_menu(self):
        self.menu_open = False
        if self.menu:
            self.menu.destroy()
            self.menu = None

    def refresh(self):
        self.clock.config(text=f"{self.state.clock_tick:02d}:{(self.state.clock_tick * 3) % 60:02d}")
        self.status.config(text=f"Héroes: {len(self.state.get_heroes())} | {self.state.scheduler_mode}")
        self.bar.after(300, self.refresh)