"""Tests de hogueras, menús, subida de nivel y frascos de Estus."""

import math
import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import config                                      # noqa: E402
from game.entities.bonfire import Bonfire                    # noqa: E402
from game.entities.enemy import ELITE, SKELETON              # noqa: E402
from game.entities.player import Intent, Player, PlayerState  # noqa: E402
from game.game import Game, GameState                        # noqa: E402
from game.systems.stats import CharacterStats, EstusFlask, level_cost  # noqa: E402
from game.ui.menus import BonfireMenu                        # noqa: E402
from game.world.level import Level                           # noqa: E402

DT = 1 / 60


@pytest.fixture
def game():
    game = Game()
    game.read_intent = lambda: Intent()
    return game


@pytest.fixture
def level():
    rows = ["#" * 12] + ["#" + "." * 10 + "#"] * 5 + ["#" * 12]
    rows[1] = "#.@" + "." * 8 + "#"
    return Level.from_string("\n".join(rows))


@pytest.fixture
def player(level):
    return Player(*level.tile_center(3, 3))


def stand_at_bonfire(game):
    """Lleva al jugador junto a la primera hoguera y la devuelve."""
    bonfire = game.bonfires[0]
    game.player.x, game.player.y = bonfire.x, bonfire.y
    return bonfire


def press_interact(game):
    game.interact_requested = True
    game.update(DT)


# --- Encender la hoguera --------------------------------------------------


def test_bonfires_start_unlit(game):
    assert game.bonfires
    assert all(not bonfire.lit for bonfire in game.bonfires)
    assert all(bonfire.sprite_id == "bonfire" for bonfire in game.bonfires)


def test_lighting_a_bonfire_moves_the_respawn_point(game):
    bonfire = stand_at_bonfire(game)
    assert game.player.respawn_point != (bonfire.x, bonfire.y)

    press_interact(game)

    assert bonfire.lit
    assert game.player.respawn_point == (bonfire.x, bonfire.y)
    assert game.notice == config.BONFIRE_LIT_MESSAGE
    # Encenderla no sienta al jugador: eso es la segunda vez.
    assert game.state is GameState.PLAYING


def test_dying_sends_you_to_the_lit_bonfire(game):
    bonfire = stand_at_bonfire(game)
    press_interact(game)

    game.player.x += 300
    game.player.health.take_damage(game.player.health.maximum)
    game.update(DT)
    for _ in range(int(config.DEATH_SCREEN_DURATION / DT) + 2):
        game.update(DT)

    assert (game.player.x, game.player.y) == (bonfire.x, bonfire.y)


def test_interacting_far_from_a_bonfire_does_nothing(game):
    bonfire = game.bonfires[0]
    game.player.x = bonfire.x + config.BONFIRE_INTERACT_RADIUS + 40
    game.player.y = bonfire.y
    press_interact(game)
    assert not bonfire.lit


def test_a_lit_bonfire_flickers():
    bonfire = Bonfire(0, 0)
    bonfire.light()
    seen = set()
    for _ in range(int(config.BONFIRE_FLICKER_PERIOD * 2 / DT)):
        bonfire.update(DT)
        seen.add(bonfire.sprite_id)
    assert seen == {"bonfire_lit", "bonfire_lit_dim"}


# --- Descansar ------------------------------------------------------------


def test_resting_restores_everything(game):
    stand_at_bonfire(game)
    press_interact(game)                 # encender

    game.player.health.take_damage(50)
    game.player.stamina.spend(60)
    game.player.estus.drink()
    press_interact(game)                 # descansar

    assert game.state is GameState.BONFIRE_MENU
    assert game.player.health.current == game.player.health.maximum
    assert game.player.stamina.current == game.player.stamina.maximum
    assert game.player.estus.charges == game.player.estus.maximum


def test_resting_respawns_ordinary_enemies_but_not_elites(game):
    stand_at_bonfire(game)
    press_interact(game)

    skeleton = next(e for e in game.enemies if e.profile is SKELETON)
    elite = next(e for e in game.enemies if e.profile is ELITE)
    skeleton_index, elite_index = skeleton.spawn_index, elite.spawn_index
    for victim in (skeleton, elite):
        victim.health.take_damage(victim.health.maximum)
    game.update(DT)

    press_interact(game)                 # descansar

    assert any(e.spawn_index == skeleton_index for e in game.enemies)
    assert all(e.spawn_index != elite_index for e in game.enemies)


