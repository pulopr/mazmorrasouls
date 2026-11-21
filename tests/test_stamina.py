"""Tests del depósito de estamina."""

import math

import pytest

from game.systems.stats import Stamina

MAXIMUM = 100.0
REGEN_RATE = 50.0
REGEN_DELAY = 0.5


@pytest.fixture
def stamina():
    return Stamina(MAXIMUM, REGEN_RATE, REGEN_DELAY)


def test_starts_full(stamina):
    assert stamina.current == MAXIMUM
    assert stamina.ratio == 1.0
    assert stamina.has_any


def test_spending_subtracts(stamina):
    assert stamina.spend(30) is True
    assert stamina.current == 70.0
    assert stamina.ratio == 0.7


def test_spending_more_than_available_leaves_it_at_zero(stamina):
    """Se puede pagar con lo que quede: la barra se vacía, no se endeuda."""
    stamina.spend(90)
    assert stamina.spend(50) is True
    assert stamina.current == 0.0
    assert not stamina.has_any


def test_never_goes_negative(stamina):
    for _ in range(20):
        stamina.spend(25)
        assert stamina.current >= 0.0


def test_cannot_spend_when_empty(stamina):
    stamina.spend(MAXIMUM)
    assert stamina.spend(10) is False
    assert stamina.current == 0.0


def test_regeneration_waits_for_the_delay(stamina):
    stamina.spend(50)

    # Durante el respiro no sube ni un punto.
    elapsed = 0.0
    while elapsed < REGEN_DELAY - 1e-9:
        stamina.update(1 / 60)
        elapsed += 1 / 60
        if elapsed < REGEN_DELAY:
            assert stamina.current == 50.0

    # Pasado el respiro, sí.
    stamina.update(0.1)
    assert stamina.current > 50.0


def test_regeneration_rate(stamina):
    stamina.spend(50)
    stamina.update(REGEN_DELAY)   # agota justo el respiro
    stamina.update(1.0)           # un segundo de recuperación
    assert math.isclose(stamina.current, 50.0 + REGEN_RATE)


def test_delay_leftover_counts_as_regeneration(stamina):
    """Si el respiro se acaba a mitad de fotograma, el resto ya recupera."""
    stamina.spend(50)
    stamina.update(REGEN_DELAY + 0.2)
    assert math.isclose(stamina.current, 50.0 + REGEN_RATE * 0.2)


def test_spending_again_restarts_the_delay(stamina):
    stamina.spend(10)
    stamina.update(REGEN_DELAY - 0.1)
    stamina.spend(10)             # reinicia el respiro
    stamina.update(REGEN_DELAY - 0.1)
    assert stamina.current == 80.0


def test_does_not_regenerate_past_the_maximum(stamina):
    stamina.spend(5)
    stamina.update(REGEN_DELAY + 100)
    assert stamina.current == MAXIMUM


def test_refill_tops_it_up(stamina):
    stamina.spend(MAXIMUM)
    stamina.refill()
    assert stamina.current == MAXIMUM
    assert stamina.delay_left == 0.0
