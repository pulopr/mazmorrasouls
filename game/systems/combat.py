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


def attack_hitbox(center_x, center_y, facing, body_half_size, reach=None, width=None):
    """Rectángulo del golpe, colocado delante de quien ataca.

    La caja se orienta según el eje dominante de la mirada: mirando de
    lado es ancha en vertical, y mirando arriba o abajo al revés. En
    diagonal se usa la orientación horizontal, desplazada en diagonal.

    `reach` y `width` permiten que cada enemigo tenga su propio alcance;
    sin ellos se usan los del ataque del jugador.
    """
    reach = config.ATTACK_REACH if reach is None else reach
    across = config.ATTACK_WIDTH if width is None else width

    dx, dy = facing
    if abs(dx) >= abs(dy):
        width, height = reach, across
    else:
        width, height = across, reach

    # Se separa del cuerpo lo justo y se centra a media distancia de alcance.
    distance = body_half_size + config.ATTACK_OFFSET + reach / 2
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


def resolve_enemy_attacks(enemies, player, level):
    """Aplica al jugador los golpes enemigos que estén activos.

    Cada ataque enemigo solo puede tocar una vez, aunque su hitbox dure
    varios fotogramas: lo recuerda la bandera `attack_has_hit`, que se
    repone al empezar cada ataque.

    Devuelve la lista de enemigos que han acertado en este fotograma.
    """
    if not player.is_alive:
        return []

    hits = []
    player_box = Box.from_entity(player)
    for enemy in enemies:
        if enemy.attack_has_hit:
            continue
        hitbox = enemy.attack_hitbox()
        if hitbox is None or not hitbox.overlaps(player_box):
            continue
        # Se marca aunque el jugador sea inmune: el golpe ya ha pasado por
        # él y no debe volver a intentarlo en el fotograma siguiente.
        enemy.attack_has_hit = True
        if player.take_hit(enemy.profile.damage, enemy.facing, level):
            hits.append(enemy)
    return hits


def separate_enemies(enemies, player, level):
    """Deshace los solapamientos: ni entre enemigos ni contra el jugador.

    Un empujón suave, sin velocidad ni inercia: a cada fotograma se
    reparte el solape. Al jugador no se le mueve —mandar sobre tu propio
    personaje se nota— así que de los dos solo cede el enemigo.
    """
    for index, enemy in enumerate(enemies):
        for other in enemies[index + 1:]:
            _push_apart(enemy, other, level, share=0.5)
        _push_apart(enemy, player, level, share=1.0)


def _push_apart(entity, other, level, share):
    """Separa dos cajas que se solapan por su eje de menor solape.

    `share` es cuánto del solape asume `entity`: 0.5 reparte a medias y
    1.0 lo pone todo de su lado.
    """
    overlap_x = min(entity.right, other.right) - max(entity.left, other.left)
    overlap_y = min(entity.bottom, other.bottom) - max(entity.top, other.top)
    if overlap_x <= 0 or overlap_y <= 0:
        return

    if overlap_x < overlap_y:
        direction = (1.0, 0.0) if entity.x >= other.x else (-1.0, 0.0)
        distance = overlap_x
    else:
        direction = (0.0, 1.0) if entity.y >= other.y else (0.0, -1.0)
        distance = overlap_y

    apply_knockback(entity, direction, distance * share, level)
    if share < 1.0:
        apply_knockback(other, (-direction[0], -direction[1]), distance * (1 - share), level)
