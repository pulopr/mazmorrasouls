"""Tests de rodar y correr: estamina, i-frames, estados y colisión."""

import math

import pytest

from game import config
from game.entities.player import Intent, Player, PlayerState, roll_progress
from game.world.level import Level

DT = 1 / 60

# Sala amplia: 20x8 tiles (640x256 px), de sobra para un rodar entero.
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
    return Player.at_level_start(level)


def roll_to_completion(player, level, direction=(1, 0), max_frames=600):
    """Empieza un rodar y avanza hasta que termina. Devuelve los fotogramas."""
    player.update(DT, Intent(direction=direction, roll=True), level)
    frames = 1
    while player.is_rolling and frames < max_frames:
        player.update(DT, Intent(), level)
        frames += 1
    return frames


# --- Rodar y estamina -----------------------------------------------------


def test_rolling_costs_stamina(player, level):
    before = player.stamina.current
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    assert player.state is PlayerState.ROLLING
    assert player.stamina.current == before - config.ROLL_STAMINA_COST


def test_can_roll_with_less_stamina_than_the_cost(player, level):
    """Con un resto de estamina se rueda igual; la barra queda a 0."""
    player.stamina.current = config.ROLL_STAMINA_COST / 2
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    assert player.state is PlayerState.ROLLING
    assert player.stamina.current == 0.0


def test_cannot_roll_with_zero_stamina(player, level):
    # Se vacía gastando, como en el juego: así queda también el respiro
    # activo y la barra sigue a 0 durante los fotogramas siguientes.
    player.stamina.spend(config.STAMINA_MAX)
    assert player.stamina.current == 0.0
    start = (player.x, player.y)
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    assert player.state is not PlayerState.ROLLING
    # Pero caminar sí puede: solo se le niega la voltereta.
    assert player.x > start[0]


def test_stamina_is_never_negative_while_spamming_rolls(player, level):
    for _ in range(600):
        player.update(DT, Intent(direction=(1, 0), roll=True), level)
        assert player.stamina.current >= 0.0


def test_stamina_regenerates_after_rolling(player, level):
    roll_to_completion(player, level)
    emptied = player.stamina.current

    # Nada más terminar, sigue el respiro: no sube todavía.
    player.update(DT, Intent(), level)
    assert player.stamina.current == emptied

    for _ in range(int(config.STAMINA_REGEN_DELAY / DT) + 30):
        player.update(DT, Intent(), level)
    assert player.stamina.current > emptied


# --- Movimiento del rodar -------------------------------------------------


def test_roll_covers_its_configured_distance(player, level):
    start_x = player.x
    roll_to_completion(player, level, direction=(1, 0))
    assert math.isclose(player.x - start_x, config.ROLL_DISTANCE)


def test_roll_progress_runs_from_zero_to_one():
    assert roll_progress(0.0) == 0.0
    assert roll_progress(config.ROLL_DURATION) == 1.0
    # Pasarse de tiempo no lleva más allá del final.
    assert roll_progress(config.ROLL_DURATION * 10) == 1.0


def test_roll_progress_is_front_loaded():
    """Ease-out: a mitad de tiempo ya se ha recorrido más de media distancia."""
    assert roll_progress(config.ROLL_DURATION / 2) > 0.5


def test_roll_decelerates():
    """La velocidad del rodar baja de principio a fin, nunca sube."""
    steps = 40
    dt = config.ROLL_DURATION / steps
    speeds = [
        (roll_progress((i + 1) * dt) - roll_progress(i * dt)) / dt
        for i in range(steps)
    ]
    assert all(after <= before + 1e-9 for before, after in zip(speeds, speeds[1:]))
    assert speeds[0] > speeds[-1]


def test_roll_starts_clearly_faster_than_running(player, level):
    """El primer fotograma del rodar debe notarse frente a correr."""
    runner = Player.at_level_start(level)
    runner.update(DT, Intent(direction=(1, 0), run=True), level)
    run_step = runner.x - level.tile_center(*level.player_start)[0]

    start_x = player.x
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    roll_step = player.x - start_x

    assert roll_step > run_step * 2


