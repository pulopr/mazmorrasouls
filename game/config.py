"""Constantes de configuración: ventana, tiempo, controles y rutas.

Todos los números de balance y ajuste del juego viven aquí (o en `data/`),
nunca sueltos por el código.
"""

from pathlib import Path

import pygame

# --- Rutas del proyecto ---------------------------------------------------

# Raíz del repositorio (este archivo está en <raíz>/game/config.py).
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LEVELS_DIR = DATA_DIR / "levels"

# Nivel que se carga al arrancar mientras no haya menú ni progresión.
# `test.txt` es la sala pequeña que usan los tests; `test_big.txt` es más
# grande que la ventana, para poder probar la cámara.
DEFAULT_LEVEL = LEVELS_DIR / "test_big.txt"

# --- Ventana y tiempo ----------------------------------------------------

CAPTION = "Mazmorra Souls"
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540

# Paso de tiempo fijo: el bucle se limita a 60 FPS y todo movimiento o
# temporizador se multiplicará por `dt` (segundos transcurridos).
FPS = 60

# Lado en píxeles de un tile del mapa. El tamaño de la fuente ASCII se
# calcula a partir de él, de modo que cambiar esto reescala el dibujado.
TILE_SIZE = 32

# --- Jugador -------------------------------------------------------------

# Caja de colisión del jugador, algo menor que un tile para que pase por
# los pasillos sin rozar las esquinas.
PLAYER_WIDTH = 24
PLAYER_HEIGHT = 24

# Velocidad de caminar, en píxeles por segundo (unos 5,6 tiles/s).
PLAYER_SPEED = 180.0

# --- Estamina ------------------------------------------------------------

STAMINA_MAX = 100.0

# Recuperación, en puntos por segundo, y el respiro que hay que esperar
# desde la última acción que gastó estamina antes de que vuelva a subir.
STAMINA_REGEN_RATE = 35.0
STAMINA_REGEN_DELAY = 0.6

# --- Rodar ---------------------------------------------------------------

ROLL_STAMINA_COST = 25.0

# Distancia y duración fijas; la velocidad sale de dividirlas, así se
# ajusta el movimiento pensando en casillas y no en px/s. Cuatro casillas
# en poco más de un cuarto de segundo: un acelerón claro frente a andar.
ROLL_DISTANCE = 128.0          # 4 casillas
ROLL_DURATION = 0.26

# El rodar no va a velocidad constante: sale disparado y frena al final
# (curva ease-out). El exponente manda en lo brusco de la frenada: 1 sería
# velocidad constante, y cuanto más alto, más seco el arranque.
ROLL_EASE_EXPONENT = 2.0

# Derivadas, solo informativas: la media es distancia/duración, y con la
# curva ease-out el primer instante va `exponente` veces más rápido que ella.
ROLL_AVERAGE_SPEED = ROLL_DISTANCE / ROLL_DURATION
ROLL_PEAK_SPEED = ROLL_AVERAGE_SPEED * ROLL_EASE_EXPONENT

# Ventana de invulnerabilidad, como fracción del rodar: así se mantiene
# proporcional aunque se cambie la duración. Ni al principio del todo ni
# hasta el final.
ROLL_IFRAME_START_FRACTION = 0.125
ROLL_IFRAME_END_FRACTION = 0.75
ROLL_IFRAME_START = ROLL_DURATION * ROLL_IFRAME_START_FRACTION
ROLL_IFRAME_END = ROLL_DURATION * ROLL_IFRAME_END_FRACTION

# --- Correr --------------------------------------------------------------

# Vez y media la velocidad de andar.
RUN_SPEED = PLAYER_SPEED * 1.5

# Gasto de estamina por segundo mientras se corre.
RUN_STAMINA_DRAIN = 20.0

# --- HUD -----------------------------------------------------------------

HUD_MARGIN = 16
HUD_BAR_WIDTH = 220
HUD_BAR_HEIGHT = 14

# --- Controles -----------------------------------------------------------
# Tabla única de teclas. De momento se usan WASD, Espacio, Shift y Esc; el
# resto queda declarado para las fases siguientes.

KEY_MOVE_UP = pygame.K_w
KEY_MOVE_LEFT = pygame.K_a
KEY_MOVE_DOWN = pygame.K_s
KEY_MOVE_RIGHT = pygame.K_d
KEY_ATTACK_LIGHT = pygame.K_j
KEY_ROLL = pygame.K_SPACE
KEY_RUN = (pygame.K_LSHIFT, pygame.K_RSHIFT)
KEY_ESTUS = pygame.K_q
KEY_INTERACT = pygame.K_e
KEY_PAUSE = pygame.K_ESCAPE
