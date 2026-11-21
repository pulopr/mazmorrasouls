"""Tests de las almas, la muerte del jugador y la mancha de sangre."""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import config                                  # noqa: E402
from game.entities.bloodstain import Bloodstain          # noqa: E402
from game.entities.enemy import ARCHER, ELITE, SKELETON, Enemy  # noqa: E402
from game.entities.player import Intent                  # noqa: E402
from game.game import Game, GameState                    # noqa: E402
from game.systems.stats import Souls                     # noqa: E402
from game.world.level import Level                       # noqa: E402

DT = 1 / 60


@pytest.fixture
def game():
    game = Game()
    game.read_intent = lambda: Intent()
    return game


def kill(game, enemy):
    """Mata a un enemigo y deja que el bucle lo recoja."""
    enemy.health.take_damage(enemy.health.maximum)
    game.update(DT)


def die(game):
    """Mata al jugador y espera a que pase el cartel de muerte."""
    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.update(DT)
    for _ in range(int(config.DEATH_SCREEN_DURATION / DT) + 2):
        game.update(DT)


def settle(souls, limit=2000):
    """Deja que el contador animado alcance su total."""
    for _ in range(limit):
        souls.update(DT)
        if souls.displayed == souls.total:
            return


# --- El contador ----------------------------------------------------------


def test_counter_animates_towards_the_total():
    souls = Souls()
    souls.gain(300)
    assert souls.total == 300
    assert souls.displayed == 0          # todavía no ha subido

    souls.update(DT)
    assert 0 < souls.displayed < 300     # va por el camino

    settle(souls)
    assert souls.displayed == 300


def test_counter_never_overshoots():
    souls = Souls()
    souls.gain(10)
    for _ in range(600):
        souls.update(DT)
        assert souls.displayed <= 10


def test_spending_needs_enough_souls():
    souls = Souls(100)
    assert souls.spend(150) is False
    assert souls.total == 100
    assert souls.spend(60) is True
    assert souls.total == 40


def test_take_all_empties_the_counter():
    souls = Souls(250)
    settle(souls)
    assert souls.take_all() == 250
    assert souls.total == 0
    assert souls.displayed == 0


# --- Ganar almas ----------------------------------------------------------


def test_each_enemy_type_gives_its_own_souls():
    assert SKELETON.souls == config.SKELETON_SOULS
    assert ARCHER.souls == config.ARCHER_SOULS
    assert ELITE.souls == config.ELITE_SOULS
    # Un esqueleto da menos que un arquero, y el élite mucho más.
    assert SKELETON.souls < ARCHER.souls < ELITE.souls


def test_killing_an_enemy_grants_its_souls(game):
    victim = next(e for e in game.enemies if e.profile is SKELETON)
    before = game.player.souls.total

    kill(game, victim)

    assert game.player.souls.total == before + config.SKELETON_SOULS
    assert victim not in game.enemies


def test_killing_an_elite_grants_many_more(game):
    elite = next(e for e in game.enemies if e.profile is ELITE)
    kill(game, elite)
    assert game.player.souls.total == config.ELITE_SOULS


# --- Morir ----------------------------------------------------------------


def test_death_shows_the_message_and_stops_the_action(game):
    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.update(DT)
    assert game.state is GameState.DEAD
    assert game.death_timer > 0

    # Mientras dura, el jugador no se mueve ni los enemigos actúan.
    frozen = (game.player.x, game.player.y)
    game.read_intent = lambda: Intent(direction=(1, 0))
    game.update(DT)
    assert (game.player.x, game.player.y) == frozen


def test_respawn_restores_health_and_stamina(game):
    game.player.stamina.spend(config.STAMINA_MAX)
    die(game)

    assert game.state is GameState.PLAYING
    assert game.player.health.current == config.PLAYER_HEALTH
    assert game.player.stamina.current == config.STAMINA_MAX


def test_respawn_puts_the_player_at_the_respawn_point(game):
    start = game.player.respawn_point
    game.player.x += 400
    die(game)
    assert (game.player.x, game.player.y) == start


def test_the_respawn_point_is_the_map_start(game):
    assert game.player.respawn_point == game.level.tile_center(*game.level.player_start)


# --- Quién reaparece ------------------------------------------------------


def test_ordinary_enemies_come_back(game):
    victim = next(e for e in game.enemies if e.profile is SKELETON)
    index = victim.spawn_index
    kill(game, victim)
    assert index not in [e.spawn_index for e in game.enemies]

    die(game)

    revived = [e for e in game.enemies if e.spawn_index == index]
    assert len(revived) == 1
    assert revived[0].health.current == config.SKELETON_HEALTH


