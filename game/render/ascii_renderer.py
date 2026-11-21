"""Renderer ASCII: dibuja cada `sprite_id` como un carácter de fuente monoespaciada."""

import pygame

from game import config
from game.render import ascii_theme
from game.render.renderer import Renderer

# Fuentes monoespaciadas que se intentan por orden antes de recurrir a la
# fuente por defecto de pygame.
MONOSPACE_CANDIDATES = (
    "dejavusansmono",
    "liberationmono",
    "ubuntumono",
    "consolas",
    "couriernew",
    "monospace",
)

# El glifo se dibuja algo más grande que el tile para que los muros se vean
# densos y las paredes formen una línea continua.
FONT_SCALE = 1.15


def _load_monospace_font(size):
    """Carga la primera fuente monoespaciada disponible del sistema."""
    path = pygame.font.match_font(",".join(MONOSPACE_CANDIDATES))
    if path:
        return pygame.font.Font(path, size)
    # Último recurso: la fuente empaquetada con pygame. No es monoespaciada,
    # pero cada glifo se centra en su tile, así que la rejilla se mantiene.
    return pygame.font.Font(None, size)


class AsciiRenderer(Renderer):
    """Dibuja el mundo con caracteres sobre una rejilla de tiles."""

    def __init__(self, surface):
        self.surface = surface
        self.tile_size = config.TILE_SIZE
        self.font = _load_monospace_font(int(self.tile_size * FONT_SCALE))
        # Cada glifo se rasteriza una sola vez y se reutiliza.
        self._glyph_cache = {}

    # --- Interfaz ---------------------------------------------------------

    def draw_level(self, level):
        self.surface.fill(ascii_theme.BACKGROUND_COLOR)

        # Mientras no haya cámara (Fase 1), el mapa se centra en la ventana.
        origin_x = (self.surface.get_width() - level.width * self.tile_size) // 2
        origin_y = (self.surface.get_height() - level.height * self.tile_size) // 2

        # Primero el suelo y los muros...
        for y in range(level.height):
            for x in range(level.width):
                self._draw_sprite(level.tile_sprite_at(x, y), x, y, origin_x, origin_y)

        # ...y encima las entidades estáticas del mapa.
        for x, y in level.bonfires:
            self._draw_sprite("bonfire", x, y, origin_x, origin_y)
        for x, y, sprite_id in level.enemy_spawns:
            self._draw_sprite(sprite_id, x, y, origin_x, origin_y)
        player_x, player_y = level.player_start
        self._draw_sprite("player", player_x, player_y, origin_x, origin_y)

    def present(self):
        pygame.display.flip()

    # --- Interno ----------------------------------------------------------

    def _glyph_surface(self, sprite_id):
        """Superficie (cacheada) con el glifo de un `sprite_id`."""
        cached = self._glyph_cache.get(sprite_id)
        if cached is None:
            char, color = ascii_theme.glyph_for(sprite_id)
            cached = self.font.render(char, True, color)
            self._glyph_cache[sprite_id] = cached
        return cached

    def _draw_sprite(self, sprite_id, tile_x, tile_y, origin_x, origin_y):
        """Dibuja un glifo centrado en el tile (tile_x, tile_y)."""
        glyph = self._glyph_surface(sprite_id)
        center = (
            origin_x + tile_x * self.tile_size + self.tile_size // 2,
            origin_y + tile_y * self.tile_size + self.tile_size // 2,
        )
        self.surface.blit(glyph, glyph.get_rect(center=center))
