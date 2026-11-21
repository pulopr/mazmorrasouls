"""HUD: los indicadores que se superponen al mundo.

De momento solo la barra de estamina, provisional. La HUD completa (vida,
almas, frascos de Estus) llega en la Fase 6.

Este módulo decide **qué** se muestra y **dónde**; el dibujado en sí es
cosa del renderer, que es el único que toca píxeles.
"""

from game import config


class Hud:
    """Coloca los indicadores sobre la pantalla."""

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

    def draw(self, renderer, player):
        """Pide al renderer que pinte los indicadores del jugador."""
        renderer.draw_bar("stamina", *self.stamina_bar_rect(), player.stamina.ratio)

    def stamina_bar_rect(self):
        """Rectángulo (x, y, ancho, alto) de la barra, abajo a la izquierda."""
        return (
            config.HUD_MARGIN,
            self.screen_height - config.HUD_MARGIN - config.HUD_BAR_HEIGHT,
            config.HUD_BAR_WIDTH,
            config.HUD_BAR_HEIGHT,
        )
