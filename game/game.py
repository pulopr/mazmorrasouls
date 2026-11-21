"""Bucle principal y estados del juego."""

from enum import Enum, auto

import pygame

from game import config
from game.entities.bloodstain import Bloodstain
from game.entities.enemy import Enemy
from game.entities.player import Intent, Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
from dataclasses import replace

from game.systems import combat, projectiles, targeting
from game.ui.hud import Hud
from game.world.level import Level


class GameState(Enum):
    """En qué pantalla está el juego.

    Cada estado tiene su propio `update`, así que añadir el menú de
    hoguera y la pausa (Fase 5) es sumar una entrada aquí y un método.
    """

    PLAYING = auto()
    DEAD = auto()     # cartel de muerte; al acabar, el jugador reaparece


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
        # Órdenes de fijado pendientes: fijar/soltar y cambiar de objetivo.
        self.lock_requested = False
        self.lock_cycle = 0
        # Interactuar (E): de momento solo recoger la mancha de sangre.
        self.interact_requested = False
        # Modo depuración: hitboxes, cajas de colisión y radios (F1).
        self.debug = False

        self.start_level()

    def start_level(self):
        """Prepara el nivel desde cero: partida nueva."""
        self.player = Player.at_level_start(self.level)
        # Élites ya derrotados: no vuelven a aparecer.
        self.defeated_for_good = set()
        self.bloodstain = None
        self.respawn_enemies()
        self.camera.follow(self.player.x, self.player.y, self.level)
        self.state = GameState.PLAYING
        self.death_timer = 0.0

    def respawn_enemies(self):
        """Repuebla el nivel, saltándose a los que no deben volver."""
        self.enemies = Enemy.spawn_from_level(self.level, skip=self.defeated_for_good)
        self.projectiles = []
        # El objetivo fijado apuntaba a un enemigo que ya no existe.
        self.lock = targeting.LockOn()

    def kill_player(self):
        """El jugador ha muerto: suelta las almas y arranca el cartel."""
        # La mancha anterior se pierde para siempre: solo puede haber una.
        lost = self.player.souls.take_all()
        self.bloodstain = (
            Bloodstain.drop(self.level, self.player.x, self.player.y, lost, self.enemies)
            if lost > 0
            else None
        )
        self.state = GameState.DEAD
        self.death_timer = config.DEATH_SCREEN_DURATION

    def respawn_player(self):
        """Devuelve al jugador a su punto de reaparición y repuebla el nivel."""
        self.player.revive()
        self.respawn_enemies()
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
                elif event.key == config.KEY_INTERACT:
                    self.interact_requested = True
                elif event.key == config.KEY_LOCK_ON:
                    self.lock_requested = True
                elif event.key == config.KEY_LOCK_PREV:
                    self.lock_cycle = -1
                elif event.key == config.KEY_LOCK_NEXT:
                    self.lock_cycle = 1
                elif event.key == config.KEY_DEBUG:
                    self.debug = not self.debug

    def update(self, dt):
        """Avanza la simulación un fotograma."""
        if self.state is GameState.DEAD:
            self.update_death(dt)
            return

        intent = self.read_intent()
        intent = self.update_lock(dt, intent)
        self.player.update(dt, intent, self.level)

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

        self.collect_the_dead()
        self.update_bloodstain(dt)

        if not self.player.is_alive:
            self.kill_player()

        self.camera.follow(*targeting.camera_focus(self.player, self.lock.target), self.level)

    def collect_the_dead(self):
        """Retira a los caídos y cobra sus almas."""
        survivors = []
        for enemy in self.enemies:
            if enemy.is_alive:
                survivors.append(enemy)
                continue
            self.player.souls.gain(enemy.profile.souls)
            if not enemy.profile.respawns:
                # Un élite derrotado no vuelve nunca más.
                self.defeated_for_good.add(enemy.spawn_index)
        self.enemies = survivors

    def update_bloodstain(self, dt):
        """Hace parpadear la mancha y la recoge si se pulsa E al lado."""
        if self.bloodstain is None:
            self.interact_requested = False
            return

        self.bloodstain.update(dt)
        if self.interact_requested and self.bloodstain.can_be_reached_by(self.player):
            self.player.souls.gain(self.bloodstain.collect())
            self.bloodstain = None
        self.interact_requested = False

    def update_lock(self, dt, intent):
        """Atiende las órdenes de fijado y devuelve el Intent con la mirada."""
        if self.lock_requested:
            self.lock.toggle(self.player, self.enemies, self.level)
        if self.lock_cycle:
            self.lock.cycle(self.lock_cycle, self.player, self.enemies, self.level)
        self.lock_requested = False
        self.lock_cycle = 0

        # Correr suelta el fijado, como en Dark Souls.
        if intent.run and intent.direction != (0, 0):
            self.lock.release()

        self.lock.update(dt, self.player, self.enemies, self.level)
        return replace(intent, look_at=self.lock.look_at())

    def update_death(self, dt):
        """Cuenta atrás del cartel de muerte. La acción está detenida."""
        self.death_timer -= dt
        # La mancha sigue parpadeando mientras sale el cartel.
        if self.bloodstain is not None:
            self.bloodstain.update(dt)
        # Las peticiones acumuladas no deben dispararse al reaparecer.
        self.roll_requested = False
        self.attack_requested = False
        self.lock_requested = False
        self.lock_cycle = 0
        self.interact_requested = False
        if self.death_timer <= 0:
            # Reaparecer, no empezar de cero: la mancha y los élites
            # derrotados sobreviven a la muerte.
            self.respawn_player()

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
        if self.bloodstain is not None:
            self.renderer.draw_entity(self.bloodstain, self.camera)
        for enemy in self.enemies:
            self.renderer.draw_entity(enemy, self.camera)
        if self.lock.is_locked:
            self.renderer.draw_lock_marker(self.lock.target, self.camera)
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
