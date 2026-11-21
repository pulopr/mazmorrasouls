"""Bucle principal y estados del juego."""

from enum import Enum, auto

import pygame

from game import config
from game.entities.bloodstain import Bloodstain
from game.entities.bonfire import Bonfire
from game.entities.enemy import Enemy
from game.entities.player import Intent, Player
from game.render.ascii_renderer import AsciiRenderer
from game.render.camera import Camera
from dataclasses import replace

from game.systems import combat, projectiles, targeting
from game.ui.hud import Hud
from game.ui.menus import BonfireMenu, LevelUpMenu
from game.world.level import Level


class GameState(Enum):
    """En qué pantalla está el juego.

    Cada estado tiene su propio `update`, así que añadir el menú de
    hoguera y la pausa (Fase 5) es sumar una entrada aquí y un método.
    """

    PLAYING = auto()
    DEAD = auto()          # cartel de muerte; al acabar, el jugador reaparece
    BONFIRE_MENU = auto()  # sentado en la hoguera; el mundo en pausa
    LEVEL_UP = auto()      # repartiendo almas; el mundo en pausa


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
        # Interactuar (E): recoger la mancha o usar la hoguera.
        self.interact_requested = False
        self.drink_requested = False
        # Modo depuración: hitboxes, cajas de colisión y radios (F1).
        self.debug = False

        self.start_level()

    def start_level(self):
        """Prepara el nivel desde cero: partida nueva."""
        self.player = Player.at_level_start(self.level)
        # Élites ya derrotados: no vuelven a aparecer.
        self.defeated_for_good = set()
        self.bloodstain = None
        self.bonfires = Bonfire.spawn_from_level(self.level)
        self.menu = None
        self.notice = None
        self.notice_timer = 0.0
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
                if self.menu is not None:
                    self.handle_menu_key(event.key)
                elif event.key == config.KEY_PAUSE:
                    # Fase 3: Esc cierra. Más adelante abrirá la pausa.
                    self.running = False
                elif event.key == config.KEY_ROLL:
                    self.roll_requested = True
                elif event.key == config.KEY_ATTACK_LIGHT:
                    self.attack_requested = True
                elif event.key == config.KEY_INTERACT:
                    self.interact_requested = True
                elif event.key == config.KEY_ESTUS:
                    self.drink_requested = True
                elif event.key == config.KEY_LOCK_ON:
                    self.lock_requested = True
                elif event.key == config.KEY_LOCK_PREV:
                    self.lock_cycle = -1
                elif event.key == config.KEY_LOCK_NEXT:
                    self.lock_cycle = 1
                elif event.key == config.KEY_DEBUG:
                    self.debug = not self.debug

    def update(self, dt):
        """Avanza la simulación un fotograma, según el estado del juego."""
        if self.state is GameState.DEAD:
            self.update_death(dt)
            return
        if self.state in (GameState.BONFIRE_MENU, GameState.LEVEL_UP):
            # Con un menú abierto el mundo queda en pausa; solo el
            # contador de almas sigue animándose.
            self.player.souls.update(dt)
            return

        self.tick_notice(dt)

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
        for bonfire in self.bonfires:
            bonfire.update(dt)
        self.update_bloodstain(dt)
        self.resolve_interaction()

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
        """Solo el parpadeo; recogerla es cosa de resolve_interaction()."""
        if self.bloodstain is not None:
            self.bloodstain.update(dt)

    def resolve_interaction(self):
        """Atiende la tecla E, sea lo que sea lo que haya al lado.

        Se resuelve en un único sitio para que la mancha y la hoguera no
        se pisen la petición entre ellas.
        """
        if not self.interact_requested:
            return
        self.interact_requested = False

        if self.collect_bloodstain():
            return
        self.use_bonfire()

    def collect_bloodstain(self):
        """Recoge la mancha si el jugador la tiene al lado."""
        if self.bloodstain is None or not self.bloodstain.can_be_reached_by(self.player):
            return False
        self.player.souls.gain(self.bloodstain.collect())
        self.bloodstain = None
        return True

    # --- Hogueras ---------------------------------------------------------

    def show_notice(self, text, duration):
        """Enseña un aviso breve en el centro."""
        self.notice = text
        self.notice_timer = duration

    def tick_notice(self, dt):
        self.notice_timer = max(0.0, self.notice_timer - dt)
        if self.notice_timer <= 0:
            self.notice = None

    @property
    def being_hunted(self):
        """¿Hay algún enemigo detrás del jugador ahora mismo?"""
        return any(enemy.is_hunting for enemy in self.enemies)

    def bonfire_within_reach(self):
        """La hoguera que el jugador tiene al lado, si la hay."""
        for bonfire in self.bonfires:
            if bonfire.is_within_reach(self.player):
                return bonfire
        return None

    def use_bonfire(self):
        """E junto a una hoguera: encenderla o sentarse a descansar."""
        bonfire = self.bonfire_within_reach()
        if bonfire is None:
            return

        if bonfire.light():
            # Primera vez: se enciende y pasa a ser el punto de reaparición.
            self.player.respawn_point = (bonfire.x, bonfire.y)
            self.show_notice(config.BONFIRE_LIT_MESSAGE, config.BONFIRE_LIT_NOTICE_DURATION)
            return

        if self.being_hunted:
            self.show_notice(config.BONFIRE_BUSY_MESSAGE, config.BONFIRE_BUSY_NOTICE_DURATION)
            return

        self.rest_at(bonfire)

    def rest_at(self, bonfire):
        """Descansar: todo a tope, enemigos de vuelta y menú abierto."""
        self.player.respawn_point = (bonfire.x, bonfire.y)
        self.player.rest()
        # Misma lógica que al morir: vuelven todos menos los élites caídos.
        # La mancha de sangre no se toca: solo morir la destruye.
        self.respawn_enemies()
        self.menu = BonfireMenu()
        self.state = GameState.BONFIRE_MENU
        self.notice = None

    # --- Menús ------------------------------------------------------------

    def handle_menu_key(self, key):
        """Navegación común: W/S mueven, E o J confirman, Esc cierra."""
        if key == config.KEY_MOVE_UP:
            self.menu.move(-1)
        elif key == config.KEY_MOVE_DOWN:
            self.menu.move(1)
        elif key in (config.KEY_INTERACT, config.KEY_ATTACK_LIGHT):
            self.confirm_menu()
        elif key == config.KEY_PAUSE:
            self.close_menu()

    def confirm_menu(self):
        """Qué hace confirmar, según el menú abierto."""
        if self.state is GameState.BONFIRE_MENU:
            if self.menu.selected == BonfireMenu.LEVEL_UP:
                self.menu = LevelUpMenu(self.player)
                self.state = GameState.LEVEL_UP
            else:
                self.close_menu()
        elif self.state is GameState.LEVEL_UP:
            self.menu.confirm()

    def close_menu(self):
        """Esc: del menú de nivel se vuelve a la hoguera; de ahí, al juego."""
        if self.state is GameState.LEVEL_UP:
            self.menu = BonfireMenu()
            self.state = GameState.BONFIRE_MENU
            return
        self.menu = None
        self.state = GameState.PLAYING
        # Levantarse no debe disparar la interacción otra vez.
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
            drink=self.drink_requested,
        )
        # Las peticiones se consumen: valen para un solo fotograma.
        self.roll_requested = False
        self.attack_requested = False
        self.drink_requested = False
        return intent

    # --- Dibujado ---------------------------------------------------------

    def draw(self):
        self.renderer.begin_frame()
        self.renderer.draw_level(self.level, self.camera)
        for bonfire in self.bonfires:
            self.renderer.draw_entity(bonfire, self.camera)
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
        if self.notice:
            self.renderer.draw_notice(self.notice)
        if self.state is GameState.DEAD:
            self.renderer.draw_message(config.DEATH_MESSAGE)
        if self.menu is not None:
            self.draw_menu()
        self.renderer.present()

    def draw_menu(self):
        """Dibuja el menú abierto con su cabecera y su ayuda."""
        if self.state is GameState.LEVEL_UP:
            self.renderer.draw_panel(
                self.menu.title,
                self.menu.header_lines(),
                self.menu.lines(),
                self.menu.index,
                footer=[self.menu.preview_line(), "W/S elegir   E subir   Esc volver"],
            )
            return
        self.renderer.draw_panel(
            self.menu.title,
            [],
            self.menu.lines(),
            self.menu.index,
            footer=["W/S elegir   E confirmar   Esc salir"],
        )

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