def test_cannot_rest_while_being_hunted(game):
    bonfire = stand_at_bonfire(game)
    press_interact(game)                 # encender

    # Un esqueleto va a por el jugador.
    hunter = game.enemies[0]
    hunter.x, hunter.y = game.player.x + 60, game.player.y
    game.update(DT)
    assert game.being_hunted

    game.player.x, game.player.y = bonfire.x, bonfire.y
    press_interact(game)

    assert game.state is GameState.PLAYING
    assert game.notice == config.BONFIRE_BUSY_MESSAGE


def test_resting_does_not_clear_the_bloodstain(game):
    game.player.souls.gain(200)
    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.update(DT)
    for _ in range(int(config.DEATH_SCREEN_DURATION / DT) + 2):
        game.update(DT)
    assert game.bloodstain is not None

    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)
    assert game.bloodstain is not None   # solo morir la destruye


# --- Menús ----------------------------------------------------------------


def test_bonfire_menu_navigates_and_leaves(game):
    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)
    assert isinstance(game.menu, BonfireMenu)
    assert game.menu.selected == BonfireMenu.LEVEL_UP

    game.handle_menu_key(config.KEY_MOVE_DOWN)
    assert game.menu.selected == BonfireMenu.LEAVE

    game.handle_menu_key(config.KEY_INTERACT)    # confirmar "Salir"
    assert game.state is GameState.PLAYING
    assert game.menu is None


def test_menu_opens_the_level_up_screen_and_comes_back(game):
    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)

    game.handle_menu_key(config.KEY_ATTACK_LIGHT)   # J también confirma
    assert game.state is GameState.LEVEL_UP

    game.handle_menu_key(config.KEY_PAUSE)          # Esc vuelve a la hoguera
    assert game.state is GameState.BONFIRE_MENU

    game.handle_menu_key(config.KEY_PAUSE)          # y de ahí, al juego
    assert game.state is GameState.PLAYING


def test_the_world_is_paused_while_a_menu_is_open(game):
    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)

    enemy = game.enemies[0]
    enemy.x, enemy.y = game.player.x + 80, game.player.y
    frozen = (enemy.x, enemy.y)
    for _ in range(60):
        game.update(DT)
    assert (enemy.x, enemy.y) == frozen


# --- Subida de nivel ------------------------------------------------------


def test_level_cost_grows():
    costs = [level_cost(level) for level in range(10)]
    assert all(later > earlier for earlier, later in zip(costs, costs[1:]))


def test_level_is_the_sum_of_points_spent():
    stats = CharacterStats()
    assert stats.level == 0
    stats.raise_stat("vigor")
    stats.raise_stat("strength")
    assert stats.level == 2


def test_cannot_level_up_without_enough_souls(player):
    assert player.souls.total == 0
    assert player.level_up("vigor") is False
    assert player.stats.level == 0
    assert player.stats.vigor == config.BASE_VIGOR


def test_levelling_up_spends_the_souls(player):
    cost = player.stats.next_level_cost
    player.souls.gain(cost + 10)
    assert player.level_up("vigor") is True
    assert player.souls.total == 10


def test_vigor_raises_max_and_current_health(player):
    player.souls.gain(10_000)
    player.health.take_damage(30)
    before_max = player.health.maximum
    before_current = player.health.current

    player.level_up("vigor")

    assert player.health.maximum == before_max + config.HEALTH_PER_VIGOR
    assert player.health.current == before_current + config.HEALTH_PER_VIGOR


def test_endurance_raises_stamina_and_its_regen(player):
    player.souls.gain(10_000)
    before_max = player.stamina.maximum
    before_regen = player.stamina.regen_rate

    player.level_up("endurance")

    assert player.stamina.maximum == before_max + config.STAMINA_PER_ENDURANCE
    assert player.stamina.regen_rate == before_regen + config.STAMINA_REGEN_PER_ENDURANCE


