"""Esqueleto arquero.

Reutiliza la máquina de estados de `Enemy` y solo cambia dos cosas: cómo
se coloca (mantiene las distancias en vez de echarse encima) y qué hace
al terminar el aviso (dispara en vez de dar un tajo). Si lo acorralas,
le queda un golpe cuerpo a cuerpo flojo.
"""

from game import config
from game.entities.enemy import ARCHER, Enemy, EnemyState
from game.systems.projectiles import Projectile


class Archer(Enemy):
    """Enemigo a distancia: tensa el arco, dispara y se aparta."""

    def __init__(self, x, y, profile=ARCHER):
        super().__init__(x, y, profile)
        # Tiempo que le falta para poder volver a disparar.
        self.shot_cooldown = 0.0
        # ¿El aviso en curso acabará en flecha o en tajo?
        self.is_aiming_shot = False
        # Flechas disparadas este fotograma, que el bucle recoge.
        self.pending_projectiles = []

    @property
    def is_aiming(self):
        """¿Está tensando el arco? Lo usa el modo depuración."""
        return self.state is EnemyState.WINDUP and self.is_aiming_shot

    def aim_line(self):
        """De dónde a dónde iría la flecha si disparara ahora."""
        start_x, start_y = self._arrow_origin()
        return (
            start_x,
            start_y,
            start_x + self.facing[0] * config.ARCHER_SHOOT_RANGE,
            start_y + self.facing[1] * config.ARCHER_SHOOT_RANGE,
        )

    def update(self, dt, level, player):
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        super().update(dt, level, player)

    # --- Comportamiento propio -------------------------------------------

    def _update_chasing(self, dt, level, player, sees_player):
        """Busca su distancia: ni encima ni fuera de alcance."""
        if self._should_give_up(player):
            self._enter(EnemyState.RETURNING)
            return

        distance = self.distance_to(player)

        # Acorralado: le queda el golpe cuerpo a cuerpo.
        if distance <= self.profile.attack_range:
            self.is_aiming_shot = False
            self._start_windup(player)
            return

        # Demasiado cerca: retrocede sin perderte de vista.
        if distance < config.ARCHER_MIN_DISTANCE:
            self._back_away(player, dt, level)
            return

        # A tiro y con el arco listo: tensa.
        if sees_player and distance <= config.ARCHER_SHOOT_RANGE and self.shot_cooldown <= 0:
            self.is_aiming_shot = True
            self._start_windup(player)
            return

        # Lejos: se acerca hasta su distancia de disparo.
        if distance > config.ARCHER_SHOOT_RANGE:
            self._move_towards(player.x, player.y, dt, level)

    def _update_windup(self, dt, level, player, sees_player):
        """Al acabar de tensar, suelta la flecha y se recupera."""
        if self.state_timer > 0:
            return
        if not self.is_aiming_shot:
            # Golpe cuerpo a cuerpo: igual que cualquier otro enemigo.
            super()._update_windup(dt, level, player, sees_player)
            return

        self._fire()
        self.is_aiming_shot = False
        self.shot_cooldown = config.ARCHER_SHOT_COOLDOWN
        # Dispara y queda vendido; no pasa por ATTACKING porque no hay tajo.
        self._enter(EnemyState.RECOVERY, config.ARCHER_SHOT_RECOVERY)

    def _start_windup(self, player):
        """Tensar el arco lleva más que levantar una espada."""
        duration = config.ARCHER_AIM_WINDUP if self.is_aiming_shot else self.profile.windup
        self.facing = self._direction_towards(player.x, player.y)
        self._enter(EnemyState.WINDUP, duration)

    def take_hit(self, damage, direction, level):
        """Un golpe le arruina la puntería."""
        super().take_hit(damage, direction, level)
        if self.state is EnemyState.STUNNED:
            self.is_aiming_shot = False

    # --- Apoyo ------------------------------------------------------------

    def _back_away(self, player, dt, level):
        """Se aleja del jugador, de espaldas, sin dejar de mirarle."""
        towards_x, towards_y = self._direction_towards(player.x, player.y)
        if (towards_x, towards_y) == (0.0, 0.0):
            return
        distance = self.profile.speed * dt
        level.move_with_collision(self, -towards_x * distance, -towards_y * distance)
        # Retrocede, pero sigue encarado hacia ti.
        self.facing = (towards_x, towards_y)

    def _arrow_origin(self):
        """Punto del que sale la flecha: justo delante del arquero."""
        offset = self.half_width + config.ARROW_WIDTH
        return (self.x + self.facing[0] * offset, self.y + self.facing[1] * offset)

    def _fire(self):
        """Suelta una flecha hacia donde apuntaba al empezar a tensar."""
        self.pending_projectiles.append(
            Projectile(
                *self._arrow_origin(),
                direction=self.facing,
                speed=config.ARROW_SPEED,
                damage=config.ARROW_DAMAGE,
                owner=self,
            )
        )