def test_roll_average_speed_is_well_above_walking(player, level):
    """La media del rodar sale de la distancia y la duración configuradas."""
    average = config.ROLL_DISTANCE / config.ROLL_DURATION
    assert math.isclose(average, config.ROLL_AVERAGE_SPEED)
    assert average > config.RUN_SPEED > config.PLAYER_SPEED


def test_roll_distance_is_exact_whatever_the_frame_rate(level):
    """La distancia no depende del reparto de fotogramas."""
    for dt in [1 / 30, 1 / 60, 1 / 144, config.ROLL_DURATION, 1.0]:
        rolling = Player.at_level_start(level)
        start_x = rolling.x
        rolling.update(dt, Intent(direction=(1, 0), roll=True), level)
        while rolling.is_rolling:
            rolling.update(dt, Intent(), level)
        assert math.isclose(rolling.x - start_x, config.ROLL_DISTANCE, abs_tol=1e-9)


def test_iframes_stay_proportional_to_the_duration():
    """La ventana se define en fracciones, así que acompaña a la duración."""
    assert math.isclose(
        config.ROLL_IFRAME_START, config.ROLL_DURATION * config.ROLL_IFRAME_START_FRACTION
    )
    assert math.isclose(
        config.ROLL_IFRAME_END, config.ROLL_DURATION * config.ROLL_IFRAME_END_FRACTION
    )
    assert 0 < config.ROLL_IFRAME_START < config.ROLL_IFRAME_END < config.ROLL_DURATION


def test_running_is_one_and_a_half_times_walking():
    assert math.isclose(config.RUN_SPEED, config.PLAYER_SPEED * 1.5)


def test_roll_lasts_its_configured_duration(player, level):
    frames = roll_to_completion(player, level)
    assert math.isclose(frames * DT, config.ROLL_DURATION, abs_tol=DT)


def test_roll_direction_cannot_be_changed_midway(player, level):
    """Una vez lanzado, el rodar ignora las teclas hasta terminar."""
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    start_y = player.y
    while player.is_rolling:
        # Se insiste hacia abajo, pero el rodar iba hacia la derecha.
        player.update(DT, Intent(direction=(0, 1)), level)
    assert player.y == start_y


def test_cannot_roll_again_while_rolling(player, level):
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    after_first = player.stamina.current
    while player.is_rolling:
        player.update(DT, Intent(direction=(1, 0), roll=True), level)
    # No se ha cobrado un segundo rodar durante el primero.
    assert player.stamina.current == after_first


def test_roll_uses_the_facing_direction_when_no_key_is_pressed(player, level):
    # Primero camina hacia arriba para fijar la mirada.
    player.update(DT, Intent(direction=(0, -1)), level)
    assert player.facing == (0.0, -1.0)

    start_y = player.y
    roll_to_completion(player, level, direction=(0, 0))
    assert player.y < start_y


def test_facing_follows_the_last_movement(player, level):
    player.update(DT, Intent(direction=(-1, 0)), level)
    assert player.facing == (-1.0, 0.0)
    # Soltar las teclas no borra la mirada.
    player.update(DT, Intent(), level)
    assert player.facing == (-1.0, 0.0)


