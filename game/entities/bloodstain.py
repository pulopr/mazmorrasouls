"""Mancha de sangre: las almas que soltaste al morir.

Solo puede existir una. Al morir, la anterior se pierde para siempre y
—si llevabas algo— nace una nueva donde caíste. Llegar hasta ella y
pulsar E devuelve las almas.

Lógica pura: ni pygame ni dibujado.
"""

import math

from game import config
from game.entities.entity import Entity
from game.systems.combat import Box


class Bloodstain(Entity):
    """Un montón de almas esperando en el suelo."""

    def __init__(self, x, y, souls):
        super().__init__(x, y, config.TILE_SIZE, config.TILE_SIZE, "bloodstain")
        self.souls = int(souls)
        # Para el parpadeo: avanza con el tiempo y no se reinicia nunca.
        self.age = 0.0

    @classmethod
    def drop(cls, level, x, y, souls, blockers=()):
        """Deja una mancha en (x, y), o en el suelo libre más cercano.

        Morir dentro de un muro o encima de un enemigo dejaría la mancha
        donde no se puede recoger, así que en ese caso se busca la
        casilla transitable más próxima que no esté ocupada.
        """
        tile_x, tile_y = level.tile_of(x, y)

        def occupied(check_x, check_y):
            centre_x, centre_y = level.tile_center(check_x, check_y)
            here = Box(
                centre_x - level.tile_size / 2,
                centre_y - level.tile_size / 2,
                level.tile_size,
                level.tile_size,
            )
            return any(here.overlaps(Box.from_entity(blocker)) for blocker in blockers)

        if not level.is_solid(tile_x, tile_y) and not occupied(tile_x, tile_y):
            # El sitio de la muerte vale tal cual.
            return cls(x, y, souls)

        spot = level.nearest_free_tile(tile_x, tile_y, is_blocked=occupied)
        if spot is None:
            # Mapa imposible; mejor dejarla donde cayó que perderla.
            return cls(x, y, souls)
        return cls(*level.tile_center(*spot), souls)

    def can_be_reached_by(self, player):
        """¿Está el jugador lo bastante cerca para recogerla con E?"""
        distance = math.hypot(player.x - self.x, player.y - self.y)
        return distance <= config.BLOODSTAIN_PICKUP_RADIUS

    def collect(self):
        """Devuelve las almas. Quien la recoge debe quitarla del mundo."""
        souls = self.souls
        self.souls = 0
        return souls

    def update(self, dt):
        """Avanza el parpadeo."""
        self.age += dt
        self._refresh_sprite()

    def _refresh_sprite(self):
        """Alterna entre dos verdes para que se vea desde lejos."""
        half = config.BLOODSTAIN_BLINK_PERIOD / 2
        bright = (self.age % config.BLOODSTAIN_BLINK_PERIOD) < half
        self.sprite_id = "bloodstain" if bright else "bloodstain_dim"
