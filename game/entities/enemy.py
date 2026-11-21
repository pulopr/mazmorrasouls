"""Enemigos y su máquina de estados.

Un enemigo es un cuerpo con vida más un **perfil** (`EnemyProfile`) que
reúne todos sus números: vida, velocidad, alcances, tiempos del ataque...
Añadir un tipo nuevo es escribir un perfil y, si hace falta, redefinir
algún método del comportamiento. El esqueleto no redefine ninguno.

Lógica pura: ni pygame ni dibujado.
"""

import math
from dataclasses import dataclass
from enum import Enum, auto

from game import config
from game.entities.entity import Entity
from game.systems import combat
from game.systems.stats import Health


class EnemyState(Enum):
    """Qué está haciendo un enemigo."""

    IDLE = auto()       # quieto en su sitio, esperando
    CHASING = auto()    # te ha visto y va a por ti
    WINDUP = auto()     # se para y avisa de que va a golpear
    ATTACKING = auto()  # el golpe existe y hace daño
    RECOVERY = auto()   # vendido un momento tras golpear
    STUNNED = auto()    # interrumpido por un golpe tuyo
    RETURNING = auto()  # te ha perdido, vuelve a su posición inicial


@dataclass(frozen=True)
class EnemyProfile:
    """Todos los números de un tipo de enemigo.

    Vive aparte del enemigo para que crear una variante sea escribir un
    perfil nuevo y no tocar el comportamiento.
    """

    sprite_id: str
    health: float
    speed: float
    damage: float
    detect_radius: float
    leash_radius: float
    attack_range: float
    windup: float
    active: float
    recovery: float
    attack_reach: float
    attack_width: float
    stun: float
    can_be_stunned: bool
    souls: int
    # Si es False, una vez derrotado no vuelve al reaparecer el jugador.
    respawns: bool = True
    sight_grace: float = config.ENEMY_SIGHT_GRACE


SKELETON = EnemyProfile(
    sprite_id="skeleton",
    health=config.SKELETON_HEALTH,
    speed=config.SKELETON_SPEED,
    damage=config.SKELETON_DAMAGE,
    detect_radius=config.SKELETON_DETECT_RADIUS,
    leash_radius=config.SKELETON_LEASH_RADIUS,
    attack_range=config.SKELETON_ATTACK_RANGE,
    windup=config.SKELETON_WINDUP,
    active=config.SKELETON_ACTIVE,
    recovery=config.SKELETON_RECOVERY,
    attack_reach=config.SKELETON_ATTACK_REACH,
    attack_width=config.SKELETON_ATTACK_WIDTH,
    stun=config.SKELETON_STUN,
    can_be_stunned=config.SKELETON_CAN_BE_STUNNED,
    souls=config.SKELETON_SOULS,
    respawns=config.SKELETON_RESPAWNS,
)

ELITE = EnemyProfile(
    sprite_id="elite",
    health=config.ELITE_HEALTH,
    speed=config.ELITE_SPEED,
    damage=config.ELITE_DAMAGE,
    detect_radius=config.ELITE_DETECT_RADIUS,
    leash_radius=config.ELITE_LEASH_RADIUS,
    attack_range=config.ELITE_ATTACK_RANGE,
    windup=config.ELITE_WINDUP,
    active=config.ELITE_ACTIVE,
    recovery=config.ELITE_RECOVERY,
    attack_reach=config.ELITE_ATTACK_REACH,
    attack_width=config.ELITE_ATTACK_WIDTH,
    stun=config.ELITE_STUN,
    can_be_stunned=config.ELITE_CAN_BE_STUNNED,
    souls=config.ELITE_SOULS,
    respawns=config.ELITE_RESPAWNS,
)

ARCHER = EnemyProfile(
    sprite_id="archer",
    health=config.ARCHER_HEALTH,
    speed=config.ARCHER_SPEED,
    damage=config.ARCHER_DAMAGE,
    detect_radius=config.ARCHER_DETECT_RADIUS,
    leash_radius=config.ARCHER_LEASH_RADIUS,
    attack_range=config.ARCHER_ATTACK_RANGE,
    windup=config.ARCHER_WINDUP,
    active=config.ARCHER_ACTIVE,
    recovery=config.ARCHER_RECOVERY,
    attack_reach=config.ARCHER_ATTACK_REACH,
    attack_width=config.ARCHER_ATTACK_WIDTH,
    stun=config.ARCHER_STUN,
    can_be_stunned=config.ARCHER_CAN_BE_STUNNED,
    souls=config.ARCHER_SOULS,
    respawns=config.ARCHER_RESPAWNS,
)

