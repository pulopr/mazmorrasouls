"""Tests del fijado de objetivo (lock-on)."""

import math

import pytest

from game import config
from game.entities.enemy import Enemy
from game.entities.player import Intent, Player
from game.systems import targeting
from game.systems.targeting import LockOn
from game.world.level import Level

DT = 1 / 60

# Sala muy ancha: 40x13 tiles (1280x416 px), cabe el radio de fijado.
OPEN_ROOM = "\n".join(
    ["#" * 40]
    + ["#" + "." * 38 + "#" for _ in range(5)]
    + ["#.@" + "." * 36 + "#"]
    + ["#" + "." * 38 + "#" for _ in range(5)]
    + ["#" * 40]
)

# Un muro vertical parte la sala en dos mitades.
SPLIT_ROOM = "\n".join(
    [
        "###############",
        "#.....#.......#",
        "#.@...#.......#",
        "#.....#.......#",
        "###############",
    ]
)


@pytest.fixture
def level():
    return Level.from_string(OPEN_ROOM)


@pytest.fixture
def player(level):
    player = Player.at_level_start(level)
    player.facing = (1.0, 0.0)
    return player


@pytest.fixture
def lock():
    return LockOn()


# --- A quién se fija ------------------------------------------------------


def test_locks_the_nearest_enemy_in_front(level, player, lock):
    near = Enemy(player.x + 80, player.y)
    far = Enemy(player.x + 240, player.y)

    assert lock.toggle(player, [far, near], level)
    assert lock.target is near


def test_prefers_an_enemy_in_front_over_one_behind(level, player, lock):
    """Mirando a la derecha, gana el de delante aunque esté algo más lejos."""
    front = Enemy(player.x + 140, player.y)
    behind = Enemy(player.x - 110, player.y)

    lock.acquire(player, [behind, front], level)
    assert lock.target is front


def test_a_much_closer_enemy_behind_still_wins(level, player, lock):
    """La preferencia es eso, una preferencia, no una regla absoluta."""
    front = Enemy(player.x + 300, player.y)
    behind = Enemy(player.x - 40, player.y)

    lock.acquire(player, [front, behind], level)
    assert lock.target is behind


def test_does_not_lock_beyond_the_radius(level, player, lock):
    far = Enemy(player.x + config.LOCK_ON_RADIUS + 50, player.y)
    assert not lock.toggle(player, [far], level)
    assert lock.target is None


def test_does_not_lock_without_line_of_sight():
    """Con un muro de por medio no se puede fijar, aunque esté cerca."""
    level = Level.from_string(SPLIT_ROOM)
    player = Player.at_level_start(level)
    hidden = Enemy(*level.tile_center(10, 2))
    lock = LockOn()

    assert targeting._distance(player, hidden) < config.LOCK_ON_RADIUS
    assert not lock.toggle(player, [hidden], level)
    assert lock.target is None


def test_does_not_lock_a_dead_enemy(level, player, lock):
    corpse = Enemy(player.x + 60, player.y)
    corpse.health.take_damage(corpse.health.maximum)
    assert not lock.toggle(player, [corpse], level)


def test_toggle_releases_an_existing_lock(level, player, lock):
    enemy = Enemy(player.x + 80, player.y)
    lock.toggle(player, [enemy], level)
    assert lock.is_locked

    lock.toggle(player, [enemy], level)
    assert not lock.is_locked
    assert lock.look_at() is None


# --- La mirada sigue al objetivo -----------------------------------------


def test_facing_follows_the_target(level, player, lock):
    enemy = Enemy(player.x, player.y - 120)      # justo encima
    lock.acquire(player, [enemy], level)
    assert lock.is_locked

    player.update(DT, Intent(look_at=lock.look_at()), level)
    assert player.facing == pytest.approx((0.0, -1.0))


def test_walking_does_not_turn_the_head_while_locked(level, player, lock):
    """WASD mueve alrededor del enemigo sin girar la mirada."""
    enemy = Enemy(player.x + 150, player.y)
    lock.acquire(player, [enemy], level)

    start_y = player.y
    for _ in range(20):
        player.update(DT, Intent(direction=(0, 1), look_at=lock.look_at()), level)

    assert player.y > start_y                     # se ha desplazado de lado
    assert player.facing[0] > 0.8                 # pero sigue encarando al enemigo


def test_rolling_goes_where_the_keys_point_but_keeps_the_lock(level, player, lock):
    enemy = Enemy(player.x + 150, player.y)
    lock.acquire(player, [enemy], level)

    start_x, start_y = player.x, player.y
    player.update(DT, Intent(direction=(0, 1), roll=True, look_at=lock.look_at()), level)
    while player.is_rolling:
        player.update(DT, Intent(look_at=lock.look_at()), level)

    # Ha rodado hacia abajo...
    assert player.y > start_y
    assert math.isclose(player.x, start_x, abs_tol=1.0)
    # ...sin dejar de mirar al enemigo.
    assert player.facing[0] > 0.5


