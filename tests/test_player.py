"""Tests del movimiento del jugador y de su colisión con los muros."""

import math

import pytest

from game import config
from game.entities.player import Intent, Player, normalize
from game.world.level import Level

# Sala abierta de 8x6 tiles (256x192 px con tiles de 32).
OPEN_ROOM = "\n".join(
    [
        "########",
        "#......#",
        "#......#",
        "#......#",
        "#..@...#",
        "########",
    ]
)

DT = 1 / 60


def make_level(text=OPEN_ROOM):
    return Level.from_string(text)


def make_player(level, tile_x=None, tile_y=None):
    """Jugador en el inicio del mapa, o centrado en el tile que se indique."""
    if tile_x is None:
        return Player.at_level_start(level)
    return Player(*level.tile_center(tile_x, tile_y))


def distance_moved(player, start):
    return math.dist((player.x, player.y), start)


# --- Normalización --------------------------------------------------------


def test_normalize_returns_unit_vector():
    for vector in [(1, 0), (0, -1), (1, 1), (-1, 1), (3, 4)]:
        assert math.isclose(math.hypot(*normalize(*vector)), 1.0)


def test_normalize_of_zero_is_zero():
    assert normalize(0, 0) == (0.0, 0.0)


def test_diagonal_is_not_faster_than_straight():
    """Moverse en diagonal debe recorrer lo mismo que en línea recta."""
    level = make_level()

    straight = make_player(level)
    start = (straight.x, straight.y)
    straight.update(DT, Intent(direction=(1, 0)), level)
    straight_distance = distance_moved(straight, start)

    diagonal = make_player(level)
    start = (diagonal.x, diagonal.y)
    diagonal.update(DT, Intent(direction=(1, 1)), level)
    diagonal_distance = distance_moved(diagonal, start)

    assert math.isclose(diagonal_distance, straight_distance)
    # Y ese recorrido es exactamente velocidad * dt.
    assert math.isclose(straight_distance, config.PLAYER_SPEED * DT)


def test_movement_scales_with_dt():
    """El doble de tiempo, el doble de distancia: nada depende de los FPS."""
    level = make_level()

    slow = make_player(level)
    start = (slow.x, slow.y)
    slow.update(DT, Intent(direction=(1, 0)), level)
    short = distance_moved(slow, start)

    fast = make_player(level)
    start = (fast.x, fast.y)
    fast.update(DT * 2, Intent(direction=(1, 0)), level)

    assert math.isclose(distance_moved(fast, start), short * 2)


def test_no_input_does_not_move():
    level = make_level()
    player = make_player(level)
    before = (player.x, player.y)
    player.update(DT, Intent(direction=(0, 0)), level)
    assert (player.x, player.y) == before


# --- Colisión -------------------------------------------------------------


@pytest.mark.parametrize(
    "direction",
    [(1, 0), (-1, 0), (0, 1), (0, -1)],
    ids=["derecha", "izquierda", "abajo", "arriba"],
)
def test_player_cannot_walk_through_walls(direction):
    """Empujando contra un muro durante dos segundos, no lo atraviesa."""
    level = make_level()
    player = make_player(level)

    for _ in range(120):
        player.update(DT, Intent(direction=direction), level)

    # Sigue dentro de la sala, sin solaparse con ningún muro.
    assert player.left >= level.tile_size
    assert player.top >= level.tile_size
    assert player.right <= (level.width - 1) * level.tile_size
    assert player.bottom <= (level.height - 1) * level.tile_size


def test_player_stops_flush_against_the_wall():
    """Al chocar, queda pegado al muro: ni dentro ni a medio tile."""
    level = make_level()
    player = make_player(level)

    for _ in range(120):
        player.update(DT, Intent(direction=(1, 0)), level)

    # El muro derecho empieza en la columna 7.
    assert math.isclose(player.right, 7 * level.tile_size)


def test_player_slides_along_a_wall_when_pushing_diagonally():
    """En diagonal contra una pared, el eje libre sigue avanzando."""
    level = make_level()
    player = make_player(level)
    # Pegado al muro derecho antes de empezar.
    player.right = 7 * level.tile_size
    blocked_x, free_y_start = player.x, player.y

    for _ in range(30):
        player.update(DT, Intent(direction=(1, 1)), level)

    # El eje bloqueado no se mueve...
    assert math.isclose(player.x, blocked_x)
    # ...pero el libre sí: se ha deslizado hacia abajo.
    assert player.y > free_y_start


def test_sliding_is_not_blocked_by_the_corner_tile():
    """Deslizarse hacia una esquina frena en ella, no se cuela en diagonal."""
    level = make_level()
    player = make_player(level)
    player.right = 7 * level.tile_size

    for _ in range(120):
        player.update(DT, Intent(direction=(1, 1)), level)

    # Acaba encajado en la esquina inferior derecha de la sala.
    assert math.isclose(player.right, 7 * level.tile_size)
    assert math.isclose(player.bottom, 5 * level.tile_size)


def test_player_fits_through_a_one_tile_corridor():
    """La caja del jugador cabe por un pasillo de un tile de ancho."""
    corridor = "\n".join(
        [
            "#####",
            "###.#",
            "###.#",
            "#.@.#",  # el jugador arranca junto a la boca del pasillo
            "#####",
        ]
    )
    level = make_level(corridor)
    player = make_player(level)
    player.x, player.y = level.tile_center(3, 3)

    for _ in range(60):
        player.update(DT, Intent(direction=(0, -1)), level)

    # Ha subido por el pasillo hasta el fondo.
    assert math.isclose(player.top, level.tile_size)


# --- El jugador nace en el '@' -------------------------------------------


def test_player_spawns_centered_on_the_start_tile():
    level = make_level()
    player = make_player(level)
    assert (player.x, player.y) == level.tile_center(*level.player_start)
    assert player.sprite_id == "player"
