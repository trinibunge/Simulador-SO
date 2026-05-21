import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *


class DungeonApp(WindowBase):
    def __init__(self, master, state, x=90, y=70):
        super().__init__(master, "🏛️ Dungeon View", PURPLE, 560, 400, x, y)
        self.state = state
        self.canvas = tk.Canvas(self.content, bg="#0a1018", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh()

    def refresh(self):
        if not self.frame.winfo_exists():
            return

        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        self.canvas.create_rectangle(12, 12, w-12, 70, fill="#162033", outline=BORDER, width=2)
        self.canvas.create_text(28, 30, anchor="w", fill=PURPLE, font=FONT_BIG, text="LA CATACUMBA")
        self.canvas.create_text(28, 52, anchor="w", fill=MUTED, font=FONT_SM,
                                text=f"Scheduler: {self.state.scheduler_mode}   Chaos: {self.state.chaos_mode}   Tick: {self.state.clock_tick}")

        self.canvas.create_rectangle(12, 88, w-12, h-42, fill="#0d131d", outline=BORDER_SOFT, width=2)
        self.canvas.create_text(28, 108, anchor="w", fill=CYAN, font=FONT_BOLD, text="HÉROES ACTIVOS")

        y = 140
        for hero in self.state.get_heroes()[:8]:
            color = GREEN if hero.state == "READY" else YELLOW
            self.canvas.create_text(28, y, anchor="w", fill=FG, font=FONT_MD,
                                    text=f"{hero.symbol}  {hero.name:<14} PID {hero.pid:<3} PRI {hero.priority:<2}")
            self.canvas.create_text(w-70, y, anchor="e", fill=color, font=FONT_BOLD, text=hero.state)
            y += 31

        if not self.state.get_heroes():
            self.canvas.create_text(w//2, h//2, fill=MUTED, font=FONT_MD,
                                    text="No hay héroes aún. Usá la Terminal para crear algunos.")

        self.frame.after(450, self.refresh)