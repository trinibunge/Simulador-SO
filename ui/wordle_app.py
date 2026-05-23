import os
import random
import unicodedata
import tkinter as tk

from ui.window_base import WindowBase
from ui.theme import *


# Colores estilo Wordle, levemente ajustados al tema claro del Hospital MS
TILE_EMPTY_BG   = "#ffffff"
TILE_EMPTY_BD   = "#d3d6da"
TILE_FILLED_BD  = "#878a8c"
TILE_TEXT_DARK  = "#1a1a1b"
TILE_TEXT_LIGHT = "#ffffff"

COLOR_GREEN     = "#6aaa64"
COLOR_YELLOW    = "#c9b458"
COLOR_GRAY      = "#787c7e"

# Para el log: representación visual del resultado de un intento
EMOJI_MAP = {"green": "🟩", "yellow": "🟨", "gray": "⬜"}


def _normaliza(palabra):
    """Pasa a minúscula y elimina tildes. La Ñ queda como N."""
    palabra = palabra.strip().lower()
    palabra = unicodedata.normalize("NFD", palabra)
    palabra = "".join(c for c in palabra if unicodedata.category(c) != "Mn")
    return palabra


def _cargar_lista(ruta_rel):
    """Carga un .txt de palabras una por línea. Devuelve set."""
    candidatas = [
        ruta_rel,
        os.path.join(os.getcwd(), ruta_rel),
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", ruta_rel),
    ]
    for r in candidatas:
        try:
            if os.path.exists(r):
                with open(r, "r", encoding="utf-8") as f:
                    palabras = set()
                    for ln in f:
                        w = _normaliza(ln)
                        if len(w) == 5 and w.isalpha() and w.isascii():
                            palabras.add(w)
                    if palabras:
                        return palabras
        except Exception:
            continue
    return set()


# Fallback minúsculo por si no encuentra los assets (no debería pasar)
_FALLBACK_OBJ = {
    "abajo", "amigo", "casas", "cielo", "fuego", "gente", "joven", "libro",
    "madre", "mundo", "padre", "perro", "queso", "salud", "tarea", "verde",
    "viaje", "amiga", "noche", "calor",
}
_FALLBACK_VAL = set(_FALLBACK_OBJ) | {
    "abeja", "abeto", "abrir", "actor", "acida", "acido", "agudo", "ahora",
    "alegre", "algun", "ancho",
}