def test_strength_raises_the_attack_damage(player):
    player.souls.gain(10_000)
    before = player.attack_damage
    player.level_up("strength")
    assert player.attack_damage == before + config.DAMAGE_PER_STRENGTH


def test_each_level_costs_more_than_the_last(player):
    player.souls.gain(10_000)
    costs = []
    for _ in range(5):
        costs.append(player.stats.next_level_cost)
        assert player.level_up("vigor")
    assert all(later > earlier for earlier, later in zip(costs, costs[1:]))


def test_level_up_menu_previews_the_change(game):
    game.player.souls.gain(10_000)
    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)
    game.handle_menu_key(config.KEY_INTERACT)       # entrar en subir de nivel

    assert game.menu.preview_line() == "Vida 100 -> 112"
    game.handle_menu_key(config.KEY_INTERACT)       # subir Vigor
    assert game.player.stats.vigor == config.BASE_VIGOR + 1
    assert game.menu.preview_line() == "Vida 112 -> 124"


# --- Frascos de Estus -----------------------------------------------------


def test_flask_runs_out():
    flask = EstusFlask(2)
    assert flask.drink() and flask.drink()
    assert flask.drink() is False
    assert not flask.has_any


def test_drinking_heals_at_the_end_of_the_gulp(player, level):
    player.health.take_damage(60)
    wounded = player.health.current

    player.update(DT, Intent(drink=True), level)
    assert player.state is PlayerState.DRINKING
    assert player.estus.charges == config.ESTUS_CHARGES - 1

    # A media bebida todavía no ha curado nada.
    for _ in range(int(config.ESTUS_DRINK_DURATION / DT / 2)):
        player.update(DT, Intent(), level)
    assert player.health.current == wounded

    while player.is_drinking:
        player.update(DT, Intent(), level)

    expected = wounded + player.health.maximum * config.ESTUS_HEAL_FRACTION
    assert math.isclose(player.health.current, min(expected, player.health.maximum))


def test_cannot_attack_or_roll_while_drinking(player, level):
    player.update(DT, Intent(drink=True), level)
    while player.is_drinking:
        assert not player.can_attack
        assert not player.can_roll
        player.update(DT, Intent(attack=True, roll=True), level)
    assert player.state is PlayerState.NORMAL


def test_drinking_barely_moves_the_player(player, level):
    start_x = player.x
    player.update(DT, Intent(direction=(1, 0), drink=True), level)
    while player.is_drinking:
        player.update(DT, Intent(direction=(1, 0)), level)

    walked = config.PLAYER_SPEED * config.ESTUS_DRINK_DURATION
    assert 0 < player.x - start_x <= walked * config.ESTUS_MOVE_FACTOR + 1e-9


def test_being_hit_while_drinking_wastes_the_flask(player, level):
    player.health.take_damage(60)
    player.update(DT, Intent(drink=True), level)
    assert player.estus.charges == config.ESTUS_CHARGES - 1

    wounded = player.health.current
    player.take_hit(5, (1, 0), level)
    assert player.state is PlayerState.HURT

    for _ in range(120):
        player.update(DT, Intent(), level)

    # Ni cura ni devuelve el frasco.
    assert player.health.current == wounded - 5
    assert player.estus.charges == config.ESTUS_CHARGES - 1


def test_drinking_without_flasks_does_nothing(player, level):
    player.estus.charges = 0
    player.health.take_damage(60)
    wounded = player.health.current

    player.update(DT, Intent(drink=True), level)
    while player.is_drinking:
        player.update(DT, Intent(), level)

    assert player.health.current == wounded
    assert player.estus.charges == 0


def test_flasks_refill_on_rest_and_on_death(game):
    game.player.estus.charges = 0

    game.player.health.take_damage(game.player.health.maximum)
    game.update(DT)
    for _ in range(int(config.DEATH_SCREEN_DURATION / DT) + 2):
        game.update(DT)
    assert game.player.estus.charges == config.ESTUS_CHARGES

    game.player.estus.charges = 0
    stand_at_bonfire(game)
    press_interact(game)
    press_interact(game)
    assert game.player.estus.charges == config.ESTUS_CHARGES
