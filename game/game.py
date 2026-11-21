"""Bucle principal del juego.

Abre la ventana, carga un nivel y mueve al jugador a 60 FPS. La máquina de
estados (menú, jugando, muerte) llegará cuando haya estados que distinguir;
aquí basta con "se está ejecutando" o no.
"""

import pygame

from game import config
from game.entities.enemy import Enemy
from game.entities.player import Intent, Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
from game.systems import combat
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
        self.enemies = Enemy.spawn_from_level(self.level)
        self.camera = Camera(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.camera.follow(self.player.x, self.player.y, self.level)
        self.hud = Hud(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.running = True
        # Rodar y atacar se piden con una pulsación, no manteniendo la
        # tecla: así dejar el dedo encima no encadena acciones.
        self.roll_requested = False
        self.attack_requested = False
        # Modo depuración: dibuja hitboxes y cajas de colisión (F1).
        self.debug = False

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
                elif event.key == config.KEY_ATTACK_LIGHT:
                    self.attack_requested = True
                elif event.key == config.KEY_DEBUG:
                    self.debug = not self.debug

    def update(self, dt):
        """Avanza la simulación un fotograma."""
        self.player.update(dt, self.read_intent(), self.level)

        # El cruce entre jugador y enemigos lo resuelve el sistema de
        # combate, no las entidades: así ninguna necesita conocer a la otra.
        combat.resolve_player_attack(self.player, self.enemies, self.level)
        for enemy in self.enemies:
            enemy.update(dt, self.level)
        # Los muertos desaparecen del mundo.
        self.enemies = [enemy for enemy in self.enemies if enemy.is_alive]

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
            attack=self.attack_requested,
        )
        # Las peticiones se consumen: valen para un solo fotograma.
        self.roll_requested = False
        self.attack_requested = False
        return intent

    def draw(self):
        self.renderer.begin_frame()
        self.renderer.draw_level(self.level, self.camera)
        for enemy in self.enemies:
            self.renderer.draw_entity(enemy, self.camera)
        self.renderer.draw_entity(self.player, self.camera)

        # El tajo solo se ve mientras el golpe está activo.
        hitbox = self.player.attack_hitbox()
        if hitbox is not None:
            self.renderer.draw_attack(*hitbox.center, self.player.facing, self.camera)

        self.hud.draw_enemy_health(self.renderer, self.enemies, self.camera)
        self.hud.draw(self.renderer, self.player)
        if self.debug:
            self.draw_debug()
        self.renderer.present()

    def draw_debug(self):
        """Contornos de las cajas: colisión en azul, hitboxes en rojo."""
        for entity in [self.player, *self.enemies]:
            self.renderer.draw_box_outline(
                combat.Box.from_entity(entity), self.camera, "collision"
            )
        hitbox = self.player.attack_hitbox()
        if hitbox is not None:
            self.renderer.draw_box_outline(hitbox, self.camera, "hitbox")
