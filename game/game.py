"""Bucle principal del juego.

Abre la ventana, carga un nivel y mueve al jugador a 60 FPS. La máquina de
estados (menú, jugando, muerte) llegará cuando haya estados que distinguir;
aquí basta con "se está ejecutando" o no.
"""

import pygame

from game import config
from game.entities.player import Intent, Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
from game.ui.hud import Hud
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
        self.hud = Hud(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.running = True
        # El rodar se pide con una pulsación, no manteniendo la tecla: así
        # dejar el dedo en Espacio no encadena volteretas.
        self.roll_requested = False

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
            elif event.type == pygame.KEYDOWN:
                if event.key == config.KEY_PAUSE:
                    # Fase 2: Esc cierra. Más adelante abrirá la pausa.
                    self.running = False
                elif event.key == config.KEY_ROLL:
                    self.roll_requested = True

    def update(self, dt):
        """Avanza la simulación un fotograma."""
        self.player.update(dt, self.read_intent(), self.level)
        self.camera.follow(self.player.x, self.player.y, self.level)

    def read_intent(self):
        """Traduce el teclado a un Intent. Aquí no se decide nada más."""
        keys = pygame.key.get_pressed()
        intent = Intent(
            direction=(
                keys[config.KEY_MOVE_RIGHT] - keys[config.KEY_MOVE_LEFT],
                keys[config.KEY_MOVE_DOWN] - keys[config.KEY_MOVE_UP],
            ),
            roll=self.roll_requested,
            run=any(keys[key] for key in config.KEY_RUN),
        )
        # La petición de rodar se consume: vale para un solo fotograma.
        self.roll_requested = False
        return intent

    def draw(self):
        self.renderer.begin_frame()
        self.renderer.draw_level(self.level, self.camera)
        self.renderer.draw_entity(self.player, self.camera)
        self.hud.draw(self.renderer, self.player)
        self.renderer.present()
