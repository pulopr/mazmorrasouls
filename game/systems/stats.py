"""Estadísticas del jugador.

De momento solo vive aquí la estamina. El coste de subir de nivel y el
resto de atributos (vigor, resistencia, fuerza) llegarán en la Fase 5.

Lógica pura: sin pygame y sin dibujar.
"""

import math

from game import config


class Stamina:
    """Depósito de estamina que se gasta de golpe y se recupera solo.

    Como en Dark Souls, la recuperación no es inmediata: tras gastar hay
    un respiro (`regen_delay`) durante el cual la barra no sube. Cualquier
    gasto nuevo reinicia ese respiro.
    """

    def __init__(self, maximum, regen_rate, regen_delay):
        self.maximum = float(maximum)
        self.current = float(maximum)
        self.regen_rate = regen_rate
        self.regen_delay = regen_delay
        # Segundos que faltan para que vuelva a recuperarse.
        self.delay_left = 0.0

    @property
    def ratio(self):
        """Fracción llena, de 0 a 1 (lo que necesita la barra del HUD)."""
        if self.maximum <= 0:
            return 0.0
        return self.current / self.maximum

    @property
    def has_any(self):
        """¿Queda algo? Basta un resto para poder lanzar una acción."""
        return self.current > 0

    def spend(self, amount):
        """Gasta estamina y reinicia el respiro de recuperación.

        Se puede pagar con lo que haya: si el coste es mayor que lo que
        queda, la barra se queda en 0, nunca en negativo. Devuelve False
        —sin gastar nada— si el depósito ya estaba vacío.
        """
        if not self.has_any:
            return False
        self.current = max(0.0, self.current - amount)
        self.delay_left = self.regen_delay
        return True

    def update(self, dt):
        """Avanza el respiro y, cuando se acaba, recupera estamina."""
        if self.delay_left > 0:
            if dt <= self.delay_left:
                self.delay_left -= dt
                return
            # El respiro se agota a mitad del fotograma: el tiempo que
            # sobra ya cuenta como recuperación, para no perder fracciones.
            dt -= self.delay_left
            self.delay_left = 0.0
        self.current = min(self.maximum, self.current + self.regen_rate * dt)

    def refill(self):
        """Deja el depósito lleno (descansar en una hoguera, Fase 5)."""
        self.current = self.maximum
        self.delay_left = 0.0


class Health:
    """Puntos de vida de una criatura.

    Más simple que la estamina: aquí no hay recuperación automática —la
    vida se recobra con los frascos de Estus o descansando en una hoguera,
    y eso llega en la Fase 5—.
    """

    def __init__(self, maximum):
        self.maximum = float(maximum)
        self.current = float(maximum)

    @property
    def ratio(self):
        """Fracción de vida restante, de 0 a 1."""
        if self.maximum <= 0:
            return 0.0
        return self.current / self.maximum

    @property
    def is_alive(self):
        return self.current > 0

    def take_damage(self, amount):
        """Resta daño sin bajar de 0. Devuelve el daño aplicado de verdad."""
        dealt = min(self.current, max(0.0, amount))
        self.current -= dealt
        return dealt

    def heal(self, amount):
        """Cura sin pasar del máximo. Devuelve lo que se ha curado."""
        healed = min(self.maximum - self.current, max(0.0, amount))
        self.current += healed
        return healed


class Souls:
    """Las almas del jugador: moneda y experiencia a la vez.

    Guarda dos números: `total`, que es el real, y `shown`, que lo
    persigue poco a poco. La HUD enseña el segundo, así que al matar algo
    el contador sube rodando en vez de saltar de golpe.
    """

    def __init__(self, amount=0):
        self.total = int(amount)
        self.shown = float(amount)

    @property
    def displayed(self):
        """Lo que debe escribir la HUD ahora mismo."""
        return int(round(self.shown))

    def gain(self, amount):
        """Suma almas. El contador las alcanzará en unos fotogramas."""
        self.total += int(amount)

    def spend(self, amount):
        """Gasta almas si llegan. Devuelve si se ha podido (Fase 5)."""
        if amount > self.total:
            return False
        self.total -= int(amount)
        return True

    def take_all(self):
        """Vacía el contador y devuelve lo que había.

        Es lo que pasa al morir: todo lo que llevabas se queda en la
        mancha de sangre.
        """
        lost = self.total
        self.total = 0
        self.shown = 0.0
        return lost

    def update(self, dt):
        """Acerca el contador visible al total real."""
        difference = self.total - self.shown
        if abs(difference) < 0.5:
            self.shown = float(self.total)
            return
        speed = max(config.SOULS_COUNTER_MIN_SPEED, abs(difference) * config.SOULS_COUNTER_CATCHUP)
        self.shown += math.copysign(min(speed * dt, abs(difference)), difference)


