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
from game.systems.stats import CharacterStats, EstusFlask, Health, Souls, Stamina


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
    drink: bool = False
    # Punto del mundo al que mirar, si hay un objetivo fijado. Con él
    # puesto, la mirada deja de seguir al movimiento. El jugador no sabe
    # nada de lock-on: solo recibe adónde mirar.
    look_at: tuple = None


class PlayerState(Enum):
    """Qué está haciendo el jugador ahora mismo."""

    NORMAL = auto()      # quieto o caminando
    RUNNING = auto()     # corriendo, gastando estamina
    ROLLING = auto()     # rodando: no acepta órdenes hasta terminar
    ATTACKING = auto()   # a mitad de un golpe
    DRINKING = auto()    # bebiendo Estus: lento e indefenso
    HURT = auto()        # encajando un golpe: no puede actuar


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
        self.stats = CharacterStats()
        self.health = Health(self.stats.max_health)
        self.estus = EstusFlask()
        self.souls = Souls()
        # Dónde reaparece al morir. De momento el '@' del mapa; en la
        # Fase 5 lo moverán las hogueras.
        self.respawn_point = (float(x), float(y))
        self.stamina = Stamina(
            self.stats.max_stamina, self.stats.stamina_regen, config.STAMINA_REGEN_DELAY
        )
        self.state = PlayerState.NORMAL
        # Última dirección en la que se movió; se rueda hacia aquí cuando
        # no se pulsa ninguna tecla de movimiento. Empieza mirando al sur.
        self.facing = (0.0, 1.0)
        self._roll_direction = (0.0, 0.0)
        self._roll_elapsed = 0.0
        self._attack_elapsed = 0.0
        self._drink_elapsed = 0.0
        # Si el trago en curso llevaba frasco de verdad.
        self._drink_has_flask = False
        # Lo que queda sin poder actuar y de invulnerabilidad, tras un golpe.
        self.hurt_timer = 0.0
        self.invulnerable_timer = 0.0
        # Mientras haya objetivo fijado, nada más puede cambiar la mirada.
        self.facing_is_locked = False
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
    def is_alive(self):
        return self.health.is_alive

    @property
    def is_hurt(self):
        """¿Está encajando un golpe, sin poder actuar?"""
        return self.state is PlayerState.HURT

    @property
    def is_roll_invulnerable(self):
        """¿Está en los i-frames del rodar?"""
        return (
            self.is_rolling
            and config.ROLL_IFRAME_START <= self._roll_elapsed < config.ROLL_IFRAME_END
        )

    @property
    def is_invulnerable(self):
        """¿Es inmune al daño ahora mismo?

        Dos motivos: los i-frames del rodar o el respiro que se concede
        tras encajar un golpe, para que no te encadenen varios seguidos.
        """
        return self.is_roll_invulnerable or self.invulnerable_timer > 0

    @property
    def attack_damage(self):
        """Daño del ataque ligero, según la Fuerza."""
        return self.stats.attack_damage

    @property
    def is_attacking(self):
        return self.state is PlayerState.ATTACKING

    @property
    def is_drinking(self):
        return self.state is PlayerState.DRINKING

    @property
    def is_busy(self):
        """¿Está metido en algo que no se puede interrumpir a voluntad?"""
        return self.is_rolling or self.is_attacking or self.is_drinking or self.is_hurt

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
        if self.is_rolling or self.is_hurt or self.is_drinking:
            return False
        if self.is_attacking and self.attack_phase is not AttackPhase.RECOVERY:
            return False
        return self.stamina.has_any

    @property
    def can_attack(self):
        """No se ataca rodando ni aturdido, ni encadenando sobre otro golpe."""
        return (
            not self.is_rolling
            and not self.is_attacking
            and not self.is_hurt
            and not self.is_drinking
            and self.stamina.has_any
        )

    @property
    def can_drink(self):
        """Solo se bebe con las manos libres; sin frascos, no pasa nada."""
        return not self.is_busy

    def attack_hitbox(self):
        """Caja del golpe mientras está activo; None el resto del tiempo."""
        if self.attack_phase is not AttackPhase.ACTIVE:
            return None
        return combat.attack_hitbox(self.x, self.y, self.facing, self.half_width)

    def level_up(self, attribute):
        """Sube una estadística pagando con almas. Devuelve si se ha podido."""
        cost = self.stats.next_level_cost
        if not self.souls.spend(cost):
            return False

        gain = self.stats.raise_stat(attribute)
        # Vigor y Resistencia suben también el valor actual, no solo el
        # máximo: subir de nivel cura un poco, como en Dark Souls.
        if attribute == "vigor":
            self.health.maximum = self.stats.max_health
            self.health.current += gain
        elif attribute == "endurance":
            self.stamina.maximum = self.stats.max_stamina
            self.stamina.current += gain
            self.stamina.regen_rate = self.stats.stamina_regen
        return True

    def rest(self):
        """Descansar en una hoguera: todo a tope."""
        self.health.heal(self.health.maximum)
        self.stamina.refill()
        self.estus.refill()
        self.state = PlayerState.NORMAL

    def revive(self):
        """Vuelve a la vida en su punto de reaparición, entero.

        No se crea un jugador nuevo: así se conservan el punto de
        reaparición y lo que vaya acumulando en fases siguientes.
        """
        self.x, self.y = self.respawn_point
        self.health.heal(self.health.maximum)
        self.stamina.refill()
        self.estus.refill()
        self.state = PlayerState.NORMAL
        self.hurt_timer = 0.0
        self.invulnerable_timer = 0.0
        self._roll_elapsed = 0.0
        self._attack_elapsed = 0.0
        self._drink_elapsed = 0.0
        self.attack_hits.clear()
        self._refresh_sprite()

    # --- Recibir golpes ---------------------------------------------------

    def take_hit(self, damage, direction, level):
        """Encaja un golpe, si es que llega a entrar.

        Devuelve False —y no pasa nada— si en este momento es inmune: en
        los i-frames del rodar o durante el respiro de un golpe anterior.
        """
        if self.is_invulnerable:
            return False

        self.health.take_damage(damage)
        combat.apply_knockback(self, direction, config.PLAYER_HURT_KNOCKBACK, level)
        self.hurt_timer = config.PLAYER_HURT_STUN
        self.invulnerable_timer = config.PLAYER_HURT_INVULNERABILITY
        self.state = PlayerState.HURT
        # El golpe corta en seco lo que estuviera haciendo.
        self.attack_hits.clear()
        return True

    # --- Fotograma --------------------------------------------------------

    def update(self, dt, intent, level):
        """Avanza un fotograma según lo que el jugador quiera hacer."""
        # La estamina se actualiza primero: así un gasto de este fotograma
        # reinicia el respiro y no se recupera nada hasta pasado el retraso.
        self.stamina.update(dt)
        self.souls.update(dt)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)

        # Con objetivo fijado la mirada apunta a él siempre, aunque se
        # esté rodando o atacando.
        self.facing_is_locked = intent.look_at is not None
        if self.facing_is_locked:
            self.facing = normalize(intent.look_at[0] - self.x, intent.look_at[1] - self.y)

        if self.is_hurt:
            self._advance_hurt(dt)
        elif self.is_rolling:
            # Rodando no se acepta nada: ni cambiar de rumbo ni rodar otra vez.
            self._advance_roll(dt, level)
        elif intent.roll and self.can_roll:
            # Rodar manda sobre atacar: es la salida de emergencia.
            self._start_roll(intent.direction)
            self._advance_roll(dt, level)
        elif self.is_drinking:
            self._advance_drink(dt, intent, level)
        elif self.is_attacking:
            self._advance_attack(dt, intent, level)
        elif intent.drink and self.can_drink:
            self._start_drink()
            self._advance_drink(dt, intent, level)
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
        if not self.facing_is_locked:
            # Con objetivo fijado se rueda de lado sin dejar de encararlo.
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

    # --- Encajar ----------------------------------------------------------

    def _advance_hurt(self, dt):
        """Aguanta el aturdimiento del golpe recibido, sin poder actuar."""
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        if self.hurt_timer <= 0:
            self.state = PlayerState.NORMAL

    # --- Beber Estus ------------------------------------------------------

    def _start_drink(self):
        """Se lleva el frasco a la boca. Sin frascos, solo es un gesto."""
        self._drink_elapsed = 0.0
        self.state = PlayerState.DRINKING
        # El frasco se pierde al empezar: si te golpean, lo has tirado.
        self._drink_has_flask = self.estus.drink()

    def _advance_drink(self, dt, intent, level):
        """Bebe despacio; la curación llega al terminar el trago."""
        duration = (
            config.ESTUS_DRINK_DURATION if self._drink_has_flask else config.ESTUS_EMPTY_DURATION
        )
        step = min(dt, duration - self._drink_elapsed)
        self._drink_elapsed += step

        # Bebiendo apenas se avanza, y no se cambia de rumbo.
        dx, dy = normalize(*intent.direction)
        if (dx, dy) != (0.0, 0.0):
            distance = self.speed * config.ESTUS_MOVE_FACTOR * step
            level.move_with_collision(self, dx * distance, dy * distance)

        if self._drink_elapsed >= duration - 1e-9:
            if self._drink_has_flask:
                self.health.heal(self.health.maximum * config.ESTUS_HEAL_FRACTION)
            self.state = PlayerState.NORMAL

    # --- Atacar -----------------------------------------------------------

    def _start_attack(self, direction):
        """Fija el rumbo del golpe y cobra la estamina."""
        dx, dy = normalize(*direction)
        if (dx, dy) != (0.0, 0.0) and not self.facing_is_locked:
            # Se golpea hacia donde se empuja; si no se empuja, hacia la
            # mirada. Con objetivo fijado, siempre hacia el objetivo.
            self.facing = (dx, dy)
        self._attack_elapsed = 0.0
        self._drink_elapsed = 0.0
        # Si el trago en curso llevaba frasco de verdad.
        self._drink_has_flask = False
        # Lo que queda sin poder actuar y de invulnerabilidad, tras un golpe.
        self.hurt_timer = 0.0
        self.invulnerable_timer = 0.0
        # Mientras haya objetivo fijado, nada más puede cambiar la mirada.
        self.facing_is_locked = False
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

        if not self.facing_is_locked:
            # Sin fijado, se mira hacia donde se anda. Con fijado, WASD
            # mueve alrededor del enemigo sin girar la mirada.
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
        if self.is_roll_invulnerable:
            self.sprite_id = "player_invulnerable"
        elif self.is_rolling:
            self.sprite_id = "player_rolling"
        elif self.invulnerable_timer > 0:
            # Parpadeo: alterna entre el glifo normal y el de herido.
            blink = int(self.invulnerable_timer / config.PLAYER_BLINK_INTERVAL) % 2
            self.sprite_id = "player_hurt" if blink else "player"
        elif self.is_drinking:
            self.sprite_id = "player_drinking"
        elif self.is_attacking:
            self.sprite_id = "player_attacking"
        else:
            self.sprite_id = "player"
