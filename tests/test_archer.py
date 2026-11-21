"""Tests del arquero y de las flechas."""

import math

import pytest

from game import config
from game.entities.archer import Archer
from game.entities.enemy import EnemyState
from game.entities.player import Intent, Player
from game.systems import projectiles
from game.systems.projectiles import Projectile
from game.world.level import Level

DT = 1 / 60

# Pasillo largo de 40x7 tiles (1280x224 px): cabe el alcance del arco.
CORRIDOR = "\n".join(
    ["#" * 40]
    + ["#" + "." * 38 + "#"]
    + ["#.@" + "." * 36 + "#"]
    + ["#" + "." * 38 + "#" for _ in range(3)]
    + ["#" * 40]
)

# Muro de por medio, para probar la línea de visión.
BLOCKED = "\n".join(
    [
        "##############",
        "#.@...##.....#",
        "#.....##.....#",
        "##############",
    ]
)


@pytest.fixture
def level():
    return Level.from_string(CORRIDOR)


@pytest.fixture
def player(level):
    return Player.at_level_start(level)


def run(archer, level, player, seconds, collect=None):
    """Avanza el arquero; si se le pasa una lista, recoge sus flechas."""
    for _ in range(int(seconds / DT)):
        archer.update(DT, level, player)
        if collect is not None:
            collect.extend(projectiles.collect_pending([archer]))


def fire_once(archer, level, player, limit=6.0):
    """Deja al arquero disparar y devuelve la primera flecha."""
    shots = []
    elapsed = 0.0
    while not shots and elapsed < limit:
        archer.update(DT, level, player)
        shots.extend(projectiles.collect_pending([archer]))
        elapsed += DT
    return shots[0] if shots else None


# --- La flecha ------------------------------------------------------------


def test_arrow_flies_straight(level, player):
    arrow = Projectile(100, 100, (1, 0), config.ARROW_SPEED, 10, owner=None)
    arrow.advance(0.1, level)
    assert math.isclose(arrow.x, 100 + config.ARROW_SPEED * 0.1)
    assert arrow.y == 100
    assert arrow.alive


def test_arrow_is_destroyed_by_a_wall(level, player):
    """Volando contra el muro del fondo, desaparece."""
    arrow = Projectile(100, 100, (-1, 0), config.ARROW_SPEED, 10, owner=None)
    for _ in range(600):
        arrow.advance(DT, level)
        if not arrow.alive:
            break
    assert not arrow.alive


def test_a_very_fast_arrow_does_not_cross_a_thin_wall(level):
    """El vuelo se trocea, así que no se cuela aunque sea rapidísima."""
    arrow = Projectile(100, 100, (-1, 0), 20_000, 10, owner=None)
    arrow.advance(DT, level)
    assert not arrow.alive


def test_arrow_damages_the_player(level, player):
    arrow = Projectile(player.x, player.y, (1, 0), config.ARROW_SPEED, config.ARROW_DAMAGE, None)
    alive = projectiles.update_projectiles([arrow], DT, level, [player])
    assert player.health.current == config.PLAYER_HEALTH - config.ARROW_DAMAGE
    assert alive == []   # la flecha se consume al acertar


def test_arrow_hits_only_once(level, player):
    """Al impactar desaparece, así que no puede volver a golpear."""
    arrow = Projectile(player.x, player.y, (1, 0), 1.0, config.ARROW_DAMAGE, None)
    remaining = [arrow]
    for _ in range(30):
        player.invulnerable_timer = 0.0    # para que un segundo golpe sí entraría
        remaining = projectiles.update_projectiles(remaining, DT, level, [player])
    assert player.health.current == config.PLAYER_HEALTH - config.ARROW_DAMAGE


def test_rolling_dodges_an_arrow(level, player):
    """Con los i-frames del rodar, la flecha pasa de largo."""
    player.update(DT, Intent(direction=(0, 1), roll=True), level)
    while not player.is_roll_invulnerable:
        player.update(DT, Intent(), level)

    arrow = Projectile(player.x, player.y, (1, 0), 1.0, config.ARROW_DAMAGE, None)
    remaining = projectiles.update_projectiles([arrow], DT, level, [player])

    assert player.health.current == config.PLAYER_HEALTH
    assert remaining == [arrow]   # no se la come: la esquiva


def test_post_hit_invulnerability_also_stops_arrows(level, player):
    player.take_hit(5, (1, 0), level)
    before = player.health.current

    arrow = Projectile(player.x, player.y, (1, 0), 1.0, config.ARROW_DAMAGE, None)
    projectiles.update_projectiles([arrow], DT, level, [player])
    assert player.health.current == before


def test_an_arrow_does_not_hit_its_owner(level, player):
    archer = Archer(player.x + 200, player.y)
    arrow = Projectile(archer.x, archer.y, (1, 0), 1.0, 10, owner=archer)
    projectiles.update_projectiles([arrow], DT, level, [archer])
    assert archer.health.current == config.ARCHER_HEALTH


# --- Comportamiento del arquero ------------------------------------------


def test_archer_shoots_at_a_distant_player(level, player):
    archer = Archer(player.x + config.ARCHER_SHOOT_RANGE - 40, player.y)
    arrow = fire_once(archer, level, player)
    assert arrow is not None
    # Sale hacia el jugador, que está a su izquierda.
    assert arrow.direction[0] < 0
    assert archer.state is EnemyState.RECOVERY


