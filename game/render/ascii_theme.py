"""Tablas de glifos y colores por `sprite_id`.

Único lugar donde se decide el aspecto de las cosas en modo ASCII. Cuando
se sustituya el ASCII por sprites, bastará con una tabla equivalente de
imágenes: la lógica seguirá hablando solo de `sprite_id`.
"""

# Color de fondo de la pantalla (fuera del mapa).
BACKGROUND_COLOR = (12, 12, 16)

# sprite_id -> (glifo, color RGB)
SPRITES = {
    # Tiles
    "floor": (".", (70, 68, 62)),
    "wall": ("#", (130, 124, 110)),
    "door": ("+", (160, 120, 60)),
    # Entidades
    "player": ("@", (235, 235, 225)),
    "skeleton": ("s", (200, 205, 210)),
    "bonfire": ("B", (235, 140, 45)),
}

# Aspecto de un `sprite_id` desconocido: visible a propósito, para que un
# fallo de datos se note en pantalla en lugar de pasar inadvertido.
FALLBACK_SPRITE = ("?", (255, 0, 255))


def glyph_for(sprite_id):
    """Devuelve (glifo, color) para un `sprite_id`."""
    return SPRITES.get(sprite_id, FALLBACK_SPRITE)
