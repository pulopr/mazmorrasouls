"""Carga de niveles desde `data/levels/*.txt`.

Un nivel es una cuadrícula de tiles. Los caracteres que representan
entidades (`@`, `B`, `s`) no son tiles: marcan el punto donde nace algo y
el tile que queda debajo es suelo.

Este módulo es lógica pura: no dibuja nada. Además de cargar el mapa,
resuelve la colisión de las entidades contra los muros.
"""

import math
from pathlib import Path

from game import config

# Margen para que un borde que cae justo en la frontera entre dos tiles
# cuente como "todavía en el tile de antes" y no roce el de al lado.
EPSILON = 1e-9

# --- Caracteres del formato de mapa --------------------------------------

CHAR_WALL = "#"
CHAR_FLOOR = "."
CHAR_PLAYER_START = "@"
CHAR_BONFIRE = "B"
CHAR_SKELETON = "s"
CHAR_ARCHER = "A"
CHAR_ELITE = "D"
CHAR_ITEM = "*"
CHAR_DOOR = "+"

# Tiles que de verdad ocupan la cuadrícula, con su `sprite_id` asociado.
# El renderer traduce ese id a un glifo y un color (hoy) o a una imagen
# (más adelante); la lógica nunca decide el aspecto.
TILE_SPRITES = {
    CHAR_WALL: "wall",
    CHAR_FLOOR: "floor",
    CHAR_DOOR: "door",
}

# Caracteres que colocan un enemigo. El mapa guarda el carácter tal cual
# y es `entities/enemy.py` quien decide qué perfil le toca a cada uno.
ENEMY_CHARS = (CHAR_SKELETON, CHAR_ARCHER, CHAR_ELITE)

# Caracteres de entidad y el tile de suelo que dejan en su lugar.
ENTITY_CHARS = (CHAR_PLAYER_START, CHAR_BONFIRE, CHAR_ITEM, *ENEMY_CHARS)

# Tiles que bloquean el paso.
SOLID_TILES = (CHAR_WALL, CHAR_DOOR)


class LevelError(Exception):
    """El archivo de mapa no cumple el formato esperado."""