class EstusFlask:
    """Los frascos de Estus: curación limitada que se repone descansando."""

    def __init__(self, charges=None):
        self.maximum = config.ESTUS_CHARGES if charges is None else int(charges)
        self.charges = self.maximum

    @property
    def has_any(self):
        return self.charges > 0

    def drink(self):
        """Gasta un frasco. Devuelve si quedaba alguno.

        La curación no se aplica aquí: el trago tarda, y lo que cura se
        cobra al final. El frasco, en cambio, se pierde al empezar —si te
        interrumpen a media bebida, lo has tirado igual—.
        """
        if not self.has_any:
            return False
        self.charges -= 1
        return True

    def refill(self):
        """Repone todos los frascos (descansar o reaparecer)."""
        self.charges = self.maximum


def level_cost(level):
    """Almas que cuesta pasar de `level` al siguiente.

    Crece con el nivel, así que cada punto es más caro que el anterior.
    """
    return int(
        config.LEVEL_COST_BASE + config.LEVEL_COST_GROWTH * level ** config.LEVEL_COST_EXPONENT
    )


class CharacterStats:
    """Vigor, Resistencia y Fuerza, y lo que cada una concede.

    El nivel del personaje es la suma de los puntos subidos por encima
    de la base, así que no se guarda aparte: se deduce.
    """

    # Nombre visible -> atributo. El orden es el del menú.
    ORDER = (("Vigor", "vigor"), ("Resistencia", "endurance"), ("Fuerza", "strength"))

    def __init__(self):
        self.vigor = config.BASE_VIGOR
        self.endurance = config.BASE_ENDURANCE
        self.strength = config.BASE_STRENGTH

    @property
    def level(self):
        """Puntos invertidos en total."""
        return (
            (self.vigor - config.BASE_VIGOR)
            + (self.endurance - config.BASE_ENDURANCE)
            + (self.strength - config.BASE_STRENGTH)
        )

    @property
    def next_level_cost(self):
        return level_cost(self.level)

    # --- Valores derivados ------------------------------------------------

    @property
    def max_health(self):
        return config.PLAYER_HEALTH + (self.vigor - config.BASE_VIGOR) * config.HEALTH_PER_VIGOR

    @property
    def max_stamina(self):
        return (
            config.STAMINA_MAX
            + (self.endurance - config.BASE_ENDURANCE) * config.STAMINA_PER_ENDURANCE
        )

    @property
    def stamina_regen(self):
        return (
            config.STAMINA_REGEN_RATE
            + (self.endurance - config.BASE_ENDURANCE) * config.STAMINA_REGEN_PER_ENDURANCE
        )

    @property
    def attack_damage(self):
        return (
            config.ATTACK_DAMAGE + (self.strength - config.BASE_STRENGTH) * config.DAMAGE_PER_STRENGTH
        )

    # --- Vista previa y subida -------------------------------------------

    def derived_for(self, attribute):
        """Qué valor derivado mueve una estadística: (etiqueta, valor)."""
        return {
            "vigor": ("Vida", self.max_health),
            "endurance": ("Estamina", self.max_stamina),
            "strength": ("Daño", self.attack_damage),
        }[attribute]

    def preview(self, attribute):
        """Vista previa de subir un punto: (etiqueta, actual, siguiente)."""
        label, current = self.derived_for(attribute)
        after = CharacterStats()
        after.vigor, after.endurance, after.strength = self.vigor, self.endurance, self.strength
        setattr(after, attribute, getattr(after, attribute) + 1)
        return (label, current, after.derived_for(attribute)[1])

    def raise_stat(self, attribute):
        """Sube un punto. Devuelve cuánto ha cambiado el valor derivado."""
        _, before, after = self.preview(attribute)
        setattr(self, attribute, getattr(self, attribute) + 1)
        return after - before
