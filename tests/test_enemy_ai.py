"""Tests de la IA del enemigo, del daño al jugador y del reinicio al morir."""

import math

import pytest

from game import config
from game.entities.enemy import Enemy, EnemyState
from game.entities.player import Intent, Player, PlayerState
from game.systems import combat
from game.world.level import Level

DT = 1 / 60

# Sala larga de 30x9 tiles (960x288 px): cabe el radio de detección entero.
OPEN_ROOM = "\n".join(
    ["#" * 30]
    + ["#" + "." * 28 + "#"]
    + ["#.@" + "." * 26 + "#"]
    + ["#" + "." * 28 + "#" for _ in range(5)]
    + ["#" * 30]
)

# Dos cuartos separados por un muro, comunicados por abajo.
WALLED_ROOM = "\n".join(
    [
        "##########",
        "#....#...#",
        "#.@..#...#",
        "#....#...#",
        "#........#",
        "##########",
    ]
)


@pytest.fixture
def level():
    return Level.from_string(OPEN_ROOM)


@pytest.fixture
def player(level):
    return Player.at_level_start(level)


def run(enemy, level, player, seconds):
    """Avanza la simulación del enemigo durante unos segundos."""
    for _ in range(int(seconds / DT)):
        enemy.update(DT, level, player)


def advance_to_state(enemy, level, player, state, limit=10.0):
    """Avanza hasta que el enemigo entra en `state`. Devuelve si llegó."""
    elapsed = 0.0
    while enemy.state is not state and elapsed < limit:
        enemy.update(DT, level, player)
        combat.resolve_enemy_attacks([enemy], player, level)
        elapsed += DT
    return enemy.state is state


# --- Detección ------------------------------------------------------------


def test_enemy_ignores_a_distant_player(level, player):
    enemy = Enemy(player.x + config.SKELETON_DETECT_RADIUS + 50, player.y)
    run(enemy, level, player, 0.5)
    assert enemy.state is EnemyState.IDLE


def test_enemy_chases_a_player_in_range(level, player):
    enemy = Enemy(player.x + config.SKELETON_DETECT_RADIUS - 20, player.y)
    start_x = enemy.x
    enemy.update(DT, level, player)
    assert enemy.state is EnemyState.CHASING
    run(enemy, level, player, 0.3)
    assert enemy.x < start_x   # se ha acercado


def test_enemy_does_not_see_through_walls():
    """Con un muro en medio no detecta, aunque esté a tiro de distancia."""
    level = Level.from_string(WALLED_ROOM)
    player = Player.at_level_start(level)           # cuarto izquierdo
    enemy = Enemy(*level.tile_center(7, 2))         # cuarto derecho

    assert enemy.distance_to(player) < config.SKELETON_DETECT_RADIUS
    assert not level.has_line_of_sight(enemy.x, enemy.y, player.x, player.y)

    run(enemy, level, player, 0.5)
    assert enemy.state is EnemyState.IDLE


def test_enemy_sees_the_player_through_open_ground():
    level = Level.from_string(WALLED_ROOM)
    player = Player.at_level_start(level)
    # Mismo cuarto, sin muro de por medio.
    enemy = Enemy(*level.tile_center(4, 2))
    assert level.has_line_of_sight(enemy.x, enemy.y, player.x, player.y)
    enemy.update(DT, level, player)
    assert enemy.state is EnemyState.CHASING


# --- Ciclo de ataque ------------------------------------------------------


def test_enemy_runs_through_every_attack_state(level, player):
    """Persigue, avisa, golpea, se recupera y vuelve a perseguir."""
    enemy = Enemy(player.x + 60, player.y)
    seen = []

    elapsed = 0.0
    while elapsed < 5.0:
        if not seen or enemy.state is not seen[-1]:
            seen.append(enemy.state)
        enemy.update(DT, level, player)
        combat.resolve_enemy_attacks([enemy], player, level)
        elapsed += DT

    for state in [
        EnemyState.CHASING,
        EnemyState.WINDUP,
        EnemyState.ATTACKING,
        EnemyState.RECOVERY,
    ]:
        assert state in seen, f"nunca pasó por {state}"
    # El orden de la primera vuelta es el esperado.
    first = [s for s in seen if s in (EnemyState.CHASING, EnemyState.WINDUP,
                                      EnemyState.ATTACKING, EnemyState.RECOVERY)][:4]
    assert first == [EnemyState.CHASING, EnemyState.WINDUP,
                     EnemyState.ATTACKING, EnemyState.RECOVERY]


