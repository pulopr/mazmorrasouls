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
    # Rodando se apaga el color, y durante los i-frames se enciende en
    # cian para que se vea de un vistazo cuándo no te pueden tocar.
    "player_rolling": ("@", (115, 140, 185)),
    "player_invulnerable": ("@", (120, 235, 255)),
    # Los enemigos van en rojo para no confundirlos de un vistazo con el jugador.
    "skeleton": ("s", (200, 55, 45)),
    "bonfire": ("B", (235, 140, 45)),
}

# Aspecto de un `sprite_id` desconocido: visible a propósito, para que un
# fallo de datos se note en pantalla en lugar de pasar inadvertido.
FALLBACK_SPRITE = ("?", (255, 0, 255))


def glyph_for(sprite_id):
    """Devuelve (glifo, color) para un `sprite_id`."""
    return SPRITES.get(sprite_id, FALLBACK_SPRITE)


# --- HUD ------------------------------------------------------------------
# Colores de las barras, por identificador: (relleno, fondo).

BAR_COLORS = {
    "stamina": ((70, 200, 90), (24, 48, 30)),
}
BAR_BORDER_COLOR = (18, 18, 22)
FALLBACK_BAR = ((200, 200, 200), (40, 40, 40))


def bar_colors_for(bar_id):
    """Devuelve (color de relleno, color de fondo) de una barra del HUD."""
    return BAR_COLORS.get(bar_id, FALLBACK_BAR)
