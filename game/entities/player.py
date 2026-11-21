"""El jugador: se mueve, corre y rueda, gastando estamina.

Los estados están explícitos en `PlayerState` porque la Fase 3 añadirá
atacar y recibir daño: cada estado decide qué se puede hacer y qué no.
"""

import math
from dataclasses import dataclass
from enum import Enum, auto

from game import config
from game.entities.entity import Entity
from game.systems import combat
from game.systems.stats import Health, Stamina


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
    attack: bool = False


class PlayerState(Enum):
    """Qué está haciendo el jugador ahora mismo."""

    NORMAL = auto()      # quieto o caminando
    RUNNING = auto()     # corriendo, gastando estamina
    ROLLING = auto()     # rodando: no acepta órdenes hasta terminar
    ATTACKING = auto()   # a mitad de un golpe


class AttackPhase(Enum):
    """Las tres partes de un golpe.

    No son estados aparte: se deducen del tiempo que lleva el ataque, de
    modo que la máquina de estados no se llena de casos.
    """

    WINDUP = auto()     # preparación: aún no hay hitbox
    ACTIVE = auto()     # el golpe existe y hace daño
    RECOVERY = auto()   # secuela: ya se puede cancelar rodando


class Player(Entity):
    """Personaje controlado por el jugador."""

    def __init__(self, x, y):
        super().__init__(x, y, config.PLAYER_WIDTH, config.PLAYER_HEIGHT, "player")
        self.speed = config.PLAYER_SPEED
        self.health = Health(config.PLAYER_HEALTH)
        self.stamina = Stamina(
            config.STAMINA_MAX, config.STAMINA_REGEN_RATE, config.STAMINA_REGEN_DELAY
        )
        self.state = PlayerState.NORMAL
        # Última dirección en la que se movió; se rueda hacia aquí cuando
        # no se pulsa ninguna tecla de movimiento. Empieza mirando al sur.
        self.facing = (0.0, 1.0)
        self._roll_direction = (0.0, 0.0)
        self._roll_elapsed = 0.0
        self._attack_elapsed = 0.0
        # Enemigos ya alcanzados por el ataque en curso, para no golpear
        # dos veces con el mismo tajo. Se vacía al empezar cada ataque.
        self.attack_hits = set()

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
    def is_attacking(self):
        return self.state is PlayerState.ATTACKING

    @property
    def attack_phase(self):
        """En qué parte del golpe está, o None si no está atacando."""
        if not self.is_attacking:
            return None
        if self._attack_elapsed < config.ATTACK_WINDUP:
            return AttackPhase.WINDUP
        if self._attack_elapsed < config.ATTACK_WINDUP + config.ATTACK_ACTIVE:
            return AttackPhase.ACTIVE
        return AttackPhase.RECOVERY

    @property
    def can_roll(self):
        """Se puede rodar con la barra casi vacía, pero no estando a 0.

        Atacando hay que aguantar hasta la recuperación: rodar antes
        cancelaría el golpe y sería gratis.
        """
        if self.is_rolling:
            return False
        if self.is_attacking and self.attack_phase is not AttackPhase.RECOVERY:
            return False
        return self.stamina.has_any

    @property
    def can_attack(self):
        """No se ataca rodando, ni encadenando sobre un golpe sin terminar."""
        return not self.is_rolling and not self.is_attacking and self.stamina.has_any

    def attack_hitbox(self):
        """Caja del golpe mientras está activo; None el resto del tiempo."""
        if self.attack_phase is not AttackPhase.ACTIVE:
            return None
        return combat.attack_hitbox(self.x, self.y, self.facing, self.half_width)

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
            # Rodar manda sobre atacar: es la salida de emergencia.
            self._start_roll(intent.direction)
            self._advance_roll(dt, level)
        elif self.is_attacking:
            self._advance_attack(dt, intent, level)
        elif intent.attack and self.can_attack:
            self._start_attack(intent.direction)
            self._advance_attack(dt, intent, level)
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
        # Rodando desde la recuperación de un golpe, ese golpe se da por
        # terminado: su hitbox ya no existe.
        self.attack_hits.clear()
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

    # --- Atacar -----------------------------------------------------------

    def _start_attack(self, direction):
        """Fija el rumbo del golpe y cobra la estamina."""
        dx, dy = normalize(*direction)
        if (dx, dy) != (0.0, 0.0):
            # Se golpea hacia donde se empuja; si no se empuja, hacia la mirada.
            self.facing = (dx, dy)
        self._attack_elapsed = 0.0
        self.attack_hits.clear()
        self.state = PlayerState.ATTACKING
        # Puede dejar la barra a 0, pero nunca en negativo.
        self.stamina.spend(config.ATTACK_STAMINA_COST)

    def _advance_attack(self, dt, intent, level):
        """Avanza el golpe y deja arrastrarse un poco mientras dura."""
        step = min(dt, config.ATTACK_DURATION - self._attack_elapsed)
        self._attack_elapsed += step

        # Atacando uno apenas se mueve, y nunca cambia de rumbo.
        dx, dy = normalize(*intent.direction)
        if (dx, dy) != (0.0, 0.0):
            distance = self.speed * config.ATTACK_MOVE_FACTOR * step
            level.move_with_collision(self, dx * distance, dy * distance)

        if self._attack_elapsed >= config.ATTACK_DURATION - 1e-9:
            self.state = PlayerState.NORMAL
            self.attack_hits.clear()

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
        elif self.is_attacking:
            self.sprite_id = "player_attacking"
        else:
            self.sprite_id = "player"