def test_archer_telegraphs_before_shooting(level, player):
    """Tensa el arco un rato, y el aviso es más largo que el del esqueleto."""
    archer = Archer(player.x + 200, player.y)
    elapsed = 0.0
    while archer.state is not EnemyState.WINDUP and elapsed < 5:
        archer.update(DT, level, player)
        elapsed += DT
    assert archer.is_aiming
    assert archer.sprite_id == "archer_windup"

    aiming = 0.0
    while archer.state is EnemyState.WINDUP:
        archer.update(DT, level, player)
        aiming += DT
    assert math.isclose(aiming, config.ARCHER_AIM_WINDUP, abs_tol=2 * DT)
    assert config.ARCHER_AIM_WINDUP > config.SKELETON_WINDUP


def test_archer_does_not_correct_its_aim(level, player):
    """Dispara adonde apuntabas al empezar a tensar, no adonde estás."""
    archer = Archer(player.x + 200, player.y)
    while not archer.is_aiming:
        archer.update(DT, level, player)
    aimed_at = archer.facing

    while archer.state is EnemyState.WINDUP:
        player.y += 4          # el jugador se aparta
        archer.update(DT, level, player)

    shots = projectiles.collect_pending([archer])
    assert shots and shots[0].direction == aimed_at


def test_archer_does_not_shoot_without_line_of_sight():
    """Con un muro de por medio ni siquiera te detecta."""
    level = Level.from_string(BLOCKED)
    player = Player.at_level_start(level)
    archer = Archer(*level.tile_center(10, 1))

    assert archer.distance_to(player) < config.ARCHER_DETECT_RADIUS
    assert not level.has_line_of_sight(archer.x, archer.y, player.x, player.y)

    shots = []
    run(archer, level, player, 3.0, collect=shots)
    assert shots == []
    assert archer.state is EnemyState.IDLE


def test_archer_backs_away_when_the_player_gets_close(level, player):
    """Si te le pegas, retrocede en vez de quedarse plantado."""
    archer = Archer(player.x + config.ARCHER_MIN_DISTANCE - 30, player.y)
    archer.update(DT, level, player)
    assert archer.state is EnemyState.CHASING

    start_x = archer.x
    run(archer, level, player, 0.3)
    assert archer.x > start_x                      # se ha alejado
    assert archer.facing[0] < 0                    # pero sigue encarado


def test_archer_approaches_a_player_out_of_range(level, player):
    archer = Archer(player.x + config.ARCHER_DETECT_RADIUS - 10, player.y)
    start_x = archer.x
    run(archer, level, player, 0.4)
    assert archer.x < start_x


def test_cornered_archer_falls_back_to_melee(level, player):
    """Pegado del todo, usa su golpe cuerpo a cuerpo flojo."""
    archer = Archer(player.x + config.ARCHER_ATTACK_RANGE - 6, player.y)
    elapsed = 0.0
    while archer.state is not EnemyState.ATTACKING and elapsed < 5:
        archer.update(DT, level, player)
        elapsed += DT

    assert archer.state is EnemyState.ATTACKING
    assert not archer.is_aiming_shot
    assert archer.attack_hitbox() is not None      # es un tajo, no una flecha
    assert projectiles.collect_pending([archer]) == []


def test_archer_respects_its_cooldown(level, player):
    """Entre flecha y flecha pasa al menos el tiempo configurado."""
    archer = Archer(player.x + 200, player.y)
    first = fire_once(archer, level, player)
    assert first is not None

    elapsed = 0.0
    second = None
    while second is None and elapsed < 6:
        archer.update(DT, level, player)
        shots = projectiles.collect_pending([archer])
        second = shots[0] if shots else None
        elapsed += DT

    assert second is not None
    minimum = config.ARCHER_SHOT_COOLDOWN
    assert elapsed >= minimum, f"disparó a los {elapsed:.2f}s, mínimo {minimum}s"


def test_hitting_an_aiming_archer_cancels_the_shot(level, player):
    archer = Archer(player.x + 200, player.y)
    while not archer.is_aiming:
        archer.update(DT, level, player)

    archer.take_hit(config.ATTACK_DAMAGE, (1, 0), level)
    assert archer.state is EnemyState.STUNNED
    assert not archer.is_aiming_shot
    assert projectiles.collect_pending([archer]) == []


def test_archer_dies_in_two_light_hits(level, player):
    archer = Archer(player.x + 200, player.y)
    archer.take_hit(config.ATTACK_DAMAGE, (1, 0), level)
    assert archer.is_alive
    archer.take_hit(config.ATTACK_DAMAGE, (1, 0), level)
    assert not archer.is_alive


def test_arrow_is_slow_enough_to_dodge():
    """Rodando de lado da tiempo a salir de la trayectoria."""
    # Lo que tarda la flecha en recorrer una distancia típica de combate.
    flight = config.ARCHER_SHOOT_RANGE / config.ARROW_SPEED
    assert flight > config.ROLL_DURATION
    # Y el rodar aparta más que el ancho de jugador y flecha juntos.
    assert config.ROLL_DISTANCE > config.PLAYER_WIDTH + config.ARROW_WIDTH
