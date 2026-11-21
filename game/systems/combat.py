"""Hitboxes y daño.

Todo lo que pasa cuando alguien golpea a alguien: dónde cae el golpe, a
quién alcanza y qué efecto tiene. Lógica pura, sin pygame y sin dibujar.
"""

from dataclasses import dataclass

from game import config


@dataclass(frozen=True)
class Box:
    """Rectángulo alineado a los ejes, medido desde su esquina superior izquierda."""

    left: float
    top: float
    width: float
    height: float

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def center(self):
        return (self.left + self.width / 2, self.top + self.height / 2)

    @classmethod
    def from_entity(cls, entity):
        """La caja de colisión de una entidad."""
        return cls(entity.left, entity.top, entity.width, entity.height)

    def overlaps(self, other):
        """¿Se tocan las dos cajas? Rozarse por el borde no cuenta."""
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )


def attack_hitbox(center_x, center_y, facing, body_half_size):
    """Rectángulo del golpe, colocado delante de quien ataca.

    La caja se orienta según el eje dominante de la mirada: mirando de
    lado es ancha en vertical, y mirando arriba o abajo al revés. En
    diagonal se usa la orientación horizontal, desplazada en diagonal.
    """
    dx, dy = facing
    if abs(dx) >= abs(dy):
        width, height = config.ATTACK_REACH, config.ATTACK_WIDTH
    else:
        width, height = config.ATTACK_WIDTH, config.ATTACK_REACH

    # Se separa del cuerpo lo justo y se centra a media distancia de alcance.
    distance = body_half_size + config.ATTACK_OFFSET + config.ATTACK_REACH / 2
    hit_x = center_x + dx * distance
    hit_y = center_y + dy * distance
    return Box(hit_x - width / 2, hit_y - height / 2, width, height)


def apply_knockback(entity, direction, distance, level):
    """Empuja a una entidad, frenándola contra los muros."""
    dx, dy = direction
    level.move_with_collision(entity, dx * distance, dy * distance)


def resolve_player_attack(player, enemies, level):
    """Reparte el golpe activo del jugador entre los enemigos que alcanza.

    Un mismo ataque solo toca a cada enemigo una vez, aunque la hitbox
    siga encima varios fotogramas: los ya golpeados se apuntan en
    `player.attack_hits`, que se vacía al empezar cada ataque.

    Devuelve la lista de enemigos golpeados en este fotograma.
    """
    hitbox = player.attack_hitbox()
    if hitbox is None:
        return []

    hits = []
    for enemy in enemies:
        if enemy in player.attack_hits or not enemy.is_alive:
            continue
        if hitbox.overlaps(Box.from_entity(enemy)):
            player.attack_hits.add(enemy)
            enemy.take_hit(config.ATTACK_DAMAGE, player.facing, level)
            hits.append(enemy)
    return hits
