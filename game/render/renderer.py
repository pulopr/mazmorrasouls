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
    def present(self):
        """Vuelca el fotograma terminado a la pantalla."""
