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
DEFAULT_LEVEL = LEVELS_DIR / "test.txt"

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

# --- Controles -----------------------------------------------------------
# Tabla única de teclas. De momento el bucle solo usa KEY_PAUSE (salir),
# el resto queda declarado para las fases siguientes.

KEY_MOVE_UP = pygame.K_w
KEY_MOVE_LEFT = pygame.K_a
KEY_MOVE_DOWN = pygame.K_s
KEY_MOVE_RIGHT = pygame.K_d
KEY_ATTACK_LIGHT = pygame.K_j
KEY_ROLL = pygame.K_SPACE
KEY_ESTUS = pygame.K_q
KEY_INTERACT = pygame.K_e
KEY_PAUSE = pygame.K_ESCAPE
