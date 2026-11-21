"""Interfaz común de los renderers.

El juego habla siempre con esta interfaz, así que cambiar el ASCII por
sprites es cambiar la implementación, no el resto del código.
"""

from abc import ABC, abstractmethod


class Renderer(ABC):
    """Dibuja el estado del juego en pantalla."""

    @abstractmethod
    def draw_level(self, level):
        """Dibuja el mapa y las entidades estáticas del nivel."""

    @abstractmethod
    def present(self):
        """Vuelca el fotograma terminado a la pantalla."""
