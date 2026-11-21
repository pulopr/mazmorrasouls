"""Tests de la cámara: sigue al jugador pero no se sale del mapa."""

import math

from game.render.camera import Camera
from game.world.level import Level

# Mapa de 40x30 tiles = 1280x960 px, más grande que esta vista de 320x240.
BIG_MAP = "\n".join(
    ["#" * 40]
    + ["#" + "." * 38 + "#" for _ in range(28)]
    + ["#" * 40]
)
VIEW_WIDTH, VIEW_HEIGHT = 320, 240


def make_level(text=BIG_MAP):
    # Todo mapa necesita un inicio de jugador, aunque a la cámara le dé igual.
    if "@" not in text:
        text = text.replace(".", "@", 1)
    return Level.from_string(text)


def make_camera():
    return Camera(VIEW_WIDTH, VIEW_HEIGHT)


def test_camera_centers_on_the_target_in_the_middle_of_the_map():
    level, camera = make_level(), make_camera()
    camera.follow(640, 480, level)
    assert (camera.x, camera.y) == (640 - VIEW_WIDTH / 2, 480 - VIEW_HEIGHT / 2)


def test_camera_stops_at_the_top_left_edge():
    """Cerca de la esquina, la vista no se asoma a coordenadas negativas."""
    level, camera = make_level(), make_camera()
    camera.follow(10, 10, level)
    assert (camera.x, camera.y) == (0, 0)


def test_camera_stops_at_the_bottom_right_edge():
    level, camera = make_level(), make_camera()
    camera.follow(level.pixel_width, level.pixel_height, level)
    assert camera.x == level.pixel_width - VIEW_WIDTH
    assert camera.y == level.pixel_height - VIEW_HEIGHT


def test_camera_never_shows_outside_the_map():
    """Recorriendo el mapa entero, la vista siempre queda dentro."""
    level, camera = make_level(), make_camera()
    for target_y in range(-200, level.pixel_height + 200, 37):
        for target_x in range(-200, level.pixel_width + 200, 37):
            camera.follow(target_x, target_y, level)
            assert 0 <= camera.x <= level.pixel_width - VIEW_WIDTH
            assert 0 <= camera.y <= level.pixel_height - VIEW_HEIGHT


def test_small_map_is_centered_instead_of_clamped():
    """Si el mapa cabe entero en la vista, se centra y no se mueve."""
    small = "\n".join(["#####", "#@..#", "#####"])  # 160x96 px
    level, camera = make_level(small), make_camera()
    camera.follow(80, 48, level)
    expected_x = (level.pixel_width - VIEW_WIDTH) / 2
    expected_y = (level.pixel_height - VIEW_HEIGHT) / 2
    assert (camera.x, camera.y) == (expected_x, expected_y)

    # Y mirar a otro punto no la mueve: no hay nada más que enseñar.
    camera.follow(0, 0, level)
    assert (camera.x, camera.y) == (expected_x, expected_y)


def test_world_to_screen_subtracts_the_camera():
    level, camera = make_level(), make_camera()
    camera.follow(640, 480, level)
    assert camera.world_to_screen(640, 480) == (VIEW_WIDTH / 2, VIEW_HEIGHT / 2)
    # Un punto justo en la esquina de la vista cae en el (0, 0) de pantalla.
    assert camera.world_to_screen(camera.x, camera.y) == (0, 0)


def test_camera_follows_the_player_smoothly():
    """Al avanzar el objetivo, la vista avanza con él sin saltos."""
    level, camera = make_level(), make_camera()
    camera.follow(640, 480, level)
    before = camera.x
    camera.follow(643, 480, level)
    assert math.isclose(camera.x - before, 3)
