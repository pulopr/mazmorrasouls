"""Menús: el de la hoguera y el de subida de nivel.

Como la HUD, estos módulos deciden **qué** se muestra y en qué orden;
pintarlo es cosa del renderer. Son lógica pura y se pueden probar sin
abrir una ventana.
"""

from game import config
from game.systems.stats import CharacterStats


class Menu:
    """Una lista de opciones con un cursor."""

    def __init__(self, title, options):
        self.title = title
        self.options = list(options)
        self.index = 0

    @property
    def selected(self):
        return self.options[self.index]

    def move(self, step):
        """Mueve el cursor, dando la vuelta por los extremos."""
        self.index = (self.index + step) % len(self.options)

    def lines(self):
        """Las líneas a dibujar, en orden."""
        return list(self.options)


class BonfireMenu(Menu):
    """Lo que se puede hacer sentado en una hoguera."""

    LEVEL_UP = "Subir de nivel"
    LEAVE = "Salir"

    def __init__(self):
        super().__init__(config.BONFIRE_MENU_TITLE, config.BONFIRE_MENU_OPTIONS)


class LevelUpMenu(Menu):
    """Reparto de almas entre las tres estadísticas."""

    def __init__(self, player):
        self.player = player
        super().__init__(
            config.LEVEL_UP_TITLE, [label for label, _ in CharacterStats.ORDER]
        )

    @property
    def attribute(self):
        """El atributo interno de la opción señalada."""
        return CharacterStats.ORDER[self.index][1]

    @property
    def cost(self):
        return self.player.stats.next_level_cost

    @property
    def can_afford(self):
        return self.player.souls.total >= self.cost

    def confirm(self):
        """Intenta subir la estadística señalada."""
        return self.player.level_up(self.attribute)

    # --- Qué se enseña ----------------------------------------------------

    def header_lines(self):
        """Nivel, almas y coste, encima de la lista."""
        return [
            f"Nivel {self.player.stats.level}",
            f"Almas {self.player.souls.total}",
            f"Siguiente nivel: {self.cost}" + ("" if self.can_afford else "  (insuficientes)"),
        ]

    def lines(self):
        """Una línea por estadística, con su valor y el derivado."""
        rendered = []
        for label, attribute in CharacterStats.ORDER:
            value = getattr(self.player.stats, attribute)
            derived_label, derived = self.player.stats.derived_for(attribute)
            rendered.append(f"{label} {value}   {derived_label} {derived:.0f}")
        return rendered

    def preview_line(self):
        """Vista previa del cambio señalado: 'Vida 100 -> 112'."""
        label, before, after = self.player.stats.preview(self.attribute)
        return f"{label} {before:.0f} -> {after:.0f}"
