"""Bucle principal del juego.

De momento solo abre la ventana, carga un nivel y lo dibuja a 60 FPS. La
máquina de estados (menú, jugando, muerte) llegará cuando haya estados que
distinguir; aquí basta con "se está ejecutando" o no.
"""

import pygame

from game import config
from game.render.ascii_renderer import AsciiRenderer
from game.world.level import Level


class Game:
    """Dueño de la ventana, el reloj y el bucle de fotogramas."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.CAPTION)
        self.clock = pygame.time.Clock()
        self.renderer = AsciiRenderer(self.screen)
        self.level = Level.load(config.DEFAULT_LEVEL)
        self.running = True

    # --- Bucle ------------------------------------------------------------

    def run(self):
        """Ejecuta el bucle hasta que se pida salir."""
        while self.running:
            # `dt` en segundos: todo movimiento y temporizador futuro se
            # multiplicará por él, aunque el reloj esté fijado a 60 FPS.
            dt = self.clock.tick(config.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == config.KEY_PAUSE:
                # Fase 0: Esc cierra. Más adelante abrirá la pausa.
                self.running = False

    def update(self, dt):
        """Avanza la simulación. Todavía no hay nada que se mueva."""

    def draw(self):
        self.renderer.draw_level(self.level)
        self.renderer.present()
