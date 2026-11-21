"""Tests del ataque del jugador, la hitbox y el daño a los enemigos."""

import math

import pytest

from game import config
from game.entities.enemy import Enemy
from game.entities.player import AttackPhase, Intent, Player, PlayerState
from game.systems import combat
from game.world.level import Level

DT = 1 / 60

# Sala de 20x8 tiles (640x256 px).
OPEN_ROOM = "\n".join(
    ["#" * 20]
    + ["#" + "." * 18 + "#"]
    + ["#.@" + "." * 16 + "#"]
    + ["#" + "." * 18 + "#" for _ in range(4)]
    + ["#" * 20]
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
def enemy(player):
    """Un esqueleto justo delante del jugador, al alcance del golpe."""
    return Enemy(player.x + 30, player.y)


def attack_until_done(player, level, enemies=(), direction=(0, 0)):
    """Lanza un ataque y lo lleva hasta el final. Devuelve los golpes dados."""
    hits = []
    player.update(DT, Intent(direction=direction, attack=True), level)
    while player.is_attacking:
        hits += combat.resolve_player_attack(player, list(enemies), level)
        player.update(DT, Intent(), level)
    return hits


# --- Geometría ------------------------------------------------------------


def test_boxes_overlap_only_when_they_really_touch():
    box = combat.Box(0, 0, 10, 10)
    assert box.overlaps(combat.Box(5, 5, 10, 10))
    assert not box.overlaps(combat.Box(20, 0, 10, 10))
    # Rozarse justo por el borde no cuenta como tocarse.
    assert not box.overlaps(combat.Box(10, 0, 10, 10))


@pytest.mark.parametrize(
    "facing, axis, sign",
    [((1, 0), "x", 1), ((-1, 0), "x", -1), ((0, 1), "y", 1), ((0, -1), "y", -1)],
    ids=["derecha", "izquierda", "abajo", "arriba"],
)
def test_hitbox_sits_in_front_of_the_attacker(facing, axis, sign):
    hitbox = combat.attack_hitbox(100, 100, facing, 12)
    center_x, center_y = hitbox.center
    offset = (center_x - 100) if axis == "x" else (center_y - 100)
    assert offset * sign > 0
    # Y en el otro eje queda centrada.
    other = (center_y - 100) if axis == "x" else (center_x - 100)
    assert math.isclose(other, 0.0)


def test_hitbox_is_wider_across_than_deep():
    """Mirando de lado abarca de arriba abajo, y al revés mirando al sur."""
    sideways = combat.attack_hitbox(100, 100, (1, 0), 12)
    assert sideways.width == config.ATTACK_REACH
    assert sideways.height == config.ATTACK_WIDTH

    downwards = combat.attack_hitbox(100, 100, (0, 1), 12)
    assert downwards.width == config.ATTACK_WIDTH
    assert downwards.height == config.ATTACK_REACH


# --- Fases del ataque -----------------------------------------------------


def test_attacking_costs_stamina(player, level):
    before = player.stamina.current
    player.update(DT, Intent(attack=True), level)
    assert player.state is PlayerState.ATTACKING
    assert player.stamina.current == before - config.ATTACK_STAMINA_COST


def test_can_attack_with_less_stamina_than_the_cost(player, level):
    player.stamina.current = config.ATTACK_STAMINA_COST / 3
    player.update(DT, Intent(attack=True), level)
    assert player.state is PlayerState.ATTACKING
    assert player.stamina.current == 0.0


def test_cannot_attack_with_zero_stamina(player, level):
    player.stamina.spend(config.STAMINA_MAX)
    player.update(DT, Intent(attack=True), level)
    assert player.state is not PlayerState.ATTACKING
    assert player.attack_hitbox() is None


def test_cannot_attack_while_rolling(player, level):
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    while player.is_rolling:
        player.update(DT, Intent(attack=True), level)
        assert not player.is_attacking
    # Terminado el rodar, el ataque vuelve a estar disponible.
    assert player.can_attack


def test_attack_goes_through_its_three_phases(player, level):
    phases = []
    player.update(DT, Intent(attack=True), level)
    while player.is_attacking:
        phases.append(player.attack_phase)
        player.update(DT, Intent(), level)

    assert phases[0] is AttackPhase.WINDUP
    assert AttackPhase.ACTIVE in phases
    assert phases[-1] is AttackPhase.RECOVERY
    # Y en ese orden, sin volver atrás.
    order = [AttackPhase.WINDUP, AttackPhase.ACTIVE, AttackPhase.RECOVERY]
    assert [p for i, p in enumerate(phases) if i == 0 or p is not phases[i - 1]] == order


def test_attack_lasts_its_configured_duration(player, level):
    frames = 1
    player.update(DT, Intent(attack=True), level)
    while player.is_attacking:
        player.update(DT, Intent(), level)
        frames += 1
    assert math.isclose(frames * DT, config.ATTACK_DURATION, abs_tol=DT)


def test_hitbox_exists_only_during_the_active_phase(player, level):
    player.update(DT, Intent(attack=True), level)
    while player.is_attacking:
        has_hitbox = player.attack_hitbox() is not None
        assert has_hitbox == (player.attack_phase is AttackPhase.ACTIVE)
        player.update(DT, Intent(), level)
    assert player.attack_hitbox() is None


def test_attacking_barely_moves_the_player(player, level):
    start_x = player.x
    attack_until_done(player, level, direction=(1, 0))
    walked = config.PLAYER_SPEED * config.ATTACK_DURATION
    assert 0 < player.x - start_x <= walked * config.ATTACK_MOVE_FACTOR + 1e-9


def test_attack_does_not_change_facing_midway(player, level):
    player.update(DT, Intent(direction=(1, 0), attack=True), level)
    while player.is_attacking:
        player.update(DT, Intent(direction=(0, -1)), level)
    assert player.facing == (1.0, 0.0)


# --- Rodar y atacar se estorban ------------------------------------------


def test_cannot_roll_before_the_recovery(player, level):
    player.update(DT, Intent(attack=True), level)
    while player.attack_phase is not AttackPhase.RECOVERY:
        assert not player.can_roll
        player.update(DT, Intent(roll=True), level)
        assert not player.is_rolling


def test_rolling_cancels_the_recovery(player, level):
    player.update(DT, Intent(attack=True), level)
    while player.attack_phase is not AttackPhase.RECOVERY:
        player.update(DT, Intent(), level)

    assert player.can_roll
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    assert player.is_rolling
    assert not player.is_attacking


# --- Daño -----------------------------------------------------------------


def test_attack_damages_an_enemy_in_front(player, level, enemy):
    hits = attack_until_done(player, level, [enemy])
    assert hits == [enemy]
    assert enemy.health.current == config.SKELETON_HEALTH - config.ATTACK_DAMAGE


def test_attack_misses_an_enemy_behind(player, level):
    behind = Enemy(player.x - 40, player.y)
    assert attack_until_done(player, level, [behind]) == []
    assert behind.health.current == config.SKELETON_HEALTH


def test_each_attack_hits_an_enemy_only_once(player, level, enemy):
    """La hitbox dura varios fotogramas, pero el tajo es uno solo."""
    hits = attack_until_done(player, level, [enemy])
    assert len(hits) == 1
    assert enemy.health.current == config.SKELETON_HEALTH - config.ATTACK_DAMAGE


def test_a_second_attack_hits_again(player, level, enemy):
    attack_until_done(player, level, [enemy])
    attack_until_done(player, level, [enemy])
    assert enemy.health.current == config.SKELETON_HEALTH - 2 * config.ATTACK_DAMAGE


def test_one_attack_can_hit_several_enemies(player, level):
    crowd = [Enemy(player.x + 30, player.y - 12), Enemy(player.x + 30, player.y + 12)]
    hits = attack_until_done(player, level, crowd)
    assert set(hits) == set(crowd)
    for enemy in crowd:
        assert enemy.health.current == config.SKELETON_HEALTH - config.ATTACK_DAMAGE


def test_enemy_dies_at_zero_health(player, level, enemy):
    needed = math.ceil(config.SKELETON_HEALTH / config.ATTACK_DAMAGE)
    for _ in range(needed):
        # Se le pega donde esté: el retroceso lo va alejando.
        player.x, player.y = enemy.x - 30, enemy.y
        player.stamina.refill()
        attack_until_done(player, level, [enemy])

    assert enemy.health.current == 0.0
    assert not enemy.is_alive


def test_dead_enemies_are_ignored_by_later_attacks(player, level, enemy):
    enemy.health.take_damage(config.SKELETON_HEALTH)
    assert attack_until_done(player, level, [enemy]) == []


# --- Retroceso y parpadeo -------------------------------------------------


def test_hit_enemy_is_pushed_back(player, level, enemy):
    before_x = enemy.x
    attack_until_done(player, level, [enemy])
    assert math.isclose(enemy.x - before_x, config.ATTACK_KNOCKBACK)


def test_knockback_does_not_push_through_walls(level):
    """Golpeando a un enemigo pegado al muro, no lo mete dentro."""
    player = Player.at_level_start(level)
    player.facing = (1.0, 0.0)
    wall_left = 19 * level.tile_size

    enemy = Enemy(0, player.y)
    enemy.right = wall_left          # pegado al muro derecho
    player.right = enemy.left - 2    # y el jugador justo detrás

    attack_until_done(player, level, [enemy])

    assert enemy.health.current < config.SKELETON_HEALTH   # sí le ha dado
    assert math.isclose(enemy.right, wall_left)            # pero no se ha movido
    assert not level.is_solid(int(enemy.x // level.tile_size), int(enemy.y // level.tile_size))


def test_hit_enemy_flashes_and_stops_flashing(player, level, enemy):
    attack_until_done(player, level, [enemy])
    assert enemy.hit_flash > 0
    assert enemy.sprite_id == "skeleton_hit"

    elapsed = 0.0
    while enemy.hit_flash > 0 and elapsed < 5:
        enemy.update(DT, level)
        elapsed += DT

    assert math.isclose(elapsed, config.ENEMY_HIT_FLASH, abs_tol=DT)
    assert enemy.sprite_id == "skeleton"


# --- Enemigos del mapa ----------------------------------------------------


def test_enemies_spawn_from_the_level(level):
    enemies = Enemy.spawn_from_level(level)
    assert len(enemies) == len(level.enemy_spawns)

    big = Level.load(config.LEVELS_DIR / "test_big.txt")
    spawned = Enemy.spawn_from_level(big)
    assert len(spawned) == len(big.enemy_spawns) == 6
    for enemy in spawned:
        assert enemy.is_alive
        assert not enemy.is_hurt
        assert enemy.health.current == config.SKELETON_HEALTH
        # Nacen centrados en su tile y fuera de los muros.
        assert not big.is_solid(int(enemy.x // big.tile_size), int(enemy.y // big.tile_size))


def test_enemies_collide_with_walls(level):
    """Empujar a un enemigo contra un muro no lo mete dentro."""
    enemy = Enemy(*level.tile_center(1, 2))
    combat.apply_knockback(enemy, (-1, 0), 500, level)
    assert math.isclose(enemy.left, level.tile_size)


def test_enemy_stays_still_without_ai(level):
    """En la Fase 3a los esqueletos son muñecos: no se mueven solos."""
    enemy = Enemy(*level.tile_center(5, 3))
    before = (enemy.x, enemy.y)
    for _ in range(120):
        enemy.update(DT, level)
    assert (enemy.x, enemy.y) == before
