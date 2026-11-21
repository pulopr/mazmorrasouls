"""Bucle principal del juego.

Abre la ventana, carga un nivel y mueve al jugador a 60 FPS. La máquina de
estados (menú, jugando, muerte) llegará cuando haya estados que distinguir;
aquí basta con "se está ejecutando" o no.
"""

import pygame

from game import config
from game.entities.player import Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
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
        self.player = Player.at_level_start(self.level)
        self.camera = Camera(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.camera.follow(self.player.x, self.player.y, self.level)
        self.running = True

    # --- Bucle ------------------------------------------------------------

    def run(self):
        """Ejecuta el bucle hasta que se pida salir."""
        while self.running:
            # `dt` en segundos: todo movimiento y temporizador se multiplica
            # por él, aunque el reloj esté fijado a 60 FPS.
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
                # Fase 1: Esc cierra. Más adelante abrirá la pausa.
                self.running = False

    def update(self, dt):
        """Avanza la simulación un fotograma."""
        self.player.update(dt, self.read_direction(), self.level)
        self.camera.follow(self.player.x, self.player.y, self.level)

    @staticmethod
    def read_direction():
        """Lee WASD y devuelve la intención de movimiento, sin normalizar.

        Normalizar es cosa del jugador; aquí solo se traduce el teclado.
        """
        keys = pygame.key.get_pressed()
        dx = keys[config.KEY_MOVE_RIGHT] - keys[config.KEY_MOVE_LEFT]
        dy = keys[config.KEY_MOVE_DOWN] - keys[config.KEY_MOVE_UP]
        return dx, dy

    def draw(self):
        self.renderer.begin_frame()
        self.renderer.draw_level(self.level, self.camera)
        self.renderer.draw_entity(self.player, self.camera)
        self.renderer.present()
