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
        # Fuentes aparte para los carteles y para las etiquetas de depuración.
        self.message_font = _load_monospace_font(
            int(self.tile_size * FONT_SCALE * ascii_theme.MESSAGE_FONT_SCALE)
        )
        self.debug_font = _load_monospace_font(max(10, int(self.tile_size * 0.4)))
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

        # El decorado del mapa. La hoguera todavía no es una entidad; los
        # enemigos sí, y los dibuja el bucle con draw_entity().
        for tile_x, tile_y in level.bonfires:
            self._draw_sprite("bonfire", tile_x, tile_y, camera)

    def draw_entity(self, entity, camera):
        """Dibuja una entidad en su posición continua, no en su tile."""
        self._blit_glyph(entity.sprite_id, *camera.world_to_screen(entity.x, entity.y))

    def draw_attack(self, x, y, facing, camera):
        """Pinta el carácter de tajo que corresponde a la dirección."""
        self._blit_glyph(ascii_theme.slash_sprite_for(facing), *camera.world_to_screen(x, y))

    def draw_world_bar(self, bar_id, x, y, width, height, ratio, camera):
        """Barrita en el mundo: se convierte a pantalla y se delega en draw_bar."""
        screen_x, screen_y = camera.world_to_screen(x, y)
        self.draw_bar(bar_id, round(screen_x), round(screen_y), width, height, ratio)

    def draw_box_outline(self, box, camera, box_id):
        """Contorno de una caja del mundo, para el modo depuración."""
        screen_x, screen_y = camera.world_to_screen(box.left, box.top)
        pygame.draw.rect(
            self.surface,
            ascii_theme.debug_box_color_for(box_id),
            (round(screen_x), round(screen_y), round(box.width), round(box.height)),
            1,
        )

    def draw_circle_outline(self, x, y, radius, camera):
        """Circunferencia en coordenadas del mundo (radio de detección)."""
        screen_x, screen_y = camera.world_to_screen(x, y)
        pygame.draw.circle(
            self.surface,
            ascii_theme.DEBUG_RADIUS_COLOR,
            (round(screen_x), round(screen_y)),
            round(radius),
            1,
        )

    def draw_debug_text(self, text, x, y, camera):
        """Etiqueta pequeña sobre un punto del mundo."""
        screen_x, screen_y = camera.world_to_screen(x, y)
        label = self.debug_font.render(text, True, ascii_theme.DEBUG_TEXT_COLOR)
        self.surface.blit(label, label.get_rect(center=(round(screen_x), round(screen_y))))

    def draw_message(self, text):
        """Cartel grande centrado en la pantalla."""
        label = self.message_font.render(text, True, ascii_theme.MESSAGE_COLOR)
        center = (self.surface.get_width() // 2, self.surface.get_height() // 2)
        self.surface.blit(label, label.get_rect(center=center))

    def draw_bar(self, bar_id, x, y, width, height, ratio):
        """Barra del HUD: fondo, relleno proporcional y borde."""
        fill_color, back_color = ascii_theme.bar_colors_for(bar_id)
        ratio = max(0.0, min(1.0, ratio))

        pygame.draw.rect(self.surface, back_color, (x, y, width, height))
        filled_width = round(width * ratio)
        if filled_width > 0:
            pygame.draw.rect(self.surface, fill_color, (x, y, filled_width, height))
        pygame.draw.rect(self.surface, ascii_theme.BAR_BORDER_COLOR, (x, y, width, height), 1)

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
        world_x = tile_x * self.tile_size + self.tile_size / 2
        world_y = tile_y * self.tile_size + self.tile_size / 2
        self._blit_glyph(sprite_id, *camera.world_to_screen(world_x, world_y))

    def _blit_glyph(self, sprite_id, screen_x, screen_y):
        """Pega un glifo centrado en un punto de la pantalla."""
        glyph = self._glyph_surface(sprite_id)
        self.surface.blit(glyph, glyph.get_rect(center=(round(screen_x), round(screen_y))))
