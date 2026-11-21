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
    "player_attacking": ("@", (255, 230, 160)),
    # Los enemigos van en rojo para no confundirlos de un vistazo con el jugador.
    "skeleton": ("s", (200, 55, 45)),
    # Fogonazo blanco del instante en que encaja un golpe.
    "skeleton_hit": ("s", (255, 255, 255)),
    # Tajos: el carácter depende de hacia dónde se golpea.
    "slash_horizontal": ("-", (255, 245, 200)),
    "slash_vertical": ("|", (255, 245, 200)),
    "slash_diagonal_down": ("\\", (255, 245, 200)),
    "slash_diagonal_up": ("/", (255, 245, 200)),
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
    "health": ((205, 55, 55), (52, 22, 22)),
    "enemy_health": ((205, 55, 55), (40, 18, 18)),
}
BAR_BORDER_COLOR = (18, 18, 22)
FALLBACK_BAR = ((200, 200, 200), (40, 40, 40))


def bar_colors_for(bar_id):
    """Devuelve (color de relleno, color de fondo) de una barra del HUD."""
    return BAR_COLORS.get(bar_id, FALLBACK_BAR)


def slash_sprite_for(facing):
    """Elige el carácter del tajo según hacia dónde se golpea.

    Horizontal `-`, vertical `|` y las diagonales `\\` o `/` según si la
    hoja baja o sube.
    """
    dx, dy = facing
    if dx != 0 and dy != 0:
        # El mismo signo baja hacia la derecha; signos distintos, sube.
        return "slash_diagonal_down" if dx * dy > 0 else "slash_diagonal_up"
    if dy == 0:
        return "slash_horizontal"
    return "slash_vertical"


# --- Depuración (F1) ------------------------------------------------------
# Color del contorno de cada tipo de caja.

DEBUG_BOX_COLORS = {
    "collision": (90, 150, 255),
    "hitbox": (255, 90, 90),
}
FALLBACK_DEBUG_BOX = (255, 255, 0)


def debug_box_color_for(box_id):
    """Color del contorno de una caja de depuración."""
    return DEBUG_BOX_COLORS.get(box_id, FALLBACK_DEBUG_BOX)