class Level:
    """Un mapa cargado: rejilla de tiles y puntos de aparición.

    Atributos:
        tiles: lista de filas; cada fila es una lista de caracteres de tile.
        width, height: dimensiones en tiles.
        player_start: coordenadas (x, y) en tiles del inicio del jugador.
        bonfires: lista de coordenadas (x, y) de hogueras.
        items: lista de coordenadas (x, y) de objetos (todavía decorado).
        enemy_spawns: lista de (x, y, carácter) de enemigos.
    """

    def __init__(
        self, tiles, player_start, bonfires, enemy_spawns, items=(), tile_size=config.TILE_SIZE
    ):
        self.tiles = tiles
        self.height = len(tiles)
        self.width = len(tiles[0]) if tiles else 0
        self.player_start = player_start
        self.bonfires = bonfires
        self.enemy_spawns = enemy_spawns
        self.items = list(items)
        self.tile_size = tile_size

    @property
    def pixel_width(self):
        """Ancho del mapa en píxeles del mundo."""
        return self.width * self.tile_size

    @property
    def pixel_height(self):
        """Alto del mapa en píxeles del mundo."""
        return self.height * self.tile_size

    # --- Carga ------------------------------------------------------------

    @classmethod
    def from_string(cls, text, tile_size=config.TILE_SIZE):
        """Construye un nivel a partir del contenido de un archivo de mapa."""
        # Se ignoran las líneas vacías del final para que un salto de línea
        # sobrante no cree una fila fantasma.
        rows = [line.rstrip("\n\r") for line in text.splitlines()]
        while rows and not rows[-1].strip():
            rows.pop()

        if not rows:
            raise LevelError("El mapa está vacío")

        widths = {len(row) for row in rows}
        if len(widths) != 1:
            raise LevelError(f"Todas las filas deben medir lo mismo; se encontraron anchos {sorted(widths)}")

        tiles = []
        player_start = None
        bonfires = []
        enemy_spawns = []
        items = []

        for y, row in enumerate(rows):
            tile_row = []
            for x, char in enumerate(row):
                if char == CHAR_PLAYER_START:
                    if player_start is not None:
                        raise LevelError("El mapa tiene más de un inicio de jugador '@'")
                    player_start = (x, y)
                elif char == CHAR_BONFIRE:
                    bonfires.append((x, y))
                elif char in ENEMY_CHARS:
                    enemy_spawns.append((x, y, char))
                elif char == CHAR_ITEM:
                    items.append((x, y))
                elif char not in TILE_SPRITES:
                    raise LevelError(f"Carácter desconocido {char!r} en ({x}, {y})")

                # Las entidades dejan suelo debajo.
                tile_row.append(CHAR_FLOOR if char in ENTITY_CHARS else char)
            tiles.append(tile_row)

        if player_start is None:
            raise LevelError("El mapa no tiene inicio de jugador '@'")

        return cls(tiles, player_start, bonfires, enemy_spawns, items, tile_size)

    @classmethod
    def load(cls, path, tile_size=config.TILE_SIZE):
        """Carga un nivel desde una ruta de archivo."""
        return cls.from_string(Path(path).read_text(encoding="utf-8"), tile_size)

    # --- Consultas --------------------------------------------------------

    def tile_at(self, x, y):
        """Carácter de tile en (x, y); muro si se sale del mapa."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return CHAR_WALL

    def tile_sprite_at(self, x, y):
        """`sprite_id` del tile en (x, y), para que lo traduzca el renderer."""
        return TILE_SPRITES[self.tile_at(x, y)]

    def is_solid(self, x, y):
        """¿Bloquea el paso el tile (x, y)? Fuera del mapa cuenta como muro."""
        return self.tile_at(x, y) in SOLID_TILES

    def tile_center(self, tile_x, tile_y):
        """Centro en píxeles del tile (tile_x, tile_y)."""
        return (
            tile_x * self.tile_size + self.tile_size / 2,
            tile_y * self.tile_size + self.tile_size / 2,
        )

    def has_line_of_sight(self, from_x, from_y, to_x, to_y):
        """¿Se ven dos puntos del mundo sin un muro de por medio?

        Trazado de rayo sencillo: se recorre el segmento a pasos de una
        fracción de tile (`SIGHT_RAY_STEP`) y se mira si alguno cae en un
        muro. Es aproximado —un paso podría saltarse una esquina muy
        justa— pero basta de sobra para decidir si un enemigo te ve, y es
        mucho más simple que un DDA.
        """
        distance = math.hypot(to_x - from_x, to_y - from_y)
        if distance == 0:
            return True

        step_length = self.tile_size * config.SIGHT_RAY_STEP
        steps = max(1, math.ceil(distance / step_length))
        for step in range(1, steps + 1):
            fraction = step / steps
            x = from_x + (to_x - from_x) * fraction
            y = from_y + (to_y - from_y) * fraction
            if self.is_solid(math.floor(x / self.tile_size), math.floor(y / self.tile_size)):
                return False
        return True

    # --- Colisión ---------------------------------------------------------

    def _overlapped_tiles(self, entity):
        """Rango de tiles (x0, x1, y0, y1) que solapa el AABB de la entidad."""
        return (
            math.floor(entity.left / self.tile_size),
            math.floor((entity.right - EPSILON) / self.tile_size),
            math.floor(entity.top / self.tile_size),
            math.floor((entity.bottom - EPSILON) / self.tile_size),
        )

    def move_with_collision(self, entity, dx, dy):
        """Mueve la entidad `dx`, `dy` píxeles sin dejarla entrar en un muro.

        Cada eje se resuelve por separado: primero se aplica el movimiento
        horizontal y se corrige, luego el vertical. Así, al empujar en
        diagonal contra una pared, el eje bloqueado se anula pero el otro
        sigue avanzando y la entidad **se desliza** a lo largo del muro en
        vez de quedarse clavada.

        El desplazamiento se trocea en pasos no mayores que un tile. Sin
        eso, un movimiento muy largo de un solo fotograma (un empujón
        fuerte, por ejemplo) aterrizaría al otro lado de la pared sin
        haber comprobado las casillas que cruza por el camino.

        Devuelve (chocó_en_x, chocó_en_y).
        """
        longest = max(abs(dx), abs(dy))
        steps = max(1, math.ceil(longest / self.tile_size))

        hit_x = hit_y = False
        for _ in range(steps):
            hit_x = self._move_axis_x(entity, dx / steps) or hit_x
            hit_y = self._move_axis_y(entity, dy / steps) or hit_y
        return hit_x, hit_y

    def _move_axis_x(self, entity, dx):
        """Aplica el movimiento horizontal y lo frena contra el muro."""
        if dx == 0:
            return False
        entity.x += dx

        x0, x1, y0, y1 = self._overlapped_tiles(entity)
        blocking = [
            tile_x
            for tile_x in range(x0, x1 + 1)
            for tile_y in range(y0, y1 + 1)
            if self.is_solid(tile_x, tile_y)
        ]
        if not blocking:
            return False

        if dx > 0:
            # Yendo a la derecha, para en la cara izquierda del muro más cercano.
            entity.right = min(blocking) * self.tile_size
        else:
            entity.left = (max(blocking) + 1) * self.tile_size
        return True

    def _move_axis_y(self, entity, dy):
        """Aplica el movimiento vertical y lo frena contra el muro."""
        if dy == 0:
            return False
        entity.y += dy

        x0, x1, y0, y1 = self._overlapped_tiles(entity)
        blocking = [
            tile_y
            for tile_x in range(x0, x1 + 1)
            for tile_y in range(y0, y1 + 1)
            if self.is_solid(tile_x, tile_y)
        ]
        if not blocking:
            return False

        if dy > 0:
            entity.bottom = min(blocking) * self.tile_size
        else:
            entity.top = (max(blocking) + 1) * self.tile_size
        return True
