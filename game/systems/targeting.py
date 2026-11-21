"""Fijado de objetivo (lock-on).

Decide a qué enemigo se apunta, cuándo se cambia y cuándo se suelta.
No toca al jugador: quien lo usa le pasa el punto al que mirar, de modo
que `Player` nunca sabe qué es un objetivo fijado.

Lógica pura: ni pygame ni dibujado.
"""

import math

from game import config


def _distance(a, b):
    return math.hypot(b.x - a.x, b.y - a.y)


def _angle_from(player, enemy):
    """Ángulo del enemigo visto desde el jugador, en radianes.

    Ojo: la `y` crece hacia abajo, así que el ángulo crece en el sentido
    de las agujas del reloj tal y como se ve en pantalla. Es lo que hace
    que la flecha derecha recorra los enemigos hacia la derecha.
    """
    return math.atan2(enemy.y - player.y, enemy.x - player.x)


def is_targetable(enemy, player, level, radius):
    """¿Se puede fijar a este enemigo? Vivo, cerca y a la vista."""
    if not enemy.is_alive:
        return False
    if _distance(player, enemy) > radius:
        return False
    return level.has_line_of_sight(player.x, player.y, enemy.x, enemy.y)


def targetable(player, enemies, level, radius=None):
    """Todos los enemigos que se pueden fijar ahora mismo."""
    radius = config.LOCK_ON_RADIUS if radius is None else radius
    return [enemy for enemy in enemies if is_targetable(enemy, player, level, radius)]


def best_target(player, enemies, level):
    """El candidato más cercano, con preferencia por los que están delante.

    La puntuación es la distancia penalizada por el ángulo respecto a la
    mirada: lo que queda a la espalda tiene que estar bastante más cerca
    para ganar. Devuelve None si no hay a quién fijar.
    """
    best = None
    best_score = None
    for enemy in targetable(player, enemies, level):
        distance = _distance(player, enemy)
        if distance == 0:
            return enemy

        # Coseno del ángulo entre la mirada y la dirección al enemigo:
        # 1 justo delante, -1 justo detrás.
        facing_x, facing_y = player.facing
        alignment = ((enemy.x - player.x) * facing_x + (enemy.y - player.y) * facing_y) / distance
        penalty = 1 + config.LOCK_ON_FRONT_BIAS * (1 - alignment) / 2

        score = distance * penalty
        if best_score is None or score < best_score:
            best, best_score = enemy, score
    return best


def camera_focus(player, target):
    """Punto que debe seguir la cámara.

    Sin objetivo, el jugador. Con él, un poco desplazado hacia el enemigo
    para que entre en pantalla, pero sin dejar de centrarse en el jugador.
    """
    if target is None:
        return (player.x, player.y)
    bias = config.LOCK_ON_CAMERA_BIAS
    return (
        player.x + (target.x - player.x) * bias,
        player.y + (target.y - player.y) * bias,
    )


class LockOn:
    """Recuerda a quién se está apuntando y lo mantiene al día."""

    def __init__(self):
        self.target = None
        # Cuánto lleva sin verse al objetivo fijado.
        self.time_unseen = 0.0

    @property
    def is_locked(self):
        return self.target is not None

    def look_at(self):
        """Punto al que debe mirar el jugador, o None si no hay objetivo."""
        if self.target is None:
            return None
        return (self.target.x, self.target.y)

    # --- Órdenes ----------------------------------------------------------

    def release(self):
        """Suelta el objetivo."""
        self.target = None
        self.time_unseen = 0.0

    def acquire(self, player, enemies, level):
        """Fija el mejor candidato. Devuelve si lo ha conseguido."""
        self.target = best_target(player, enemies, level)
        self.time_unseen = 0.0
        return self.is_locked

    def toggle(self, player, enemies, level):
        """Fija si no había nada fijado; si lo había, lo suelta."""
        if self.is_locked:
            self.release()
            return False
        return self.acquire(player, enemies, level)

    def cycle(self, step, player, enemies, level):
        """Salta al siguiente objetivo en un sentido, ordenados por ángulo.

        `step` es +1 (sentido horario en pantalla: hacia la derecha) o -1.
        """
        if not self.is_locked:
            return False

        options = sorted(targetable(player, enemies, level), key=lambda e: _angle_from(player, e))
        if not options:
            self.release()
            return False

        if self.target in options:
            index = (options.index(self.target) + step) % len(options)
            self.target = options[index]
        else:
            # El de antes ya no vale: se empieza por el mejor que quede.
            self.target = best_target(player, enemies, level)

        self.time_unseen = 0.0
        return self.is_locked

    # --- Mantenimiento ----------------------------------------------------

    def update(self, dt, player, enemies, level):
        """Suelta o reengancha el objetivo según cómo haya cambiado el mundo."""
        if not self.is_locked:
            return

        # Muerto o desaparecido: salta al siguiente que valga.
        if not self.target.is_alive or self.target not in enemies:
            self.acquire(player, enemies, level)
            return

        if _distance(player, self.target) > config.LOCK_ON_BREAK_RADIUS:
            self.release()
            return

        if level.has_line_of_sight(player.x, player.y, self.target.x, self.target.y):
            self.time_unseen = 0.0
        else:
            self.time_unseen += dt
            if self.time_unseen > config.LOCK_ON_SIGHT_GRACE:
                self.release()