class WordleApp(WindowBase):
    """
    Wordle en español. Se registra como proceso del sistema (kind='app')
    igual que Snake o el Asistente, así aparece en la cola del scheduler,
    suma métricas reales y queda registrado en la Bitácora.

    Reglas:
    - 6 intentos, palabras de 5 letras.
    - Verde: letra correcta en posición correcta.
    - Amarillo: letra correcta en posición incorrecta.
    - Gris: letra no está en la palabra.
    - Se ignoran tildes (escribimos "arbol", no "árbol").
    - Si la palabra escrita NO está en el diccionario válido, se rechaza
      sin gastar intento.
    - Al ganar o perder, ESPACIO / R inicia una nueva partida.

    Logueo en Bitácora (state.log con tag 'APP'):
    - apertura/cierre los emite el propio state.admitir/dar_alta
    - cada intento: 'intento N/6: PALABRA -> 🟩🟨⬜⬜⬜'
    - victoria/derrota
    - reinicio
    """

    APP_NAME = "Juego Wordle"
    APP_PRIORITY = 8
    APP_BURST = 999_999_999

    TILE = 56
    GAP = 6
    ROWS = 6
    COLS = 5

    def __init__(self, master, state=None, x=440, y=120):
        # ancho: 5 tiles + 4 gaps + 2*88 padding = 280 + 24 + 176 = 480
        # alto: 6 tiles + 5 gaps + status + nueva-partida + 2*40 = 366 + 80 + 80 = 526
        super().__init__(master, "🟩 Juego Wordle", GREEN, 480, 560, x, y)
        self.state = state

        # Registrarse como proceso del sistema
        self._app_paciente = None
        if state is not None:
            self._app_paciente = state.admitir(
                self.APP_NAME,
                priority=self.APP_PRIORITY,
                burst=self.APP_BURST,
                kind="app",
            )

        # Diccionarios
        base = "assets/wordle"
        self.objetivos = list(_cargar_lista(f"{base}/objetivos"))
        self.validas = _cargar_lista(f"{base}/validas")
        if not self.objetivos:
            self.objetivos = list(_FALLBACK_OBJ)
        if not self.validas:
            self.validas = set(_FALLBACK_VAL)
        # Toda objetivo es válida también, sí o sí
        for w in self.objetivos:
            self.validas.add(w)

        # UI: header con instrucciones cortas
        self.hint = tk.Label(
            self.content,
            text="Adiviná la palabra de 5 letras  ·  ENTER para enviar  ·  ⌫ para borrar",
            bg=PANEL, fg=MUTED, font=FONT_SM,
        )
        self.hint.pack(pady=(8, 4))

        # Canvas con la grilla
        grid_w = self.COLS * self.TILE + (self.COLS - 1) * self.GAP
        grid_h = self.ROWS * self.TILE + (self.ROWS - 1) * self.GAP
        self.canvas = tk.Canvas(
            self.content,
            width=grid_w, height=grid_h,
            bg=PANEL, highlightthickness=0,
        )
        self.canvas.pack(pady=(4, 6))

        # Status label (mensajes de error, victoria, derrota)
        self.status = tk.Label(
            self.content,
            text="", bg=PANEL, fg=FG, font=FONT_BOLD,
        )
        self.status.pack(pady=(0, 4))

        # Botón nueva partida (visible solo al terminar)
        self.btn_new = tk.Button(
            self.content,
            text="Nueva partida (espacio)",
            bg=GREEN, fg="#ffffff", font=FONT_BOLD,
            relief="flat", bd=0, padx=14, pady=6,
            activebackground="#1a6b35", activeforeground="#ffffff",
            cursor="hand2",
            command=self.nueva_partida,
        )
        # No la packeamos todavía

        # Estado de juego
        self.target = None
        self.intentos = []      # lista de tuplas (palabra_str, colores_list)
        self.actual = ""        # palabra siendo tipeada
        self.terminado = False
        self.gano = False
        self._intentos_jugados = 0
        self._flash_after_id = None

        # Bindings de teclado: a nivel frame para que reciba el foco
        for w in (self.frame, self.content, self.canvas):
            w.bind("<Key>", self._on_key)
        self.canvas.bind("<Button-1>", lambda e: self.frame.focus_set())
        self.frame.focus_set()

        self.nueva_partida(_loguea=False)
        self.draw()

    # ─────────────────────────────────────────────────────────────────
    #  Ciclo de juego
    # ─────────────────────────────────────────────────────────────────

    def nueva_partida(self, _loguea=True):
        self.target = random.choice(self.objetivos)
        self.intentos = []
        self.actual = ""
        self.terminado = False
        self.gano = False
        self._intentos_jugados = 0
        self.status.config(text="", fg=FG)
        try:
            self.btn_new.pack_forget()
        except Exception:
            pass
        if _loguea and self.state is not None:
            self.state.log("APP", f"'{self.APP_NAME}' nueva partida iniciada")
        self.draw()
        try:
            self.frame.focus_set()
        except Exception:
            pass

    def on_close(self):
        """Al cerrar la ventana, dar de alta el proceso del sistema."""
        if self.state is not None and self._app_paciente is not None:
            try:
                self.state.dar_alta(self._app_paciente.pid)
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────
    #  Input
    # ─────────────────────────────────────────────────────────────────

    def _on_key(self, event):
        if not self.alive:
            return

        # Si la partida terminó, espacio / R reinician
        if self.terminado:
            if event.keysym in ("space", "Return") or event.char.lower() == "r":
                self.nueva_partida()
            return

        key = event.keysym
        if key == "Return":
            self._enviar()
            return
        if key in ("BackSpace", "Delete"):
            if self.actual:
                self.actual = self.actual[:-1]
                self._limpiar_status()
                self.draw()
            return

        # Letra
        char = event.char.lower() if event.char else ""
        if char and len(char) == 1 and ("a" <= char <= "z" or char == "ñ"):
            # ignoramos ñ (no está en nuestro diccionario)
            if char == "ñ":
                return
            if len(self.actual) < self.COLS:
                self.actual += char
                self._limpiar_status()
                self.draw()

    def _limpiar_status(self):
        if self.status.cget("text"):
            self.status.config(text="")

    def _enviar(self):
        if len(self.actual) < self.COLS:
            self._flash_status("Faltan letras", RED)
            return
        guess = self.actual
        if guess not in self.validas:
            self._flash_status(f"'{guess.upper()}' no está en el diccionario", RED)
            return

        # Procesar intento
        colores = self._colorear(guess, self.target)
        self.intentos.append((guess, colores))
        self.actual = ""
        self._intentos_jugados += 1

        # Loguear el intento en la Bitácora
        if self.state is not None:
            emoji = "".join(EMOJI_MAP[c] for c in colores)
            self.state.log(
                "APP",
                f"'{self.APP_NAME}' intento {self._intentos_jugados}/{self.ROWS}: "
                f"{guess.upper()} → {emoji}",
            )

        # ¿Ganó?
        if all(c == "green" for c in colores):
            self.terminado = True
            self.gano = True
            self.status.config(
                text=f"¡Acertaste en {self._intentos_jugados}/{self.ROWS}!",
                fg=COLOR_GREEN,
            )
            self.btn_new.pack(pady=(2, 8))
            if self.state is not None:
                self.state.log(
                    "APP",
                    f"'{self.APP_NAME}' victoria :)) en {self._intentos_jugados}/{self.ROWS} "
                    f"· palabra: {self.target.upper()}",
                )
        elif self._intentos_jugados >= self.ROWS:
            # Perdió
            self.terminado = True
            self.gano = False
            self.status.config(
                text=f"Sin más intentos. La palabra era: {self.target.upper()}",
                fg=RED,
            )
            self.btn_new.pack(pady=(2, 8))
            if self.state is not None:
                self.state.log(
                    "APP",
                    f"'{self.APP_NAME}' Derrota :(( la palabra era: {self.target.upper()}",
                )

        self.draw()

    def _flash_status(self, text, color):
        """Muestra un mensaje breve abajo de la grilla."""
        self.status.config(text=text, fg=color)
        if self._flash_after_id is not None:
            try:
                self.frame.after_cancel(self._flash_after_id)
            except Exception:
                pass
        self._flash_after_id = self.frame.after(1800, self._limpiar_status)

    # ─────────────────────────────────────────────────────────────────
    #  Algoritmo de coloreo Wordle (maneja letras repetidas)
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _colorear(guess, target):
        """
        Devuelve lista de 5 colores ('green'|'yellow'|'gray') para guess.
        Maneja correctamente letras repetidas: si target='LLAMA' y guess='ALILA',
        el conteo evita marcar dos veces una misma letra.
        """
        n = len(guess)
        result = ["gray"] * n
        counts = {}
        for c in target:
            counts[c] = counts.get(c, 0) + 1
        # 1ra pasada: verdes
        for i in range(n):
            if guess[i] == target[i]:
                result[i] = "green"
                counts[guess[i]] -= 1
        # 2da pasada: amarillos
        for i in range(n):
            if result[i] == "gray":
                if counts.get(guess[i], 0) > 0:
                    result[i] = "yellow"
                    counts[guess[i]] -= 1
        return result

    # ─────────────────────────────────────────────────────────────────
    #  Render
    # ─────────────────────────────────────────────────────────────────

    def draw(self):
        c = self.canvas
        c.delete("all")
        for row in range(self.ROWS):
            for col in range(self.COLS):
                x0 = col * (self.TILE + self.GAP)
                y0 = row * (self.TILE + self.GAP)
                x1 = x0 + self.TILE
                y1 = y0 + self.TILE

                letra = ""
                fill = TILE_EMPTY_BG
                outline = TILE_EMPTY_BD
                fg = TILE_TEXT_DARK

                if row < len(self.intentos):
                    palabra, colores = self.intentos[row]
                    letra = palabra[col].upper()
                    color = colores[col]
                    if color == "green":
                        fill = COLOR_GREEN
                        outline = COLOR_GREEN
                        fg = TILE_TEXT_LIGHT
                    elif color == "yellow":
                        fill = COLOR_YELLOW
                        outline = COLOR_YELLOW
                        fg = TILE_TEXT_LIGHT
                    else:  # gray
                        fill = COLOR_GRAY
                        outline = COLOR_GRAY
                        fg = TILE_TEXT_LIGHT
                elif row == len(self.intentos) and not self.terminado:
                    # Fila actual
                    if col < len(self.actual):
                        letra = self.actual[col].upper()
                        outline = TILE_FILLED_BD

                c.create_rectangle(x0, y0, x1, y1,
                                   fill=fill, outline=outline, width=2)
                if letra:
                    c.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                                  text=letra, fill=fg,
                                  font=("Segoe UI", 24, "bold"))