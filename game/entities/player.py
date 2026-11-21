"""El jugador: se mueve en tiempo real y choca con los muros."""

import math

from game import config
from game.entities.entity import Entity


def normalize(dx, dy):
    """Devuelve el vector (dx, dy) con longitud 1, o (0, 0) si es nulo.

    Sin esto, moverse en diagonal sería más rápido que en línea recta
    (sqrt(2) veces más).
    """
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0
    return dx / length, dy / length


class Player(Entity):
    """Personaje controlado por el jugador."""

    def __init__(self, x, y):
        super().__init__(x, y, config.PLAYER_WIDTH, config.PLAYER_HEIGHT, "player")
        self.speed = config.PLAYER_SPEED

    @classmethod
    def at_level_start(cls, level):
        """Crea al jugador centrado en el tile '@' del mapa."""
        tile_x, tile_y = level.player_start
        return cls(*level.tile_center(tile_x, tile_y))

    def update(self, dt, direction, level):
        """Avanza un fotograma.

        `direction` es la intención de movimiento sin normalizar (por
        ejemplo (1, -1) para arriba-derecha); de normalizarla se encarga
        este método, así que quien lee el teclado no tiene que pensarlo.
        """
        dx, dy = normalize(*direction)
        if dx == 0 and dy == 0:
            return
        # Todo movimiento se multiplica por dt para no depender de los FPS.
        distance = self.speed * dt
        level.move_with_collision(self, dx * distance, dy * distance)
