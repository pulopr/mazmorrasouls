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
# `nivel_01.txt` es el primer nivel de verdad. `test.txt` (sala pequeña) y
# `test_big.txt` (cuatro salas) se mantienen para los tests.
DEFAULT_LEVEL = LEVELS_DIR / "nivel_01.txt"

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

PLAYER_HEALTH = 100.0

# Qué pasa al encajar un golpe: empujón, un momento sin poder actuar y
# una invulnerabilidad corta para que no te encadenen golpes.
PLAYER_HURT_KNOCKBACK = 26.0
PLAYER_HURT_STUN = 0.22
PLAYER_HURT_INVULNERABILITY = 0.75

# Cada cuánto alterna el parpadeo del @ mientras es invulnerable.
PLAYER_BLINK_INTERVAL = 0.07

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

# --- Ataque ligero -------------------------------------------------------

ATTACK_DAMAGE = 34.0           # tres golpes matan a un esqueleto
ATTACK_STAMINA_COST = 20.0

# Las tres fases del golpe, en segundos. La hitbox solo existe durante
# ATTACK_ACTIVE; en la recuperación ya se puede cancelar rodando.
ATTACK_WINDUP = 0.09
ATTACK_ACTIVE = 0.10
ATTACK_RECOVERY = 0.21
ATTACK_DURATION = ATTACK_WINDUP + ATTACK_ACTIVE + ATTACK_RECOVERY

# Hitbox: un rectángulo delante del jugador. ATTACK_REACH es lo que se
# aleja del cuerpo y ATTACK_WIDTH lo que abarca de lado.
ATTACK_REACH = 34.0
ATTACK_WIDTH = 42.0
ATTACK_OFFSET = 2.0            # hueco entre el cuerpo y la hitbox

# Atacando uno queda casi clavado en el sitio.
ATTACK_MOVE_FACTOR = 0.15

# Empujón que recibe el enemigo golpeado, en píxeles.
ATTACK_KNOCKBACK = 18.0

# --- Enemigos (común) ----------------------------------------------------

ENEMY_WIDTH = 24
ENEMY_HEIGHT = 24

# Parpadeo en blanco al recibir un golpe, en segundos.
ENEMY_HIT_FLASH = 0.12

# Cuánto aguanta sin ver al jugador antes de darlo por perdido y volverse
# a su sitio.
ENEMY_SIGHT_GRACE = 1.2

# El muestreo del rayo de visión: una fracción de tile. Más fino es más
# preciso y más lento.
SIGHT_RAY_STEP = 0.25

# --- Esqueleto (enemigo básico) ------------------------------------------
# Poca vida, ataque rápido con aviso corto pero visible, y daño moderado.

SKELETON_HEALTH = 70.0              # muere en 3 golpes ligeros (34 de daño)
SKELETON_SPEED = 95.0               # algo más lento que andar (180)
SKELETON_DAMAGE = 15.0              # 15% de la vida del jugador
SKELETON_DETECT_RADIUS = 220.0      # ~7 casillas
SKELETON_LEASH_RADIUS = 420.0       # si te alejas más, se vuelve a su sitio
SKELETON_ATTACK_RANGE = 36.0        # a qué distancia se planta a golpear
SKELETON_WINDUP = 0.40              # aviso: da tiempo a rodar
SKELETON_ACTIVE = 0.12
SKELETON_RECOVERY = 0.35            # queda vendido un momento
SKELETON_ATTACK_REACH = 32.0
SKELETON_ATTACK_WIDTH = 38.0
SKELETON_STUN = 0.30                # cuánto se queda aturdido al ser golpeado
SKELETON_CAN_BE_STUNNED = True      # habrá enemigos que no se interrumpan

# --- Élite (D): enemigo difícil ------------------------------------------
# Mismo comportamiento que el esqueleto, pero mucho más duro y peligroso.
# Dará más almas al morir cuando existan las almas (Fase 4).

ELITE_HEALTH = 260.0                # unos 8 golpes ligeros
ELITE_SPEED = 110.0
ELITE_DAMAGE = 34.0                 # un tercio de la vida del jugador
ELITE_DETECT_RADIUS = 280.0
ELITE_LEASH_RADIUS = 520.0
ELITE_ATTACK_RANGE = 44.0
ELITE_WINDUP = 0.55                 # avisa más, pero pega mucho más fuerte
ELITE_ACTIVE = 0.16
ELITE_RECOVERY = 0.40
ELITE_ATTACK_REACH = 42.0
ELITE_ATTACK_WIDTH = 48.0
ELITE_STUN = 0.14                   # cuesta mucho más interrumpirlo
ELITE_CAN_BE_STUNNED = True
ELITE_SOULS = 300                   # Fase 4

# --- Arquero (A) ---------------------------------------------------------
# Muy poca vida; su peligro es la distancia. El disparo llega en la Parte 3.

ARCHER_HEALTH = 45.0                # muere en 2 golpes ligeros
ARCHER_SPEED = 100.0
ARCHER_DAMAGE = 10.0                # su golpe cuerpo a cuerpo, flojo
ARCHER_DETECT_RADIUS = 340.0        # ve más lejos que el esqueleto
ARCHER_LEASH_RADIUS = 560.0
ARCHER_ATTACK_RANGE = 34.0
ARCHER_WINDUP = 0.30
ARCHER_ACTIVE = 0.10
ARCHER_RECOVERY = 0.25
ARCHER_ATTACK_REACH = 28.0
ARCHER_ATTACK_WIDTH = 32.0
ARCHER_STUN = 0.35                  # se descompone con nada
ARCHER_CAN_BE_STUNNED = True

# --- Muerte del jugador --------------------------------------------------
# Provisional hasta la Fase 4: cartel y reinicio del nivel.

DEATH_MESSAGE = "HAS MUERTO"
DEATH_SCREEN_DURATION = 2.5

# --- HUD -----------------------------------------------------------------

HUD_MARGIN = 16
HUD_BAR_WIDTH = 220
HUD_BAR_HEIGHT = 14
HUD_BAR_SPACING = 6

# Barra pequeña sobre los enemigos heridos.
ENEMY_BAR_WIDTH = 28
ENEMY_BAR_HEIGHT = 4
ENEMY_BAR_OFFSET = 22          # cuánto se levanta sobre el centro del enemigo

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

# Dibuja hitboxes y cajas de colisión.
KEY_DEBUG = pygame.K_F1
