"""Proyectiles: flechas y lo que venga después.

Un proyectil vuela en línea recta hasta chocar con un muro o acertar a
alguien, y solo golpea una vez porque al impactar desaparece.

Lógica pura: ni pygame ni dibujado.
"""

import math

from game import config
from game.entities.entity import Entity
from game.systems.combat import Box


class Projectile(Entity):
    """Algo que vuela recto y hace daño al llegar."""

    def __init__(self, x, y, direction, speed, damage, owner, sprite_id="arrow"):
        # El `sprite_id` es genérico: qué carácter le toca según hacia
        # dónde vuela lo decide el renderer, no la lógica.
        super().__init__(x, y, config.ARROW_WIDTH, config.ARROW_HEIGHT, sprite_id)
        self.direction = direction
        self.speed = speed
        self.damage = damage
        # Quién lo disparó: no se hiere a sí mismo y sirve para saber de
        # quién es el mérito cuando haya almas (Fase 4).
        self.owner = owner
        self.alive = True

    def advance(self, dt, level):
        """Avanza en línea recta; si entra en un muro, se destruye.

        El vuelo se trocea en pasos de medio tile para que una flecha
        rápida no se cuele a través de una pared fina.
        """
        dx = self.direction[0] * self.speed * dt
        dy = self.direction[1] * self.speed * dt
        steps = max(1, math.ceil(max(abs(dx), abs(dy)) / (level.tile_size / 2)))

        for _ in range(steps):
            self.x += dx / steps
            self.y += dy / steps
            if level.is_solid(
                math.floor(self.x / level.tile_size), math.floor(self.y / level.tile_size)
            ):
                self.alive = False
                return

    def hits(self, target):
        """¿Está encima de ese objetivo?"""
        return Box.from_entity(self).overlaps(Box.from_entity(target))


def update_projectiles(projectiles, dt, level, targets):
    """Avanza todos los proyectiles y reparte los impactos.

    Devuelve la lista de los que siguen vivos. Un proyectil que acierta
    desaparece, así que no puede golpear dos veces. Si el objetivo es
    invulnerable —rodando con i-frames, o con el respiro de un golpe
    reciente—, la flecha le **atraviesa** sin consumirse: esquivar es
    esquivar, no comerse el proyectil.
    """
    survivors = []
    for projectile in projectiles:
        projectile.advance(dt, level)
        if not projectile.alive:
            continue

        for target in targets:
            if target is projectile.owner or not target.is_alive:
                continue
            if not projectile.hits(target):
                continue
            if target.take_hit(projectile.damage, projectile.direction, level):
                projectile.alive = False
            break

        if projectile.alive:
            survivors.append(projectile)
    return survivors


def collect_pending(enemies):
    """Recoge los proyectiles que los enemigos han disparado este fotograma."""
    fired = []
    for enemy in enemies:
        pending = getattr(enemy, "pending_projectiles", None)
        if pending:
            fired.extend(pending)
            pending.clear()
    return fired