def test_windup_is_long_enough_to_react(level, player):
    """El aviso dura lo configurado, que es lo que da tiempo a rodar."""
    enemy = Enemy(player.x + 40, player.y)
    assert advance_to_state(enemy, level, player, EnemyState.WINDUP)

    elapsed = 0.0
    while enemy.state is EnemyState.WINDUP:
        assert enemy.is_telegraphing
        assert enemy.sprite_id == "skeleton_windup"
        assert enemy.attack_hitbox() is None    # todavía no hace daño
        enemy.update(DT, level, player)
        elapsed += DT
    assert math.isclose(elapsed, config.SKELETON_WINDUP, abs_tol=2 * DT)


def test_hitbox_exists_only_while_attacking(level, player):
    enemy = Enemy(player.x + 40, player.y)
    assert advance_to_state(enemy, level, player, EnemyState.ATTACKING)
    assert enemy.attack_hitbox() is not None

    assert advance_to_state(enemy, level, player, EnemyState.RECOVERY)
    assert enemy.attack_hitbox() is None


def test_attack_direction_is_fixed_at_the_windup(level, player):
    """Moverse durante el aviso no hace que el golpe te siga."""
    enemy = Enemy(player.x + 40, player.y)
    assert advance_to_state(enemy, level, player, EnemyState.WINDUP)
    aimed_at = enemy.facing

    # El jugador se aparta mientras el enemigo prepara el golpe.
    while enemy.state is EnemyState.WINDUP:
        player.y += 3
        enemy.update(DT, level, player)

    assert enemy.facing == aimed_at


# --- Daño al jugador ------------------------------------------------------


def test_enemy_attack_damages_the_player(level, player):
    enemy = Enemy(player.x + 40, player.y)
    before = player.health.current
    assert advance_to_state(enemy, level, player, EnemyState.RECOVERY)
    assert player.health.current == before - config.SKELETON_DAMAGE
    assert player.state is PlayerState.HURT


def test_roll_iframes_avoid_the_damage(level, player):
    """Rodando en el momento justo, el golpe no entra."""
    enemy = Enemy(player.x + 40, player.y)
    assert advance_to_state(enemy, level, player, EnemyState.WINDUP)

    before = player.health.current
    while enemy.state is not EnemyState.RECOVERY:
        # Se rueda para estar en i-frames cuando llegue el golpe.
        if player.can_roll and not player.is_rolling:
            player.update(DT, Intent(direction=(0, 1), roll=True), level)
        else:
            player.update(DT, Intent(), level)
        enemy.update(DT, level, player)
        if enemy.attack_hitbox() is not None and player.is_roll_invulnerable:
            combat.resolve_enemy_attacks([enemy], player, level)

    assert player.health.current == before


def test_each_enemy_attack_hits_only_once(level, player):
    """La hitbox dura varios fotogramas pero el golpe es uno."""
    enemy = Enemy(player.x + 40, player.y)
    before = player.health.current
    assert advance_to_state(enemy, level, player, EnemyState.ATTACKING)

    # Se le quita la invulnerabilidad para que un segundo golpe sí entraría.
    while enemy.state is EnemyState.ATTACKING:
        player.invulnerable_timer = 0.0
        combat.resolve_enemy_attacks([enemy], player, level)
        enemy.update(DT, level, player)

    assert player.health.current == before - config.SKELETON_DAMAGE


def test_invulnerability_after_a_hit_blocks_a_second_one(level, player):
    """Dos enemigos golpeando a la vez solo pueden quitarte una vez."""
    first = Enemy(player.x + 40, player.y)
    second = Enemy(player.x - 40, player.y)
    before = player.health.current

    elapsed = 0.0
    while elapsed < 3.0:
        for enemy in (first, second):
            enemy.update(DT, level, player)
        combat.resolve_enemy_attacks([first, second], player, level)
        player.update(DT, Intent(), level)
        elapsed += DT
        if player.health.current < before:
            break

    assert player.health.current == before - config.SKELETON_DAMAGE
    assert player.is_invulnerable


def test_hurt_player_cannot_act(level, player):
    player.take_hit(10, (1, 0), level)
    assert player.state is PlayerState.HURT
    assert not player.can_roll
    assert not player.can_attack

    # Pasado el aturdimiento, vuelve a responder.
    for _ in range(int(config.PLAYER_HURT_STUN / DT) + 2):
        player.update(DT, Intent(), level)
    assert player.state is PlayerState.NORMAL
    assert player.can_attack


