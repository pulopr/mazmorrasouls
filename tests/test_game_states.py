"""Tests de los estados del juego: muerte del jugador y reinicio del nivel.

Necesitan un `Game`, y con él pygame, así que se abre una ventana falsa
con el driver `dummy`.
"""

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import config                      # noqa: E402
from game.entities.player import Intent      # noqa: E402
from game.game import Game, GameState        # noqa: E402

DT = 1 / 60


@pytest.fixture
def game():
    game = Game()
    # Se neutraliza el teclado: en los tests no hay nadie pulsando nada.
    game.read_intent = lambda: Intent()
    yield game


def test_game_starts_playing(game):
    assert game.state is GameState.PLAYING
    assert game.player.is_alive
    assert game.enemies


def test_player_death_switches_to_the_death_screen(game):
    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.update(DT)
    assert game.state is GameState.DEAD
    assert game.death_timer > 0


def test_level_restarts_after_the_death_screen(game):
    # Se deja el mundo hecho un desastre: jugador muerto y un enemigo menos.
    game.enemies.pop()
    enemies_left = len(game.enemies)
    game.player.health.take_damage(config.PLAYER_HEALTH)
    game.player.stamina.spend(config.STAMINA_MAX)
    game.update(DT)

    # Mientras dura el cartel, no se reinicia nada.
    game.update(DT)
    assert game.state is GameState.DEAD
    assert len(game.enemies) == enemies_left

    # Pasada la cuenta atrás, el nivel vuelve a su estado inicial.
    for _ in range(int(config.DEATH_SCREEN_DURATION / DT) + 2):
        game.update(DT)

    assert game.state is GameState.PLAYING
    assert game.player.health.current == config.PLAYER_HEALTH
    assert game.player.stamina.current == config.STAMINA_MAX
    assert len(game.enemies) == enemies_left + 1
    assert (game.player.x, game.player.y) == game.level.tile_center(*game.level.player_start)


def test_respawning_puts_the_enemies_back_in_place(game):
    homes = sorted(enemy.home for enemy in game.enemies)
    for enemy in game.enemies:
        enemy.x += 200
        enemy.health.take_damage(10)

    game.respawn_enemies()

    assert sorted(enemy.home for enemy in game.enemies) == homes
    for enemy in game.enemies:
        assert (enemy.x, enemy.y) == enemy.home
        assert not enemy.is_hurt


def test_dead_enemies_are_removed(game):
    victim = game.enemies[0]
    victim.health.take_damage(victim.health.maximum)
    game.update(DT)
    assert victim not in game.enemies


def test_the_whole_frame_runs_without_errors(game):
    """Un par de segundos de juego real, dibujado incluido."""
    for _ in range(120):
        game.update(DT)
        game.draw()
    assert game.state is GameState.PLAYING


def test_debug_mode_draws_without_errors(game):
    game.debug = True
    for _ in range(30):
        game.update(DT)
        game.draw()
