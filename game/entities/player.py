"""El jugador: se mueve, corre y rueda, gastando estamina.

Los estados están explícitos en `PlayerState` porque la Fase 3 añadirá
atacar y recibir daño: cada estado decide qué se puede hacer y qué no.
"""

import math
from dataclasses import dataclass
from enum import Enum, auto

from game import config
from game.entities.entity import Entity
from game.systems.stats import Stamina


def normalize(dx, dy):
    """Devuelve el vector (dx, dy) con longitud 1, o (0, 0) si es nulo.

    Sin esto, moverse en diagonal sería más rápido que en línea recta
    (sqrt(2) veces más).
    """
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0
    return dx / length, dy / length


def roll_progress(elapsed):
    """Fracción de la distancia ya recorrida tras `elapsed` segundos de rodar.

    Curva *ease-out*: el jugador sale disparado y frena al final, en vez de
    ir a velocidad constante. Se trabaja con la distancia recorrida y no
    con la velocidad porque así el total es exactamente ROLL_DISTANCE,
    caiga donde caiga el reparto de fotogramas.
    """
    if config.ROLL_DURATION <= 0:
        return 1.0
    fraction = min(1.0, max(0.0, elapsed / config.ROLL_DURATION))
    return 1.0 - (1.0 - fraction) ** config.ROLL_EASE_EXPONENT


@dataclass(frozen=True)
class Intent:
    """Lo que el jugador quiere hacer este fotograma.

    Separa "leer el teclado" de "decidir qué pasa": el bucle traduce las
    teclas a un Intent y el jugador solo interpreta intenciones, así se
    puede probar sin pygame.
    """

    direction: tuple = (0, 0)
    roll: bool = False
    run: bool = False


class PlayerState(Enum):
    """Qué está haciendo el jugador ahora mismo."""

    NORMAL = auto()    # quieto o caminando
    RUNNING = auto()   # corriendo, gastando estamina
    ROLLING = auto()   # rodando: no acepta órdenes hasta terminar


class Player(Entity):
    """Personaje controlado por el jugador."""

    def __init__(self, x, y):
        super().__init__(x, y, config.PLAYER_WIDTH, config.PLAYER_HEIGHT, "player")
        self.speed = config.PLAYER_SPEED
        self.stamina = Stamina(
            config.STAMINA_MAX, config.STAMINA_REGEN_RATE, config.STAMINA_REGEN_DELAY
        )
        self.state = PlayerState.NORMAL
        # Última dirección en la que se movió; se rueda hacia aquí cuando
        # no se pulsa ninguna tecla de movimiento. Empieza mirando al sur.
        self.facing = (0.0, 1.0)
        self._roll_direction = (0.0, 0.0)
        self._roll_elapsed = 0.0

    @classmethod
    def at_level_start(cls, level):
        """Crea al jugador centrado en el tile '@' del mapa."""
        tile_x, tile_y = level.player_start
        return cls(*level.tile_center(tile_x, tile_y))

    # --- Consultas de estado ----------------------------------------------

    @property
    def is_rolling(self):
        return self.state is PlayerState.ROLLING

    @property
    def is_running(self):
        return self.state is PlayerState.RUNNING

    @property
    def is_invulnerable(self):
        """¿Está en los i-frames del rodar?

        Todavía no hay nada que haga daño; esto queda listo para la Fase 3.
        """
        return (
            self.is_rolling
            and config.ROLL_IFRAME_START <= self._roll_elapsed < config.ROLL_IFRAME_END
        )

    @property
    def can_roll(self):
        """Se puede rodar con la barra casi vacía, pero no estando a 0."""
        return not self.is_rolling and self.stamina.has_any

    # --- Fotograma --------------------------------------------------------

    def update(self, dt, intent, level):
        """Avanza un fotograma según lo que el jugador quiera hacer."""
        # La estamina se actualiza primero: así un gasto de este fotograma
        # reinicia el respiro y no se recupera nada hasta pasado el retraso.
        self.stamina.update(dt)

        if self.is_rolling:
            # Rodando no se acepta nada: ni cambiar de rumbo ni rodar otra vez.
            self._advance_roll(dt, level)
        elif intent.roll and self.can_roll:
            self._start_roll(intent.direction)
            self._advance_roll(dt, level)
        else:
            self._move_on_foot(dt, intent, level)

        self._refresh_sprite()

    # --- Rodar ------------------------------------------------------------

    def _start_roll(self, direction):
        """Fija el rumbo del rodar y cobra la estamina."""
        dx, dy = normalize(*direction)
        if (dx, dy) == (0.0, 0.0):
            # Sin teclas pulsadas, se rueda hacia donde se mira.
            dx, dy = self.facing
        self._roll_direction = (dx, dy)
        self.facing = (dx, dy)
        self._roll_elapsed = 0.0
        self.state = PlayerState.ROLLING
        # Puede dejar la barra a 0, pero nunca en negativo.
        self.stamina.spend(config.ROLL_STAMINA_COST)

    def _advance_roll(self, dt, level):
        """Mueve el rodar siguiendo la curva y lo termina al cumplir su duración."""
        # El último fotograma se recorta para no pasarse de la duración
        # aunque llegue un dt grande.
        step = min(dt, config.ROLL_DURATION - self._roll_elapsed)
        travelled_before = roll_progress(self._roll_elapsed)
        self._roll_elapsed += step

        # Se avanza la diferencia de progreso, no velocidad por tiempo: así
        # el rodar completo suma exactamente ROLL_DISTANCE.
        distance = config.ROLL_DISTANCE * (roll_progress(self._roll_elapsed) - travelled_before)
        dx, dy = self._roll_direction
        level.move_with_collision(self, dx * distance, dy * distance)

        # El margen evita un fotograma final de sobra que no movería nada,
        # por los redondeos de ir sumando dt.
        if self._roll_elapsed >= config.ROLL_DURATION - 1e-9:
            self.state = PlayerState.NORMAL

    # --- Caminar y correr -------------------------------------------------

    def _move_on_foot(self, dt, intent, level):
        """Camina o corre en la dirección pedida."""
        dx, dy = normalize(*intent.direction)
        if (dx, dy) == (0.0, 0.0):
            self.state = PlayerState.NORMAL
            return

        self.facing = (dx, dy)

        # Correr exige estamina: al vaciarse, se sigue andando sin más.
        if intent.run and self.stamina.has_any:
            self.stamina.spend(config.RUN_STAMINA_DRAIN * dt)
            self.state = PlayerState.RUNNING
            speed = config.RUN_SPEED
        else:
            self.state = PlayerState.NORMAL
            speed = self.speed

        distance = speed * dt
        level.move_with_collision(self, dx * distance, dy * distance)

    # --- Aspecto ----------------------------------------------------------

    def _refresh_sprite(self):
        """Elige el `sprite_id` según el estado; el color lo pone el tema."""
        if self.is_invulnerable:
            self.sprite_id = "player_invulnerable"
        elif self.is_rolling:
            self.sprite_id = "player_rolling"
        else:
            self.sprite_id = "player"