def test_hurt_player_is_knocked_back_and_blinks(level, player):
    before_x = player.x
    player.take_hit(10, (1, 0), level)
    assert math.isclose(player.x - before_x, config.PLAYER_HURT_KNOCKBACK)

    seen = set()
    for _ in range(int(config.PLAYER_HURT_INVULNERABILITY / DT)):
        player.update(DT, Intent(), level)
        seen.add(player.sprite_id)
    assert {"player", "player_hurt"} <= seen    # ha parpadeado


def test_take_hit_is_refused_while_invulnerable(level, player):
    assert player.take_hit(10, (1, 0), level) is True
    assert player.take_hit(10, (1, 0), level) is False
    assert player.health.current == config.PLAYER_HEALTH - 10


# --- Aturdimiento del enemigo --------------------------------------------


def test_hitting_an_enemy_cancels_its_windup(level, player):
    enemy = Enemy(player.x + 40, player.y)
    assert advance_to_state(enemy, level, player, EnemyState.WINDUP)

    enemy.take_hit(config.ATTACK_DAMAGE, (1, 0), level)
    assert enemy.state is EnemyState.STUNNED

    # Y al recomponerse no retoma el golpe: vuelve a perseguir.
    run(enemy, level, player, config.SKELETON_STUN + 0.05)
    assert enemy.state is EnemyState.CHASING


def test_an_enemy_that_cannot_be_stunned_keeps_its_windup(level, player):
    """Preparado para enemigos que no se interrumpen."""
    from dataclasses import replace
    from game.entities.enemy import SKELETON

    tough = Enemy(player.x + 40, player.y, replace(SKELETON, can_be_stunned=False))
    assert advance_to_state(tough, level, player, EnemyState.WINDUP)
    tough.take_hit(10, (1, 0), level)
    assert tough.state is EnemyState.WINDUP


# --- Volver a su sitio ----------------------------------------------------


def test_enemy_returns_home_when_the_player_escapes(level, player):
    # Nace lejos del jugador y lo persigue un rato, para separarse de casa.
    enemy = Enemy(player.x + config.SKELETON_DETECT_RADIUS - 10, player.y)
    home = enemy.home
    run(enemy, level, player, 0.8)
    assert enemy.state is EnemyState.CHASING
    assert math.hypot(enemy.x - home[0], enemy.y - home[1]) > 20

    # El jugador se marcha muy lejos.
    player.x, player.y = 10_000, 10_000
    run(enemy, level, player, 0.2)
    assert enemy.state is EnemyState.RETURNING

    run(enemy, level, player, 6.0)
    assert enemy.state is EnemyState.IDLE
    assert (enemy.x, enemy.y) == home


def test_enemy_gives_up_after_losing_sight_for_a_while():
    """Perder la vista un rato basta, aunque siga cerca."""
    level = Level.from_string(WALLED_ROOM)
    player = Player.at_level_start(level)
    enemy = Enemy(*level.tile_center(4, 2))
    enemy.update(DT, level, player)
    assert enemy.state is EnemyState.CHASING

    # El jugador se esconde tras el muro, sin alejarse.
    player.x, player.y = level.tile_center(7, 2)
    run(enemy, level, player, config.ENEMY_SIGHT_GRACE + 0.2)
    assert enemy.state in (EnemyState.RETURNING, EnemyState.IDLE)


# --- Nadie se solapa ------------------------------------------------------


def test_enemies_do_not_overlap_each_other(level, player):
    close = [Enemy(300, 100), Enemy(304, 100)]
    for _ in range(60):
        combat.separate_enemies(close, player, level)
    box_a, box_b = (combat.Box.from_entity(e) for e in close)
    assert not box_a.overlaps(box_b)


def test_enemies_do_not_overlap_the_player(level, player):
    enemy = Enemy(player.x + 4, player.y)
    for _ in range(60):
        combat.separate_enemies([enemy], player, level)
    assert not combat.Box.from_entity(enemy).overlaps(combat.Box.from_entity(player))


def test_separation_does_not_push_anyone_into_a_wall(level, player):
    """Apretujados contra el muro, nadie acaba dentro de él."""
    player.left = level.tile_size
    crowd = [Enemy(player.x + 2, player.y), Enemy(player.x + 6, player.y)]
    for _ in range(120):
        combat.separate_enemies(crowd, player, level)
    for entity in [player, *crowd]:
        assert entity.left >= level.tile_size - 1e-6
