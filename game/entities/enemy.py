"""Enemigos.

En la Fase 3a son muñecos de práctica: tienen vida, chocan con los muros
y encajan golpes, pero no se mueven solos. La IA (patrullar, perseguir y
atacar con aviso previo) llega en la Fase 3b.
"""

from game import config
from game.entities.entity import Entity
from game.systems import combat
from game.systems.stats import Health

# Vida inicial según el tipo de enemigo, por `sprite_id`.
HEALTH_BY_SPRITE = {
    "skeleton": config.SKELETON_HEALTH,
}


class Enemy(Entity):
    """Criatura hostil con vida."""

    def __init__(self, x, y, sprite_id="skeleton"):
        super().__init__(x, y, config.ENEMY_WIDTH, config.ENEMY_HEIGHT, sprite_id)
        self.base_sprite_id = sprite_id
        self.health = Health(HEALTH_BY_SPRITE.get(sprite_id, config.SKELETON_HEALTH))
        # Segundos que le quedan de parpadeo blanco tras recibir un golpe.
        self.hit_flash = 0.0

    @classmethod
    def spawn_from_level(cls, level):
        """Crea un enemigo por cada marca del mapa, centrado en su tile."""
        return [
            cls(*level.tile_center(tile_x, tile_y), sprite_id)
            for tile_x, tile_y, sprite_id in level.enemy_spawns
        ]

    @property
    def is_alive(self):
        return self.health.is_alive

    @property
    def is_hurt(self):
        """¿Ha perdido algo de vida? Lo usa el HUD para enseñar su barra."""
        return self.health.ratio < 1.0

    def take_hit(self, damage, direction, level):
        """Encaja un golpe: pierde vida, retrocede y parpadea."""
        self.health.take_damage(damage)
        self.hit_flash = config.ENEMY_HIT_FLASH
        if self.is_alive:
            # A los muertos no se les empuja: desaparecen en el acto.
            combat.apply_knockback(self, direction, config.ATTACK_KNOCKBACK, level)
        self._refresh_sprite()

    def update(self, dt, level):
        """Avanza un fotograma. De momento solo se le apaga el parpadeo."""
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        self._refresh_sprite()

    def _refresh_sprite(self):
        """Elige el `sprite_id`; el color lo pone el tema."""
        self.sprite_id = f"{self.base_sprite_id}_hit" if self.hit_flash > 0 else self.base_sprite_id
