"""Cámara: decide qué trozo del mundo se ve.

Guarda la esquina superior izquierda de la vista en coordenadas del mundo
y traduce de mundo a pantalla. Es solo aritmética — no dibuja ni importa
pygame —, pero vive en `render/` porque es parte de cómo se presenta el
juego, no de sus reglas.
"""


def _clamp(value, lowest, highest):
    """Encierra `value` en [lowest, highest]."""
    return max(lowest, min(value, highest))


class Camera:
    """Vista rectangular que sigue a un objetivo sin salirse del mapa."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0.0
        self.y = 0.0

    def follow(self, target_x, target_y, level):
        """Centra la vista en (target_x, target_y) sin asomarse fuera del mapa.

        Si el mapa es más pequeño que la ventana en algún eje, no hay nada
        que recortar: en ese eje el mapa se centra y se queda quieto.
        """
        self.x = self._axis(target_x, self.width, level.pixel_width)
        self.y = self._axis(target_y, self.height, level.pixel_height)

    @staticmethod
    def _axis(target, view_size, level_size):
        """Posición de la vista en un eje, ya limitada a los bordes del mapa."""
        centered = target - view_size / 2
        if level_size <= view_size:
            # El mapa cabe entero: se centra (el valor sale negativo o cero).
            return (level_size - view_size) / 2
        return _clamp(centered, 0.0, level_size - view_size)

    def world_to_screen(self, x, y):
        """Convierte un punto del mundo a coordenadas de pantalla."""
        return x - self.x, y - self.y
