"""HUD: los indicadores que se superponen al mundo.

De momento, las barras de vida y estamina del jugador, el contador de
almas y la barrita de los enemigos heridos, todo provisional. La HUD completa (almas, frascos de
Estus) llega en la Fase 6.

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
        renderer.draw_bar("health", *self.health_bar_rect(), player.health.ratio)
        renderer.draw_bar("stamina", *self.stamina_bar_rect(), player.stamina.ratio)
        renderer.draw_hud_text(self.estus_text(player), *self.estus_anchor())
        renderer.draw_hud_text(self.souls_text(player), *self.souls_anchor(), align="right")

    def draw_enemy_health(self, renderer, enemies, camera):
        """Barrita sobre cada enemigo herido; los intactos no la enseñan."""
        for enemy in enemies:
            if not enemy.is_hurt:
                continue
            renderer.draw_world_bar(
                "enemy_health",
                enemy.x - config.ENEMY_BAR_WIDTH / 2,
                enemy.y - config.ENEMY_BAR_OFFSET,
                config.ENEMY_BAR_WIDTH,
                config.ENEMY_BAR_HEIGHT,
                enemy.health.ratio,
                camera,
            )

    def estus_text(self, player):
        """Frascos de Estus que quedan, junto a las barras."""
        return f"ESTUS {player.estus.charges}"

    def estus_anchor(self):
        """Encima de la barra de vida, sin llegar a tocarla."""
        x, y, _, _ = self.health_bar_rect()
        return (x, y - config.HUD_TEXT_LINE - config.HUD_BAR_SPACING)

    def souls_text(self, player):
        """Lo que se escribe en el contador de almas."""
        return f"ALMAS {player.souls.displayed}"

    def souls_anchor(self):
        """Esquina superior derecha del contador, abajo a la derecha."""
        return (
            self.screen_width - config.HUD_MARGIN,
            self.screen_height - config.HUD_MARGIN - config.HUD_BAR_HEIGHT * 2,
        )

    # --- Colocación -------------------------------------------------------
    # Las dos barras del jugador se apilan abajo a la izquierda, con la
    # vida encima de la estamina.

    def stamina_bar_rect(self):
        """Rectángulo (x, y, ancho, alto) de la barra de estamina."""
        return (
            config.HUD_MARGIN,
            self.screen_height - config.HUD_MARGIN - config.HUD_BAR_HEIGHT,
            config.HUD_BAR_WIDTH,
            config.HUD_BAR_HEIGHT,
        )

    def health_bar_rect(self):
        """Rectángulo (x, y, ancho, alto) de la barra de vida."""
        x, y, width, height = self.stamina_bar_rect()
        return (x, y - height - config.HUD_BAR_SPACING, width, height)
