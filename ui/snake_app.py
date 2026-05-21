import tkinter as tk
import random
from ui.window_base import WindowBase
from ui.theme import *


class SnakeApp(WindowBase):
    """
    Snake clásico.
    - Si toca un borde: reinicia automáticamente al tamaño original.
    - Si choca consigo misma: GAME OVER, SPACE/R para reiniciar.
    """

    GRID = 20
    CELL = 20

    def __init__(self, master, state=None, x=460, y=160):
        super().__init__(master, "🥚 Snake.exe", GREEN, 460, 540, x, y)
        self.state = state

        self.canvas = tk.Canvas(
            self.content, width=self.GRID * self.CELL, height=self.GRID * self.CELL,
            bg="#05070a", highlightthickness=0
        )
        self.canvas.pack(padx=10, pady=10)

        self.info = tk.Label(self.content, text="", bg=PANEL, fg=FG, font=FONT)
        self.info.pack()

        for w in (self.frame, self.canvas):
            w.bind("<Up>",    lambda e: self.set_dir(0, -1))
            w.bind("<Down>",  lambda e: self.set_dir(0, 1))
            w.bind("<Left>",  lambda e: self.set_dir(-1, 0))
            w.bind("<Right>", lambda e: self.set_dir(1, 0))
            w.bind("<space>", lambda e: self.reset_if_dead())
            w.bind("r",       lambda e: self.reset_if_dead())
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        self.canvas.focus_set()

        self.reset()
        self.schedule_loop()

    def reset(self):
        """Vuelve al estado inicial: 3 segmentos, dirección derecha."""
        self.snake = [(10, 10), (9, 10), (8, 10)]
        self.dir = (1, 0)
        self.pending_dir = self.dir
        self.food = self._random_food()
        self.dead = False
        self.score = 0

    def reset_if_dead(self):
        if self.dead:
            self.reset()

    def _random_food(self):
        while True:
            f = (random.randint(0, self.GRID - 1), random.randint(0, self.GRID - 1))
            if f not in self.snake:
                return f

    def set_dir(self, x, y):
        # comparar contra pending_dir para que UP→LEFT funcione en el mismo frame
        if (x, y) == (-self.pending_dir[0], -self.pending_dir[1]):
            return
        self.pending_dir = (x, y)

    def schedule_loop(self):
        if not self.alive:
            return
        self.frame.after(120, self.loop)

    def loop(self):
        if not self.alive or not self.frame.winfo_exists():
            return

        if not self.dead:
            self.dir = self.pending_dir
            head = self.snake[0]
            nx = head[0] + self.dir[0]
            ny = head[1] + self.dir[1]

            # tocar borde => reset automático al tamaño original
            if nx < 0 or nx >= self.GRID or ny < 0 or ny >= self.GRID:
                self.reset()
                self.draw()
                self.schedule_loop()
                return

            new_head = (nx, ny)

            # chocar consigo misma => GAME OVER
            if new_head in self.snake:
                self.dead = True
            else:
                self.snake.insert(0, new_head)
                if new_head == self.food:
                    self.score += 1
                    self.food = self._random_food()
                else:
                    self.snake.pop()

        self.draw()
        self.schedule_loop()

    def draw(self):
        c = self.canvas
        c.delete("all")
        # grilla
        for i in range(0, self.GRID * self.CELL, self.CELL):
            c.create_line(i, 0, i, self.GRID * self.CELL, fill="#122030")
            c.create_line(0, i, self.GRID * self.CELL, i, fill="#122030")
        # comida
        fx, fy = self.food
        c.create_rectangle(fx * self.CELL + 2, fy * self.CELL + 2,
                           fx * self.CELL + self.CELL - 2, fy * self.CELL + self.CELL - 2,
                           fill=RED, outline="")
        # serpiente
        for i, (x, y) in enumerate(self.snake):
            color = GREEN if i == 0 else "#2aa56c"
            c.create_rectangle(x * self.CELL + 2, y * self.CELL + 2,
                               x * self.CELL + self.CELL - 2, y * self.CELL + self.CELL - 2,
                               fill=color, outline="")
        # overlay de muerte (solo cuando choca consigo misma)
        if self.dead:
            c.create_rectangle(0, 0, self.GRID * self.CELL, self.GRID * self.CELL,
                               fill="#000000", stipple="gray50", outline="")
            c.create_text(self.GRID * self.CELL // 2, self.GRID * self.CELL // 2 - 14,
                          text="GAME OVER", fill="#fca5a5", font=("Aptos", 22, "bold"))
            c.create_text(self.GRID * self.CELL // 2, self.GRID * self.CELL // 2 + 18,
                          text="SPACE / R para reiniciar", fill="#fde68a",
                          font=("Aptos", 11))

        self.info.config(text=f"Score: {self.score}   {'MUERTO' if self.dead else 'VIVO'}")