def test_rolling_does_not_go_through_walls(level):
    """Rodando contra un muro se para en él, no lo atraviesa."""
    player = Player.at_level_start(level)
    player.right = 19 * level.tile_size   # pegado al muro derecho
    wall = player.right

    roll_to_completion(player, level, direction=(1, 0))

    assert math.isclose(player.right, wall)
    assert not level.is_solid(*[int(v // level.tile_size) for v in (player.x, player.y)])


def test_rolling_into_a_wall_still_ends(level):
    """Aunque no avance, el rodar termina por tiempo y no deja colgado."""
    player = Player.at_level_start(level)
    player.right = 19 * level.tile_size
    frames = roll_to_completion(player, level, direction=(1, 0))
    assert player.state is PlayerState.NORMAL
    assert math.isclose(frames * DT, config.ROLL_DURATION, abs_tol=DT)


# --- Invulnerabilidad -----------------------------------------------------


def test_iframes_only_last_their_window(player, level):
    """La invulnerabilidad empieza y acaba dentro de la ventana configurada."""
    assert not player.is_invulnerable

    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    elapsed = DT
    invulnerable_times = []
    while player.is_rolling:
        if player.is_invulnerable:
            invulnerable_times.append(elapsed)
        player.update(DT, Intent(), level)
        elapsed += DT

    assert invulnerable_times, "debería haber i-frames en algún momento del rodar"
    assert min(invulnerable_times) >= config.ROLL_IFRAME_START
    assert max(invulnerable_times) < config.ROLL_IFRAME_END
    # Terminado el rodar, vuelve a ser vulnerable.
    assert not player.is_invulnerable


def test_not_invulnerable_while_walking_or_running(player, level):
    for intent in [Intent(direction=(1, 0)), Intent(direction=(1, 0), run=True), Intent()]:
        player.update(DT, intent, level)
        assert not player.is_invulnerable


def test_sprite_id_marks_the_roll_and_the_iframes(player, level):
    assert player.sprite_id == "player"

    seen = set()
    player.update(DT, Intent(direction=(1, 0), roll=True), level)
    while player.is_rolling:
        seen.add(player.sprite_id)
        player.update(DT, Intent(), level)

    assert seen == {"player_rolling", "player_invulnerable"}
    assert player.sprite_id == "player"


# --- Correr ---------------------------------------------------------------


def test_running_is_faster_than_walking(level):
    walker = Player.at_level_start(level)
    runner = Player.at_level_start(level)
    walker.update(DT, Intent(direction=(1, 0)), level)
    runner.update(DT, Intent(direction=(1, 0), run=True), level)

    assert runner.x > walker.x
    assert runner.state is PlayerState.RUNNING
    assert walker.state is PlayerState.NORMAL


def test_running_drains_stamina(player, level):
    before = player.stamina.current
    player.update(DT, Intent(direction=(1, 0), run=True), level)
    assert math.isclose(player.stamina.current, before - config.RUN_STAMINA_DRAIN * DT)


def test_running_in_place_does_not_drain(player, level):
    """Shift sin moverse no gasta nada."""
    before = player.stamina.current
    player.update(DT, Intent(run=True), level)
    assert player.stamina.current == before
    assert player.state is PlayerState.NORMAL


def test_running_stops_when_stamina_runs_out(level):
    """Al vaciarse la barra se sigue andando, a velocidad normal."""
    player = Player.at_level_start(level)
    intent = Intent(direction=(1, 0), run=True)
    # Se parte de un resto que da para dos fotogramas de carrera: correr
    # 100 puntos enteros daría para cruzar la sala varias veces.
    player.stamina.current = config.RUN_STAMINA_DRAIN * DT * 2

    frames = 0
    while player.stamina.has_any and frames < 10:
        assert player.state in (PlayerState.NORMAL, PlayerState.RUNNING)
        player.update(DT, intent, level)
        frames += 1

    assert player.stamina.current == 0.0

    # A partir de aquí, cada fotograma avanza lo que avanza caminando.
    before_x = player.x
    player.update(DT, intent, level)
    assert math.isclose(player.x - before_x, config.PLAYER_SPEED * DT)
    assert player.state is PlayerState.NORMAL


def test_stamina_recovers_after_running_and_lets_you_run_again(player, level):
    for _ in range(30):
        player.update(DT, Intent(direction=(1, 0), run=True), level)
    drained = player.stamina.current

    for _ in range(120):
        player.update(DT, Intent(), level)

    assert player.stamina.current > drained
    player.update(DT, Intent(direction=(-1, 0), run=True), level)
    assert player.state is PlayerState.RUNNING
