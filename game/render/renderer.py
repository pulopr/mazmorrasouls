"""Interfaz común de los renderers.

El juego habla siempre con esta interfaz, así que cambiar el ASCII por
sprites es cambiar la implementación, no el resto del código.
"""

from abc import ABC, abstractmethod


class Renderer(ABC):
    """Dibuja el estado del juego en pantalla."""

    @abstractmethod
    def begin_frame(self):
        """Prepara el fotograma (limpia la pantalla)."""

    @abstractmethod
    def draw_level(self, level, camera):
        """Dibuja el mapa y su decorado, visto desde `camera`."""

    @abstractmethod
    def draw_entity(self, entity, camera):
        """Dibuja una entidad, vista desde `camera`."""

    @abstractmethod
    def draw_attack(self, x, y, facing, camera):
        """Dibuja el efecto de un golpe en (x, y) del mundo, hacia `facing`."""

    @abstractmethod
    def draw_lock_marker(self, entity, camera):
        """Marca al enemigo fijado para que se distinga del resto."""

    @abstractmethod
    def draw_projectile(self, projectile, camera):
        """Dibuja un proyectil; su aspecto depende de hacia dónde vuela."""

    @abstractmethod
    def draw_world_bar(self, bar_id, x, y, width, height, ratio, camera):
        """Dibuja una barrita en coordenadas del mundo (sobre un enemigo)."""

    @abstractmethod
    def draw_box_outline(self, box, camera, box_id):
        """Dibuja el contorno de una caja del mundo. Solo para depurar."""

    @abstractmethod
    def draw_circle_outline(self, x, y, radius, camera):
        """Dibuja una circunferencia del mundo. Solo para depurar."""

    @abstractmethod
    def draw_debug_text(self, text, x, y, camera):
        """Escribe una etiqueta pequeña en un punto del mundo. Solo para depurar."""

    @abstractmethod
    def draw_debug_line(self, from_x, from_y, to_x, to_y, camera):
        """Traza una línea entre dos puntos del mundo. Solo para depurar."""

    @abstractmethod
    def draw_hud_text(self, text, x, y, align="left"):
        """Escribe texto de HUD anclado por su esquina izquierda o derecha."""

    @abstractmethod
    def draw_message(self, text):
        """Escribe un mensaje grande en el centro de la pantalla."""

    @abstractmethod
    def draw_bar(self, bar_id, x, y, width, height, ratio):
        """Dibuja una barra del HUD llena en `ratio` (de 0 a 1).

        El HUD decide qué barra y dónde; el color lo pone el renderer.
        """

    @abstractmethod
    def present(self):
        """Vuelca el fotograma terminado a la pantalla."""
