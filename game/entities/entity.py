"""Clase base de todo lo que ocupa un lugar en el mundo.

Las entidades se mueven con **posición continua** (píxeles en float) sobre
la rejilla de tiles del mapa, y colisionan como cajas alineadas a los ejes
(AABB). La posición es el **centro** de la caja.

Este módulo es lógica pura: no sabe nada de cómo se dibuja.
"""


class Entity:
    """Una caja con posición, tamaño y aspecto.

    Atributos:
        x, y: centro de la caja, en píxeles del mundo (float).
        width, height: tamaño de la caja de colisión, en píxeles.
        sprite_id: identificador de aspecto que traduce el renderer.
    """

    def __init__(self, x, y, width, height, sprite_id):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.sprite_id = sprite_id

    # --- Bordes de la caja -----------------------------------------------
    # Se exponen con setter para que la resolución de colisiones pueda
    # decir "pega tu lado derecho a esta pared" sin hacer cuentas a mano.

    @property
    def half_width(self):
        return self.width / 2

    @property
    def half_height(self):
        return self.height / 2

    @property
    def left(self):
        return self.x - self.half_width

    @left.setter
    def left(self, value):
        self.x = value + self.half_width

    @property
    def right(self):
        return self.x + self.half_width

    @right.setter
    def right(self, value):
        self.x = value - self.half_width

    @property
    def top(self):
        return self.y - self.half_height

    @top.setter
    def top(self, value):
        self.y = value + self.half_height

    @property
    def bottom(self):
        return self.y + self.half_height

    @bottom.setter
    def bottom(self, value):
        self.y = value - self.half_height

    def __repr__(self):
        return f"{type(self).__name__}(x={self.x:.1f}, y={self.y:.1f}, sprite_id={self.sprite_id!r})"
