import tkinter as tk
import random
from ui.window_base import WindowBase
from ui.theme import *


class SnakeApp(WindowBase):
    """
    Snake clásico.

    Cambios respecto a la versión vieja:
    - Se llama "🐍 Juego Snake" (no más Snake.exe()).
    - Se REGISTRA como proceso al abrir: aparece en la sala de espera
      del Hospital y compite por la CPU como cualquier otro proceso.
      Esto materializa la idea de que las aplicaciones del usuario
      también son procesos del sistema operativo.
    - Loguea en la Bitácora: registro como proceso, reinicios, game over.

    Reglas:
    - Si toca un borde: reinicia automáticamente al tamaño original.
    - Si choca consigo misma: GAME OVER, SPACE/R para reiniciar.
    """

    GRID = 20
    CELL = 20

    # Identidad como proceso
    APP_NAME = "Juego Snake"
    APP_PRIORITY = 8           # baja prioridad: no es vida o muerte
    APP_BURST = 999_999_999    # nunca termina por burst

    def __init__(self, master, state=None, x=460, y=160):
        super().__init__(master, "🐍 Juego Snake", GREEN, 460, 540, x, y)
        self.state = state

        # Registrarse como proceso del sistema (kind="app")
        self._app_paciente = None
        if state is not None:
            self._app_paciente = state.admitir(
                self.APP_NAME,
                priority=self.APP_PRIORITY,
                burst=self.APP_BURST,
                kind="app",
            )

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
            w.bind("<space>", lambda e: self.reset_if_dead(manual=True))
            w.bind("r",       lambda e: self.reset_if_dead(manual=True))
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())
        self.canvas.focus_set()

        self._first_reset = True
        self.reset()
        self.schedule_loop()

    def on_close(self):
        """Al cerrar la ventana, dar de alta el proceso."""
        if self.state is not None and self._app_paciente is not None:
            try:
                self.state.dar_alta(self._app_paciente.pid)
            except Exception:
                pass

    def reset(self):
        was_running = not self._first_reset
        self.snake = [(10, 10), (9, 10), (8, 10)]
        self.dir = (1, 0)
        self.pending_dir = self.dir
        self.food = self._random_food()
        self.dead = False
        self.score = 0

        if was_running and self.state is not None:
            self.state.log("APP", f"'{self.APP_NAME}' reiniciado por el usuario")
        self._first_reset = False

    def reset_if_dead(self, manual=False):
        if self.dead:
            self.reset()

    def _random_food(self):
        while True:
            f = (random.randint(0, self.GRID - 1), random.randint(0, self.GRID - 1))
            if f not in self.snake:
                return f

    def set_dir(self, x, y):
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

            # tocar borde => reset automático
            if nx < 0 or nx >= self.GRID or ny < 0 or ny >= self.GRID:
                self.reset()
                self.draw()
                self.schedule_loop()
                return

            new_head = (nx, ny)

            # chocar consigo misma => GAME OVER
            if new_head in self.snake:
                self.dead = True
                if self.state is not None:
                    self.state.log("APP",
                        f"'{self.APP_NAME}' GAME OVER · score final: {self.score}")
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
        for i in range(0, self.GRID * self.CELL, self.CELL):
            c.create_line(i, 0, i, self.GRID * self.CELL, fill="#122030")
            c.create_line(0, i, self.GRID * self.CELL, i, fill="#122030")
        fx, fy = self.food
        c.create_rectangle(fx * self.CELL + 2, fy * self.CELL + 2,
                           fx * self.CELL + self.CELL - 2, fy * self.CELL + self.CELL - 2,
                           fill=RED, outline="")
        for i, (x, y) in enumerate(self.snake):
            color = GREEN if i == 0 else "#2aa56c"
            c.create_rectangle(x * self.CELL + 2, y * self.CELL + 2,
                               x * self.CELL + self.CELL - 2, y * self.CELL + self.CELL - 2,
                               fill=color, outline="")
        if self.dead:
            c.create_rectangle(0, 0, self.GRID * self.CELL, self.GRID * self.CELL,
                               fill="#000000", stipple="gray50", outline="")
            c.create_text(self.GRID * self.CELL // 2, self.GRID * self.CELL // 2 - 14,
                          text="GAME OVER", fill="#fca5a5", font=("Aptos", 22, "bold"))
            c.create_text(self.GRID * self.CELL // 2, self.GRID * self.CELL // 2 + 18,
                          text="SPACE / R para reiniciar", fill="#fde68a",
                          font=("Aptos", 11))

        self.info.config(text=f"Score: {self.score}   {'MUERTO' if self.dead else 'VIVO'}")