# Perfil que usa cada carácter del mapa.
PROFILES = {
    "s": SKELETON,
    "D": ELITE,
    "A": ARCHER,
}


class Enemy(Entity):
    """Criatura hostil con vida y un comportamiento por estados."""

    def __init__(self, x, y, profile=SKELETON):
        super().__init__(x, y, config.ENEMY_WIDTH, config.ENEMY_HEIGHT, profile.sprite_id)
        self.profile = profile
        self.health = Health(profile.health)
        # Su sitio: adonde vuelve cuando te pierde.
        self.home = (float(x), float(y))
        self.facing = (0.0, 1.0)

        self.state = EnemyState.IDLE
        # Lo que le queda del estado actual, cuando el estado dura un tiempo.
        self.state_timer = 0.0
        # Desde cuándo no te ve; si pasa de `sight_grace`, se vuelve.
        self.time_unseen = 0.0
        # Segundos que le quedan de parpadeo blanco tras recibir un golpe.
        self.hit_flash = 0.0
        # Un mismo ataque solo te toca una vez.
        self.attack_has_hit = False
        # Proyectiles disparados este fotograma; solo los usa el arquero.
        self.pending_projectiles = []
        # Su puesto en la lista del mapa; lo rellena spawn_from_level().
        self.spawn_index = None

    @classmethod
    def spawn_from_level(cls, level, skip=()):
        """Crea un enemigo por cada marca del mapa, centrado en su tile.

        `skip` son los índices de los que no deben volver a aparecer: los
        élite ya derrotados.
        """
        # Import tardío: Archer hereda de Enemy y no puede importarse arriba.
        from game.entities.archer import Archer

        enemies = []
        for index, (tile_x, tile_y, enemy_char) in enumerate(level.enemy_spawns):
            profile = PROFILES[enemy_char]
            if index in skip:
                continue
            enemy_class = Archer if profile is ARCHER else cls
            enemy = enemy_class(*level.tile_center(tile_x, tile_y), profile)
            # Su puesto en el mapa: sirve para saber quién no debe volver.
            enemy.spawn_index = index
            enemies.append(enemy)
        return enemies

    # --- Consultas --------------------------------------------------------

    @property
    def is_alive(self):
        return self.health.is_alive

    @property
    def is_hurt(self):
        """¿Ha perdido algo de vida? Lo usa el HUD para enseñar su barra."""
        return self.health.ratio < 1.0

    @property
    def is_telegraphing(self):
        """¿Está avisando de un golpe? El renderer lo pinta en amarillo."""
        return self.state is EnemyState.WINDUP

    def attack_hitbox(self):
        """Caja del golpe mientras está activo; None el resto del tiempo."""
        if self.state is not EnemyState.ATTACKING:
            return None
        return combat.attack_hitbox(
            self.x,
            self.y,
            self.facing,
            self.half_width,
            reach=self.profile.attack_reach,
            width=self.profile.attack_width,
        )

    def distance_to(self, other):
        return math.hypot(other.x - self.x, other.y - self.y)

    def can_see(self, target, level):
        """¿Está a tiro de vista y sin muros de por medio?"""
        if self.distance_to(target) > self.profile.detect_radius:
            return False
        return level.has_line_of_sight(self.x, self.y, target.x, target.y)

    # --- Recibir golpes ---------------------------------------------------

    def take_hit(self, damage, direction, level):
        """Encaja un golpe: pierde vida, retrocede, parpadea y se aturde."""
        self.health.take_damage(damage)
        self.hit_flash = config.ENEMY_HIT_FLASH
        if not self.is_alive:
            # A los muertos no se les empuja: desaparecen en el acto.
            self._refresh_sprite()
            return

        combat.apply_knockback(self, direction, config.ATTACK_KNOCKBACK, level)
        if self.profile.can_be_stunned:
            # El aturdimiento cancela lo que estuviera haciendo, aviso incluido.
            self._enter(EnemyState.STUNNED, self.profile.stun)
        self._refresh_sprite()

    # --- Fotograma --------------------------------------------------------

    def update(self, dt, level, player):
        """Avanza un fotograma de comportamiento."""
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        self.state_timer = max(0.0, self.state_timer - dt)

        sees_player = player.is_alive and self.can_see(player, level)
        self.time_unseen = 0.0 if sees_player else self.time_unseen + dt

        handler = {
            EnemyState.IDLE: self._update_idle,
            EnemyState.CHASING: self._update_chasing,
            EnemyState.WINDUP: self._update_windup,
            EnemyState.ATTACKING: self._update_attacking,
            EnemyState.RECOVERY: self._update_recovery,
            EnemyState.STUNNED: self._update_stunned,
            EnemyState.RETURNING: self._update_returning,
        }[self.state]
        handler(dt, level, player, sees_player)

        self._refresh_sprite()

    # --- Un método por estado ---------------------------------------------
    # Todos reciben lo mismo, así que un tipo nuevo puede redefinir solo
    # el que le interese (el arquero cambia la persecución y el ataque).

    def _update_idle(self, dt, level, player, sees_player):
        """Quieto hasta que te ve."""
        if sees_player:
            self._enter(EnemyState.CHASING)

    def _update_chasing(self, dt, level, player, sees_player):
        """Va hacia ti; si llega a distancia de golpe, avisa."""
        if self._should_give_up(player):
            self._enter(EnemyState.RETURNING)
            return
        if self.distance_to(player) <= self.profile.attack_range:
            self._start_windup(player)
            return
        self._move_towards(player.x, player.y, dt, level)

    def _update_windup(self, dt, level, player, sees_player):
        """Avisa un momento; la dirección ya quedó fijada al empezar."""
        if self.state_timer <= 0:
            self.attack_has_hit = False
            self._enter(EnemyState.ATTACKING, self.profile.active)

    def _update_attacking(self, dt, level, player, sees_player):
        """El golpe está activo; no corrige el rumbo."""
        if self.state_timer <= 0:
            self._enter(EnemyState.RECOVERY, self.profile.recovery)

    def _update_recovery(self, dt, level, player, sees_player):
        """Vendido un momento antes de volver a la carga."""
        if self.state_timer <= 0:
            self._enter(EnemyState.CHASING if sees_player else EnemyState.RETURNING)

    def _update_stunned(self, dt, level, player, sees_player):
        """Interrumpido: no hace nada hasta recomponerse."""
        if self.state_timer <= 0:
            self._enter(EnemyState.CHASING if sees_player else EnemyState.RETURNING)

    def _update_returning(self, dt, level, player, sees_player):
        """Vuelve a su sitio, salvo que te vuelva a ver por el camino."""
        if sees_player:
            self._enter(EnemyState.CHASING)
            return
        home_x, home_y = self.home
        if math.hypot(home_x - self.x, home_y - self.y) <= self.profile.speed * dt:
            self.x, self.y = home_x, home_y
            self._enter(EnemyState.IDLE)
            return
        self._move_towards(home_x, home_y, dt, level)

    # --- Apoyo ------------------------------------------------------------

    def _enter(self, state, duration=0.0):
        """Cambia de estado y fija cuánto dura, si es que dura."""
        self.state = state
        self.state_timer = duration

    def _start_windup(self, player):
        """Se planta y apunta. El rumbo se fija aquí y ya no se corrige."""
        self.facing = self._direction_towards(player.x, player.y)
        self._enter(EnemyState.WINDUP, self.profile.windup)

    def _should_give_up(self, player):
        """¿Te ha perdido, por distancia o por no verte en un rato?"""
        if not player.is_alive:
            return True
        if self.distance_to(player) > self.profile.leash_radius:
            return True
        return self.time_unseen > self.profile.sight_grace

    def _direction_towards(self, target_x, target_y):
        """Vector unitario hacia un punto; (0, 0) si ya se está ahí."""
        dx, dy = target_x - self.x, target_y - self.y
        length = math.hypot(dx, dy)
        if length == 0:
            return (0.0, 0.0)
        return (dx / length, dy / length)

    def _move_towards(self, target_x, target_y, dt, level, speed=None):
        """Avanza hacia un punto, chocando con los muros."""
        dx, dy = self._direction_towards(target_x, target_y)
        if (dx, dy) == (0.0, 0.0):
            return
        self.facing = (dx, dy)
        distance = (self.profile.speed if speed is None else speed) * dt
        level.move_with_collision(self, dx * distance, dy * distance)

    def _refresh_sprite(self):
        """Elige el `sprite_id`; el color lo pone el tema."""
        base = self.profile.sprite_id
        if self.hit_flash > 0:
            self.sprite_id = f"{base}_hit"
        elif self.is_telegraphing:
            self.sprite_id = f"{base}_windup"
        else:
            self.sprite_id = base
