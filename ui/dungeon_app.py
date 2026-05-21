import tkinter as tk
from ui.window_base import WindowBase
from ui.theme import *
from core.dungeon_game import DungeonGame
from ui.toast import Toast


class DungeonApp(WindowBase):
    def __init__(self, master, state, x=200, y=80):
        super().__init__(master, "Dungeon View", PURPLE, 980, 640, x, y)
        self.state = state
        self.game = DungeonGame(state)

        self.main = tk.Frame(self.content, bg=PANEL)
        self.main.pack(fill="both", expand=True)

        self.top = tk.Frame(self.main, bg=PANEL)
        self.top.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(
            self.top,
            text="DungeonOS — Runner educativo",
            bg=PANEL,
            fg=FG,
            font=FONT_BOLD
        ).pack(anchor="w")

        tk.Label(
            self.top,
            text="SPACE = saltar | ENTER = DungScript / interactuar",
            bg=PANEL,
            fg=MUTED,
            font=FONT_SM
        ).pack(anchor="w", pady=(2, 0))

        self.body = tk.Frame(self.main, bg=PANEL)
        self.body.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.canvas = tk.Canvas(
            self.body,
            bg="#f8fafc",
            highlightthickness=1,
            highlightbackground=BORDER,
            width=680,
            height=520
        )
        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = tk.Frame(self.body, bg=PANEL, width=240)
        right.pack(side="right", fill="y")

        self.info = tk.Text(
            right,
            bg=PANEL_2,
            fg=FG,
            font=FONT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            width=30,
            height=30
        )
        self.info.pack(fill="both", expand=True)

        self.bind_controls()
        self.refresh_view()

    def bind_controls(self):
        controls = [
            ("<space>", lambda e: self.game.jump()),
            ("<Return>", lambda e: self.run_command()),
            ("w", lambda e: self.game.jump()),
        ]
        for widget in (self.frame, self.canvas):
            for key, handler in controls:
                widget.bind(key, handler)

        self.canvas.focus_set()

    def run_command(self):
        msg = self.game.interact()
        self.game.messages.append(msg)
        Toast(self.master, msg, TEAL)

    def draw_ground(self):
        w = int(self.canvas.winfo_width() or 680)
        h = int(self.canvas.winfo_height() or 520)
        self.canvas.create_rectangle(0, h - 90, w, h, fill="#d9e7f5", outline="")
        self.canvas.create_line(0, h - 90, w, h - 90, fill="#9eb3c7", width=3)

    def draw_player(self):
        x = 80
        y = int(self.game.player["y"] * 45)

        self.canvas.create_text(x, y, text=self.game.active_process, font=("Apple Color Emoji", 28))
        self.canvas.create_text(x + 30, y - 28, text="🧠", font=("Apple Color Emoji", 14))

    def draw_objects(self):
        base_x = 100
        for obs in self.game.obstacles:
            x = base_x + int(obs.x * 45)
            y = int(obs.y * 45)
            symbol = {
                "segfault": "💀",
                "mutex": "🔒",
                "deadlock": "👹",
                "lowprio": "📉",
            }.get(obs.kind, "❓")
            self.canvas.create_text(x, y, text=symbol, font=("Apple Color Emoji", 24))

        for item in self.game.collectibles:
            x = base_x + int(item["x"] * 45)
            y = int(item["y"] * 45)
            self.canvas.create_text(x, y, text=item["icon"], font=("Apple Color Emoji", 22))

    def refresh_view(self):
        if not self.frame.winfo_exists():
            return

        self.game.update()

        self.canvas.delete("all")
        self.info.delete("1.0", tk.END)

        self.draw_ground()
        self.draw_objects()
        self.draw_player()

        title = "RUNNING" if not self.game.game_over and not self.game.win else ("GAME OVER" if self.game.game_over else "WIN")
        self.canvas.create_text(20, 20, anchor="nw", text=f"DungeonOS — {title}", fill="#111827", font=FONT_BOLD)

        if self.game.game_over:
            self.canvas.create_text(340, 170, text="💀 PROCESS TERMINATED", fill="#dc2626", font=("Aptos", 24, "bold"))
        elif self.game.win:
            self.canvas.create_text(340, 170, text="🏁 YOU WIN", fill="#16a34a", font=("Aptos", 24, "bold"))

        self.info.insert(tk.END, "ESTADO\n──────\n")
        self.info.insert(tk.END, self.game.status() + "\n\n")

        self.info.insert(tk.END, "PROCESOS\n────────\n")
        for p in self.game.process_rows():
            self.info.insert(tk.END, f"{p['pid']} {p['icon']} {p['name']}  {p['prio']}  {p['state']}\n")

        self.info.insert(tk.END, "\nLOG\n───\n")
        for msg in self.game.messages[-14:]:
            self.info.insert(tk.END, msg + "\n")

        self.frame.after(60, self.refresh_view)