def test_attack_hitbox_comes_out_towards_the_target(level, player, lock):
    enemy = Enemy(player.x, player.y + 150)       # justo debajo
    lock.acquire(player, [enemy], level)

    player.update(DT, Intent(attack=True, look_at=lock.look_at()), level)
    while player.attack_hitbox() is None:
        player.update(DT, Intent(look_at=lock.look_at()), level)

    center_x, center_y = player.attack_hitbox().center
    assert center_y > player.y                    # el golpe sale hacia abajo
    assert math.isclose(center_x, player.x, abs_tol=1.0)


def test_without_lock_the_head_follows_the_movement(level, player):
    """Sin fijado, todo sigue como antes."""
    player.update(DT, Intent(direction=(0, 1)), level)
    assert player.facing == (0.0, 1.0)


# --- Cambiar de objetivo --------------------------------------------------


def test_cycling_follows_the_angle_order(level, player, lock):
    """Los objetivos se recorren por ángulo, no por distancia."""
    above = Enemy(player.x + 100, player.y - 100)   # arriba a la derecha
    right = Enemy(player.x + 140, player.y)         # justo a la derecha
    below = Enemy(player.x + 100, player.y + 100)   # abajo a la derecha
    enemies = [right, above, below]

    # El ángulo crece en el sentido de las agujas del reloj en pantalla.
    assert targeting._angle_from(player, above) < targeting._angle_from(player, right)
    assert targeting._angle_from(player, right) < targeting._angle_from(player, below)

    lock.target = above
    lock.cycle(1, player, enemies, level)
    assert lock.target is right
    lock.cycle(1, player, enemies, level)
    assert lock.target is below

    lock.cycle(-1, player, enemies, level)
    assert lock.target is right
    lock.cycle(-1, player, enemies, level)
    assert lock.target is above


def test_cycling_wraps_around(level, player, lock):
    first = Enemy(player.x + 100, player.y - 100)
    last = Enemy(player.x + 100, player.y + 100)
    enemies = [first, last]

    lock.target = last
    lock.cycle(1, player, enemies, level)
    assert lock.target is first


def test_cycling_does_nothing_without_a_lock(level, player, lock):
    enemy = Enemy(player.x + 80, player.y)
    assert not lock.cycle(1, player, [enemy], level)
    assert lock.target is None


def test_cycling_skips_enemies_out_of_range(level, player, lock):
    close = Enemy(player.x + 80, player.y)
    far = Enemy(player.x + config.LOCK_ON_RADIUS + 100, player.y)

    lock.acquire(player, [close, far], level)
    lock.cycle(1, player, [close, far], level)
    assert lock.target is close      # el lejano no entra en la rotación


# --- Se suelta solo -------------------------------------------------------


def test_lock_breaks_when_the_target_gets_away(level, player, lock):
    enemy = Enemy(player.x + 100, player.y)
    lock.acquire(player, [enemy], level)

    enemy.x = player.x + config.LOCK_ON_BREAK_RADIUS + 10
    lock.update(DT, player, [enemy], level)
    assert not lock.is_locked


def test_lock_survives_a_brief_loss_of_sight():
    level = Level.from_string(SPLIT_ROOM)
    player = Player.at_level_start(level)
    visible = Enemy(*level.tile_center(4, 2))
    lock = LockOn()
    lock.acquire(player, [visible], level)

    # Se esconde tras el muro, pero poco rato.
    visible.x, visible.y = level.tile_center(10, 2)
    for _ in range(int((config.LOCK_ON_SIGHT_GRACE - 0.1) / DT)):
        lock.update(DT, player, [visible], level)
    assert lock.is_locked

    # Si tarda más de la cuenta, se suelta.
    for _ in range(int(0.3 / DT)):
        lock.update(DT, player, [visible], level)
    assert not lock.is_locked


def test_lock_jumps_to_the_next_enemy_when_the_target_dies(level, player, lock):
    victim = Enemy(player.x + 80, player.y)
    other = Enemy(player.x + 160, player.y)
    enemies = [victim, other]

    lock.acquire(player, enemies, level)
    assert lock.target is victim

    victim.health.take_damage(victim.health.maximum)
    lock.update(DT, player, enemies, level)
    assert lock.target is other


def test_lock_releases_when_the_last_enemy_dies(level, player, lock):
    only = Enemy(player.x + 80, player.y)
    lock.acquire(player, [only], level)

    only.health.take_damage(only.health.maximum)
    lock.update(DT, player, [only], level)
    assert not lock.is_locked


def test_lock_releases_when_the_target_leaves_the_list(level, player, lock):
    """Si el enemigo desaparece del mundo, no se queda apuntando al vacío."""
    enemy = Enemy(player.x + 80, player.y)
    lock.acquire(player, [enemy], level)

    lock.update(DT, player, [], level)
    assert not lock.is_locked


# --- Cámara ---------------------------------------------------------------


def test_camera_focus_is_the_player_without_a_target(player):
    assert targeting.camera_focus(player, None) == (player.x, player.y)


def test_camera_focus_leans_towards_the_target(level, player):
    enemy = Enemy(player.x + 200, player.y)
    focus_x, focus_y = targeting.camera_focus(player, enemy)

    assert focus_x == player.x + 200 * config.LOCK_ON_CAMERA_BIAS
    assert focus_y == player.y
    # Se desplaza, pero sin llegar al punto medio ni abandonar al jugador.
    assert player.x < focus_x < (player.x + enemy.x) / 2
