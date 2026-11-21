"""Tests de la carga de niveles."""

import pytest

from game import config
from game.world.level import Level, LevelError

SMALL_LEVEL_PATH = config.LEVELS_DIR / "test.txt"

# Mapa mínimo escrito a mano para no depender de los archivos de `data/`.
SMALL_MAP = "\n".join(
    [
        "#####",
        "#@.s#",
        "#.B.#",
        "#####",
    ]
)


def test_dimensions():
    level = Level.from_string(SMALL_MAP)
    assert (level.width, level.height) == (5, 4)


def test_player_start_and_spawns():
    level = Level.from_string(SMALL_MAP)
    assert level.player_start == (1, 1)
    assert level.bonfires == [(2, 2)]
    # El mapa guarda el carácter; qué perfil le toca lo decide enemy.py.
    assert level.enemy_spawns == [(3, 1, "s")]


def test_entities_leave_floor_underneath():
    level = Level.from_string(SMALL_MAP)
    # Donde había '@', 'B' o 's' el tile es suelo y no bloquea.
    for x, y in [(1, 1), (2, 2), (3, 1)]:
        assert level.tile_sprite_at(x, y) == "floor"
        assert not level.is_solid(x, y)


def test_walls_and_out_of_bounds_are_solid():
    level = Level.from_string(SMALL_MAP)
    assert level.is_solid(0, 0)
    assert level.tile_sprite_at(0, 0) == "wall"
    # Fuera del mapa cuenta como muro, para que nada se escape.
    assert level.is_solid(-1, 1)
    assert level.is_solid(level.width, 1)
    assert level.is_solid(1, level.height)


def test_trailing_blank_lines_are_ignored():
    level = Level.from_string(SMALL_MAP + "\n\n")
    assert level.height == 4


@pytest.mark.parametrize(
    "text",
    [
        "####\n#@.#\n###\n",  # filas de ancho distinto
        "#####\n#...#\n#####\n",  # sin inicio de jugador
        "#####\n#@@.#\n#####\n",  # dos inicios de jugador
        "#####\n#@x.#\n#####\n",  # carácter desconocido
        "",  # mapa vacío
    ],
)
def test_malformed_maps_are_rejected(text):
    with pytest.raises(LevelError):
        Level.from_string(text)


# --- Los mapas de `data/levels` ------------------------------------------


def test_small_level_file_loads():
    # La sala pequeña es la que usan los tests, así que se nombra explícita:
    # no debe depender de cuál sea el nivel por defecto del juego.
    level = Level.load(SMALL_LEVEL_PATH)
    assert (level.width, level.height) == (20, 11)
    assert level.player_start == (9, 8)
    assert len(level.bonfires) == 1
    assert len(level.enemy_spawns) == 2
    # La sala está cerrada por muros en todo su perímetro.
    for x in range(level.width):
        assert level.is_solid(x, 0)
        assert level.is_solid(x, level.height - 1)
    for y in range(level.height):
        assert level.is_solid(0, y)
        assert level.is_solid(level.width - 1, y)


def test_big_level_is_larger_than_the_window():
    """El mapa grande existe para probar la cámara: debe desbordar la ventana."""
    level = Level.load(config.LEVELS_DIR / "test_big.txt")
    assert level.pixel_width > config.SCREEN_WIDTH
    assert level.pixel_height > config.SCREEN_HEIGHT
    assert len(level.enemy_spawns) >= 2
    # Sus bordes también son muro, para que no haya forma de salirse.
    for x in range(level.width):
        assert level.is_solid(x, 0) and level.is_solid(x, level.height - 1)
    for y in range(level.height):
        assert level.is_solid(0, y) and level.is_solid(level.width - 1, y)


def test_default_level_is_loadable():
    """Sea cual sea el nivel por defecto, el juego debe poder cargarlo."""
    level = Level.load(config.DEFAULT_LEVEL)
    assert level.player_start is not None


# --- El primer nivel de verdad -------------------------------------------


def test_nivel_01_is_valid():
    """El primer nivel carga, tiene un solo inicio y una sola hoguera."""
    level = Level.load(config.LEVELS_DIR / "nivel_01.txt")
    assert (level.width, level.height) == (64, 72)
    assert level.player_start is not None
    assert len(level.bonfires) == 1
    # Trae los tres tipos de enemigo y los objetos.
    chars = [char for _, _, char in level.enemy_spawns]
    assert chars.count("s") == 6
    assert chars.count("A") == 1
    assert chars.count("D") == 1
    assert len(level.items) == 5


def test_nivel_01_is_walled_in():
    level = Level.load(config.LEVELS_DIR / "nivel_01.txt")
    for x in range(level.width):
        assert level.is_solid(x, 0) and level.is_solid(x, level.height - 1)
    for y in range(level.height):
        assert level.is_solid(0, y) and level.is_solid(level.width - 1, y)


def test_nivel_01_floor_is_all_reachable_from_the_start():
    """Ningún rincón del nivel queda aislado del inicio del jugador."""
    level = Level.load(config.LEVELS_DIR / "nivel_01.txt")
    walkable = {
        (x, y)
        for y in range(level.height)
        for x in range(level.width)
        if not level.is_solid(x, y)
    }

    # Inundación desde el '@'.
    reached = {level.player_start}
    pending = [level.player_start]
    while pending:
        x, y = pending.pop()
        for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbour in walkable and neighbour not in reached:
                reached.add(neighbour)
                pending.append(neighbour)

    assert reached == walkable, f"{len(walkable - reached)} casillas inalcanzables"


def test_every_enemy_char_has_a_profile():
    """Todo carácter de enemigo del formato tiene su perfil."""
    from game.entities.enemy import PROFILES
    from game.world.level import ENEMY_CHARS

    assert set(ENEMY_CHARS) == set(PROFILES)


def test_entities_in_nivel_01_stand_on_floor():
    level = Level.load(config.LEVELS_DIR / "nivel_01.txt")
    places = [level.player_start, *level.bonfires, *level.items]
    places += [(x, y) for x, y, _ in level.enemy_spawns]
    for x, y in places:
        assert not level.is_solid(x, y)