def test_a_defeated_elite_does_not_come_back(game):
    elite = next(e for e in game.enemies if e.profile is ELITE)
    index = elite.spawn_index
    kill(game, elite)

    die(game)

    assert index in game.defeated_for_good
    assert all(e.spawn_index != index for e in game.enemies)
    # Y sigue sin volver tras más muertes.
    die(game)
    assert all(e.spawn_index != index for e in game.enemies)


def test_the_archer_comes_back(game):
    archer = next(e for e in game.enemies if e.profile is ARCHER)
    index = archer.spawn_index
    kill(game, archer)
    die(game)
    assert any(e.spawn_index == index for e in game.enemies)


# --- La mancha de sangre --------------------------------------------------


def test_dying_drops_the_souls_in_a_bloodstain(game):
    game.player.souls.gain(180)
    where = (game.player.x, game.player.y)

    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.update(DT)

    assert game.player.souls.total == 0
    assert game.bloodstain is not None
    assert game.bloodstain.souls == 180
    # Cae donde moriste.
    assert game.level.tile_of(*where) == game.level.tile_of(game.bloodstain.x, game.bloodstain.y)


def test_collecting_the_bloodstain_returns_the_souls(game):
    game.player.souls.gain(180)
    die(game)
    assert game.bloodstain is not None

    # Se va hasta la mancha y se pulsa E.
    game.player.x, game.player.y = game.bloodstain.x, game.bloodstain.y
    game.interact_requested = True
    game.update(DT)

    assert game.player.souls.total == 180
    assert game.bloodstain is None


def test_interacting_far_from_the_bloodstain_does_nothing(game):
    game.player.souls.gain(180)
    die(game)

    game.player.x = game.bloodstain.x + config.BLOODSTAIN_PICKUP_RADIUS + 30
    game.player.y = game.bloodstain.y
    game.interact_requested = True
    game.update(DT)

    assert game.player.souls.total == 0
    assert game.bloodstain is not None


def test_dying_again_destroys_the_previous_bloodstain(game):
    game.player.souls.gain(180)
    die(game)
    first = game.bloodstain
    assert first.souls == 180

    game.player.souls.gain(40)
    die(game)

    assert game.bloodstain is not first
    assert game.bloodstain.souls == 40
    # Las 180 de antes se han perdido para siempre.
    assert game.player.souls.total == 0


def test_dying_with_no_souls_leaves_no_bloodstain(game):
    assert game.player.souls.total == 0
    die(game)
    assert game.bloodstain is None


def test_dying_with_no_souls_still_destroys_the_old_bloodstain(game):
    game.player.souls.gain(180)
    die(game)
    assert game.bloodstain is not None

    # Segunda muerte sin llevar nada: la mancha anterior se pierde igual.
    die(game)
    assert game.bloodstain is None


def test_only_one_bloodstain_can_exist(game):
    for amount in (50, 70, 90):
        game.player.souls.gain(amount)
        die(game)
        assert game.bloodstain.souls == amount


# --- Dónde cae la mancha --------------------------------------------------


def test_bloodstain_moves_out_of_a_wall():
    """Morir dentro de un muro no esconde las almas dentro de él."""
    level = Level.from_string("######\n#....#\n#.@..#\n######")
    stain = Bloodstain.drop(level, *level.tile_center(0, 0), 100)
    tile = level.tile_of(stain.x, stain.y)
    assert not level.is_solid(*tile)


def test_bloodstain_moves_out_of_an_enemy():
    """Si caes encima de un enemigo, la mancha se aparta a un hueco libre."""
    level = Level.from_string("########\n#......#\n#.@....#\n########")
    squatter = Enemy(*level.tile_center(4, 2))

    stain = Bloodstain.drop(level, squatter.x, squatter.y, 100, blockers=[squatter])

    assert level.tile_of(stain.x, stain.y) != level.tile_of(squatter.x, squatter.y)
    assert not level.is_solid(*level.tile_of(stain.x, stain.y))


def test_bloodstain_stays_put_when_the_spot_is_fine():
    level = Level.from_string("########\n#......#\n#.@....#\n########")
    stain = Bloodstain.drop(level, *level.tile_center(4, 2), 100)
    assert level.tile_of(stain.x, stain.y) == (4, 2)


def test_bloodstain_blinks():
    stain = Bloodstain(0, 0, 100)
    seen = set()
    for _ in range(int(config.BLOODSTAIN_BLINK_PERIOD * 2 / DT)):
        stain.update(DT)
        seen.add(stain.sprite_id)
    assert seen == {"bloodstain", "bloodstain_dim"}
