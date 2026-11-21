"""Hogueras: punto de reaparición y descanso.

La primera vez que se interactúa con una se enciende y pasa a ser el
sitio donde reaparecerás. Encendida, volver a ella permite descansar.

Lógica pura: ni pygame ni dibujado.
"""

import math

from game import config
from game.entities.entity import Entity


class Bonfire(Entity):
    """Una hoguera del mapa, apagada hasta que la enciendes."""

    def __init__(self, x, y):
        super().__init__(x, y, config.TILE_SIZE, config.TILE_SIZE, "bonfire")
        self.lit = False
        # Para el parpadeo del fuego.
        self.age = 0.0

    @classmethod
    def spawn_from_level(cls, level):
        """Una hoguera por cada 'B' del mapa."""
        return [cls(*level.tile_center(tile_x, tile_y)) for tile_x, tile_y in level.bonfires]

    def is_within_reach(self, player):
        """¿Está el jugador lo bastante cerca para usarla con E?"""
        distance = math.hypot(player.x - self.x, player.y - self.y)
        return distance <= config.BONFIRE_INTERACT_RADIUS

    def light(self):
        """La enciende. Devuelve si estaba apagada (es decir, si es nuevo)."""
        if self.lit:
            return False
        self.lit = True
        return True

    def update(self, dt):
        self.age += dt
        self._refresh_sprite()

    def _refresh_sprite(self):
        """Apagada en un tono, encendida parpadeando entre dos."""
        if not self.lit:
            self.sprite_id = "bonfire"
            return
        half = config.BONFIRE_FLICKER_PERIOD / 2
        bright = (self.age % config.BONFIRE_FLICKER_PERIOD) < half
        self.sprite_id = "bonfire_lit" if bright else "bonfire_lit_dim"
