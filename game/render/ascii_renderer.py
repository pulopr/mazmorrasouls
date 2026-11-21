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

    def begin_frame(self):
        self.surface.fill(ascii_theme.BACKGROUND_COLOR)

    def draw_level(self, level, camera):
        """Dibuja los tiles visibles y el decorado del mapa."""
        # Solo se recorren los tiles que caen dentro de la cámara: en un
        # mapa grande, dibujarlo entero cada fotograma sería tirar trabajo.
        first_col, last_col = self._visible_range(camera.x, self.surface.get_width(), level.width)
        first_row, last_row = self._visible_range(camera.y, self.surface.get_height(), level.height)

        for tile_y in range(first_row, last_row + 1):
            for tile_x in range(first_col, last_col + 1):
                self._draw_sprite(level.tile_sprite_at(tile_x, tile_y), tile_x, tile_y, camera)

        # El decorado del mapa. La hoguera y los esqueletos todavía no son
        # entidades: se dibujan desde los datos del nivel.
        for tile_x, tile_y in level.bonfires:
            self._draw_sprite("bonfire", tile_x, tile_y, camera)
        for tile_x, tile_y, sprite_id in level.enemy_spawns:
            self._draw_sprite(sprite_id, tile_x, tile_y, camera)

    def draw_entity(self, entity, camera):
        """Dibuja una entidad en su posición continua, no en su tile."""
        glyph = self._glyph_surface(entity.sprite_id)
        screen_x, screen_y = camera.world_to_screen(entity.x, entity.y)
        self.surface.blit(glyph, glyph.get_rect(center=(round(screen_x), round(screen_y))))

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

    def _visible_range(self, camera_start, view_size, tile_count):
        """Primer y último índice de tile visible en un eje."""
        first = max(0, int(camera_start // self.tile_size))
        last = min(tile_count - 1, int((camera_start + view_size) // self.tile_size))
        return first, last

    def _draw_sprite(self, sprite_id, tile_x, tile_y, camera):
        """Dibuja un glifo centrado en el tile (tile_x, tile_y)."""
        glyph = self._glyph_surface(sprite_id)
        world_x = tile_x * self.tile_size + self.tile_size / 2
        world_y = tile_y * self.tile_size + self.tile_size / 2
        screen_x, screen_y = camera.world_to_screen(world_x, world_y)
        self.surface.blit(glyph, glyph.get_rect(center=(round(screen_x), round(screen_y))))
