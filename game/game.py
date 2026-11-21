"""Bucle principal y estados del juego."""

from enum import Enum, auto

import pygame

from game import config
from game.entities.enemy import Enemy
from game.entities.player import Intent, Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
from game.systems import combat, projectiles
from game.ui.hud import Hud
from game.world.level import Level


class GameState(Enum):
    """En qué pantalla está el juego."""

    PLAYING = auto()
    DEAD = auto()   # cartel de muerte; al acabar, se reinicia el nivel


class Game:
    """Dueño de la ventana, el reloj y el bucle de fotogramas."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.CAPTION)
        self.clock = pygame.time.Clock()
        self.renderer = AsciiRenderer(self.screen)
        self.hud = Hud(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        self.camera = Camera(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)

        self.level = Level.load(config.DEFAULT_LEVEL)
        self.running = True
        # Rodar y atacar se piden con una pulsación, no manteniendo la
        # tecla: así dejar el dedo encima no encadena acciones.
        self.roll_requested = False
        self.attack_requested = False
        # Modo depuración: hitboxes, cajas de colisión y radios (F1).
        self.debug = False

        self.reset_level()

    def reset_level(self):
        """Deja el nivel como al empezar: jugador vivo y enemigos en su sitio."""
        self.player = Player.at_level_start(self.level)
        self.enemies = Enemy.spawn_from_level(self.level)
        self.projectiles = []
        self.camera.follow(self.player.x, self.player.y, self.level)
        self.state = GameState.PLAYING
        self.death_timer = 0.0

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
                    # Fase 3: Esc cierra. Más adelante abrirá la pausa.
                    self.running = False
                elif event.key == config.KEY_ROLL:
                    self.roll_requested = True
                elif event.key == config.KEY_ATTACK_LIGHT:
                    self.attack_requested = True
                elif event.key == config.KEY_DEBUG:
                    self.debug = not self.debug

    def update(self, dt):
        """Avanza la simulación un fotograma."""
        if self.state is GameState.DEAD:
            self.update_death(dt)
            return

        self.player.update(dt, self.read_intent(), self.level)

        # El cruce entre jugador y enemigos lo resuelve el sistema de
        # combate, no las entidades: así ninguna necesita conocer a la otra.
        combat.resolve_player_attack(self.player, self.enemies, self.level)
        for enemy in self.enemies:
            enemy.update(dt, self.level, self.player)
        combat.resolve_enemy_attacks(self.enemies, self.player, self.level)
        combat.separate_enemies(self.enemies, self.player, self.level)

        # Flechas: primero las recién disparadas, luego vuelan todas.
        self.projectiles += projectiles.collect_pending(self.enemies)
        self.projectiles = projectiles.update_projectiles(
            self.projectiles, dt, self.level, [self.player]
        )

        # Los muertos desaparecen del mundo.
        self.enemies = [enemy for enemy in self.enemies if enemy.is_alive]

        if not self.player.is_alive:
            self.state = GameState.DEAD
            self.death_timer = config.DEATH_SCREEN_DURATION

        self.camera.follow(self.player.x, self.player.y, self.level)

    def update_death(self, dt):
        """Cuenta atrás del cartel de muerte y reinicio del nivel.

        Provisional hasta la Fase 4, que traerá hogueras y mancha de sangre.
        """
        self.death_timer -= dt
        # Las peticiones acumuladas no deben dispararse al reaparecer.
        self.roll_requested = False
        self.attack_requested = False
        if self.death_timer <= 0:
            self.reset_level()

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

    # --- Dibujado ---------------------------------------------------------

    def draw(self):
        self.renderer.begin_frame()
        self.renderer.draw_level(self.level, self.camera)
        for enemy in self.enemies:
            self.renderer.draw_entity(enemy, self.camera)
        for arrow in self.projectiles:
            self.renderer.draw_projectile(arrow, self.camera)
        if self.player.is_alive:
            self.renderer.draw_entity(self.player, self.camera)

        self.draw_attacks()
        self.hud.draw_enemy_health(self.renderer, self.enemies, self.camera)
        self.hud.draw(self.renderer, self.player)
        if self.debug:
            self.draw_debug()
        if self.state is GameState.DEAD:
            self.renderer.draw_message(config.DEATH_MESSAGE)
        self.renderer.present()

    def draw_attacks(self):
        """Los tajos solo se ven mientras su golpe está activo."""
        for attacker in [self.player, *self.enemies]:
            hitbox = attacker.attack_hitbox()
            if hitbox is not None:
                self.renderer.draw_attack(*hitbox.center, attacker.facing, self.camera)

    def draw_debug(self):
        """Cajas, radios de detección y estado de cada enemigo."""
        for entity in [self.player, *self.enemies]:
            self.renderer.draw_box_outline(
                combat.Box.from_entity(entity), self.camera, "collision"
            )
            hitbox = entity.attack_hitbox()
            if hitbox is not None:
                self.renderer.draw_box_outline(hitbox, self.camera, "hitbox")

        for enemy in self.enemies:
            self.renderer.draw_circle_outline(
                enemy.x, enemy.y, enemy.profile.detect_radius, self.camera
            )
            self.renderer.draw_debug_text(
                enemy.state.name, enemy.x, enemy.top - 10, self.camera
            )
            # Trayectoria prevista mientras el arquero tensa el arco.
            if getattr(enemy, "is_aiming", False):
                self.renderer.draw_debug_line(*enemy.aim_line(), self.camera)
