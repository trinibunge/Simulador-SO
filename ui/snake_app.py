import tkinter as tk
import random
from ui.window_base import WindowBase
from ui.theme import *


class SnakeApp(WindowBase):
    def __init__(self, master, state=None, x=460, y=160):
        super().__init__(master, "🥚 Snake.exe", GREEN, 430, 480, x, y)
        self.state = state

        self.canvas = tk.Canvas(self.content, width=400, height=400, bg="#05070a", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

        self.snake = [(10, 10), (9, 10), (8, 10)]
        self.food = (15, 15)
        self.dir = (1, 0)

        self.frame.focus_set()
        self.frame.bind("<Up>", lambda e: self.set_dir(0, -1))
        self.frame.bind("<Down>", lambda e: self.set_dir(0, 1))
        self.frame.bind("<Left>", lambda e: self.set_dir(-1, 0))
        self.frame.bind("<Right>", lambda e: self.set_dir(1, 0))
        self.loop()

    def set_dir(self, x, y):
        self.dir = (x, y)

    def loop(self):
        if not self.frame.winfo_exists():
            return

        head = self.snake[0]
        new_head = (head[0] + self.dir[0], head[1] + self.dir[1])

        if new_head[0] < 0:
            new_head = (19, new_head[1])
        if new_head[0] > 19:
            new_head = (0, new_head[1])
        if new_head[1] < 0:
            new_head = (new_head[0], 19)
        if new_head[1] > 19:
            new_head = (new_head[0], 0)

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.food = (random.randint(0, 19), random.randint(0, 19))
        else:
            self.snake.pop()

        self.draw()
        self.frame.after(120, self.loop)

    def draw(self):
        self.canvas.delete("all")
        for i in range(0, 400, 20):
            self.canvas.create_line(i, 0, i, 400, fill="#122030")
            self.canvas.create_line(0, i, 400, i, fill="#122030")

        fx, fy = self.food
        self.canvas.create_rectangle(fx*20+2, fy*20+2, fx*20+18, fy*20+18, fill=RED, outline="")

        for i, (x, y) in enumerate(self.snake):
            color = GREEN if i == 0 else "#2aa56c"
            self.canvas.create_rectangle(x*20+2, y*20+2, x*20+18, y*20+18, fill=color, outline="")