# CLAUDE.md — Juego de mazmorras estilo Souls (ASCII)

Este archivo es la referencia del proyecto. Léelo al empezar cada sesión y actualiza la sección **Estado actual** al terminar cada tarea.

## Visión

Juego de acción en **tiempo real**, vista cenital, ambientado en una mazmorra e inspirado en Dark Souls:
- Combate exigente con **estamina**: atacar y rodar la consumen.
- Al matar enemigos se ganan **almas**, que se gastan en subir estadísticas.
- **Hogueras**: descansar en una cura, rellena los frascos de Estus, reaparece a los enemigos y fija el punto de reaparición. Desde ella se sube de nivel.
- **Muerte**: el jugador reaparece en la última hoguera y deja sus almas donde murió (mancha de sangre). Si llega a ella las recupera. Si muere antes, se pierden.
- Niveles **diseñados a mano**, con atajos y puertas que se abren desde un lado, no generados al azar.

Es un proyecto personal de aprendizaje. Se prefiere código claro y comentado a código astuto.

## Tecnología

- **Python 3.11+** y **pygame-ce** (`pip install pygame-ce`, se importa como `pygame`).
- Entorno virtual en `.venv/`. Las dependencias van en `requirements.txt`.
- Tests con **pytest** para la lógica (daño, costes de nivel, colisiones, estados).
- Sin más dependencias salvo que se acuerde.

## Gráficos: ASCII ahora, sprites después

Los gráficos empiezan en ASCII (caracteres dibujados con una fuente monoespaciada dentro de pygame) y más adelante se sustituirán por sprites. Para que ese cambio no obligue a reescribir nada:

- **La lógica nunca dibuja.** Ningún archivo fuera de `game/render/` llama a `pygame.draw`, `blit` ni carga fuentes.
- Cada entidad tiene un `sprite_id` (`"player"`, `"skeleton"`, `"bonfire"`...). El renderer traduce ese id a lo que toque: hoy un carácter y un color, mañana una imagen.
- Las tablas de glifos y colores viven en `game/render/ascii_theme.py`.

## Arquitectura

```
main.py                  # punto de entrada
game/
  config.py              # constantes: tamaño de tile, FPS, controles, balance
  game.py                # bucle principal y máquina de estados (menú, jugando, muerte, nivel)
  world/
    level.py             # carga mapas desde data/levels/*.txt, colisión con muros
  entities/
    entity.py            # clase base: posición (float), tamaño, sprite_id
    player.py
    enemy.py
  systems/
    combat.py            # hitboxes, daño, invulnerabilidad al rodar
    stats.py             # estadísticas, coste de subir nivel
  render/
    renderer.py          # interfaz común
    ascii_renderer.py
    ascii_theme.py
    camera.py
  ui/
    hud.py               # vida, estamina, almas, frascos
    menus.py             # menú de hoguera y subida de nivel
data/
  levels/                # mapas en texto
tests/
```

### Convenciones
- **Código en inglés** (nombres de variables, funciones y clases). **Comentarios, docstrings y documentación en español.**
- Paso de tiempo fijo (60 FPS). Todo movimiento y temporizador se multiplica por `dt`.
- El mundo es una cuadrícula de tiles para el mapa, pero las entidades se mueven con **posición continua** (píxeles en float) y colisión por cajas (AABB) contra los muros.
- Los números de balance (daño, velocidades, costes) van en `config.py` o en `data/`, nunca sueltos por el código.

## Formato de mapas (`data/levels/*.txt`)

| Carácter | Significado |
|---|---|
| `#` | Muro |
| `.` | Suelo |
| `@` | Inicio del jugador |
| `B` | Hoguera |
| `s` | Esqueleto (enemigo básico) |
| `A` | Esqueleto arquero |
| `D` | Enemigo difícil (élite): más vida, más daño y más almas |
| `*` | Objeto (por definir; de momento solo decorado) |
| `+` | Puerta |

La mancha de sangre (`&`) no se escribe en el mapa: nace al morir el jugador.

## Controles (iniciales)

| Tecla | Acción |
|---|---|
| WASD | Moverse |
| J | Ataque ligero |
| Espacio | Rodar (esquiva con frames de invulnerabilidad) |
| Shift | Correr (gasta estamina mientras se mueve) |
| Q | Beber Estus |
| E | Interactuar (hoguera, puertas) |
| Esc | Pausa |
| Tab | Fijar o soltar el objetivo más cercano (lock-on) |
| Flecha izq./der. | Cambiar de objetivo fijado |
| F1 | Modo depuración: hitboxes y cajas de colisión |

## Estadísticas (primera versión)

- **Vigor**: vida máxima.
- **Resistencia**: estamina máxima y velocidad de recuperación.
- **Fuerza**: daño del ataque.
- Cada nivel cuesta más almas que el anterior. La fórmula está en `systems/stats.py` y sus constantes en `config.py`.

## Forma de trabajar

1. Cada tarea es **una funcionalidad pequeña**. No adelantes trabajo de fases futuras.
2. Antes de programar algo no trivial, explica brevemente el plan.
3. Añade tests para la lógica nueva y ejecuta `pytest` antes de dar la tarea por terminada.
4. Comprueba que el juego arranca sin errores (se puede usar `SDL_VIDEODRIVER=dummy` para una prueba sin ventana).
5. Al terminar: actualiza **Estado actual**, resume qué se ha hecho y cómo probarlo, y propón el mensaje de commit.

## Hoja de ruta

- [x] **Fase 0**: estructura del proyecto, ventana, bucle, renderer ASCII mostrando un mapa de prueba.
- [x] **Fase 1**: movimiento del jugador en tiempo real, colisiones con muros y cámara que lo sigue.
- [x] **Fase 2**: estamina y rodar con invulnerabilidad.
- [ ] **Fase 3**: enemigo básico (patrulla, persigue, ataque con aviso previo), ataque del jugador, vida y muerte de enemigos.
  - [x] **3a**: ataque del jugador, enemigos con vida y muerte (sin IA).
  - [x] **3b**: IA del esqueleto (persigue, ataca con aviso) y daño al jugador.
- [x] **Fase 4**: almas, muerte del jugador y mancha de sangre.
- [ ] **Fase 5**: hogueras (descanso, reaparición de enemigos, Estus) y menú de subida de nivel.
- [ ] **Fase 6**: HUD completo y pantalla de "HAS MUERTO".
- [ ] **Fase 7**: más tipos de enemigos, puertas y atajos, primer jefe.
  - [x] Arquero (`A`) y élite (`D`) ya existen; faltan puertas, atajos y jefe.
- [ ] **Fase 8**: guardado de partida.
- [ ] **Fase 9**: sustituir el ASCII por sprites o tiles.

## Estado actual

**Fases 0, 1, 2, 3 y 4 terminadas.**

Fase 0 — esqueleto:
- Entorno virtual en `.venv/`, `requirements.txt` (pygame-ce 2.5.8, pytest 9.2.0) y `.gitignore`.
- `main.py` + `game/game.py`: ventana de 960x540 y bucle a 60 FPS con `dt` en segundos,
  que se cierra con Esc o con la X.
- `game/render/`: interfaz `Renderer`, `AsciiRenderer` (glifos monoespaciados cacheados)
  y `ascii_theme.py` (glifos y colores por `sprite_id`).

Fase 1 — movimiento:
- `game/entities/entity.py`: clase base con posición continua en float (el centro de la
  caja), tamaño y `sprite_id`, con los bordes `left/right/top/bottom` como propiedades.
- `Level.move_with_collision()`: colisión AABB resolviendo **un eje cada vez**, de modo
  que al empujar en diagonal contra una pared el jugador se desliza en vez de clavarse.
  `Level` conoce su `tile_size` y expone `pixel_width`/`pixel_height` y `tile_center()`.
- `game/render/camera.py`: sigue al jugador y se recorta a los bordes del mapa; si el
  mapa cabe entero en la ventana, lo centra. Aritmética pura, sin pygame.
- `data/levels/test_big.txt` (56x32 tiles, cuatro salas con pasillos) y
  `data/levels/test.txt` (sala pequeña) son los mapas de los tests.

Fase 2 — estamina, rodar y correr:
- `game/systems/stats.py`: clase `Stamina`. Gastar nunca deja la barra en negativo y
  reinicia el respiro; pasado `STAMINA_REGEN_DELAY` vuelve a subir, arrastrando el
  tiempo sobrante del fotograma para no perder fracciones.
- `game/entities/player.py`: estados explícitos en `PlayerState` (NORMAL, RUNNING,
  ROLLING) y un `Intent(direction, roll, run)` que separa leer el teclado de decidir
  qué pasa. El jugador guarda su `facing`.
  - **Rodar**: cuesta estamina y se permite con cualquier resto mayor que 0. Distancia
    y duración fijas (128 px = 4 casillas en 0,26 s), rumbo fijado al empezar —de las
    teclas o, si no hay, de la mirada—, sin poder cambiarlo ni encadenar otro rodar, y
    respetando las colisiones. `is_invulnerable` cubre la ventana de i-frames.
    No va a velocidad constante: sigue una curva **ease-out** (`roll_progress()`), con
    un pico inicial de 985 px/s (5,5x andar) que frena hasta pararse. Se mueve por
    diferencia de progreso, no por velocidad x tiempo, así que el total es exactamente
    `ROLL_DISTANCE` con cualquier `dt`.
  - **Correr**: 1,5x la velocidad de andar a cambio de un goteo de estamina; al vaciarse
    la barra se sigue andando a velocidad normal.
- `game/ui/hud.py`: barra de estamina provisional abajo a la izquierda. El HUD decide
  qué indicador y dónde, y llama a `renderer.draw_bar()`; los píxeles y los colores
  siguen viviendo en `render/`.
- El `sprite_id` del jugador cambia a `player_rolling` / `player_invulnerable`, así que
  el color del rodar y de los i-frames se decide en `ascii_theme.py`.
- El rodar se dispara con el evento KEYDOWN, no con la tecla mantenida.
- Los i-frames se declaran como fracción de la duración del rodar
  (`ROLL_IFRAME_*_FRACTION`), de modo que siguen siendo proporcionales si se reajusta.
- Tests de la Fase 2: `test_stamina` y `test_player_actions`.

Balance actual del movimiento (tile = 32 px):

| | px/s | x andar |
|---|---|---|
| Andar | 180 | 1,00 |
| Correr | 270 | 1,50 |
| Rodar (media) | 492 | 2,74 |
| Rodar (pico inicial) | 985 | 5,47 |

Fase 3a — ataque y enemigos con vida:
- `game/systems/combat.py`: `Box` (AABB con `overlaps()` y `from_entity()`),
  `attack_hitbox()` que coloca el rectángulo delante según la mirada, `apply_knockback()`
  y `resolve_player_attack()`. Sin pygame.
- `game/entities/enemy.py`: los esqueletos del mapa pasan a ser entidades con `Health`,
  colisión con muros y parpadeo al encajar un golpe. **Todavía no se mueven**: la IA es
  la Fase 3b. `Enemy.spawn_from_level()` los crea desde las marcas del mapa, así que el
  renderer ya no los dibuja como decorado.
- `Health` en `systems/stats.py`, junto a `Stamina`. El jugador también tiene vida,
  aunque aún nada se la quite.
- **Ataque ligero (J)**: cuesta estamina con la misma regla que el rodar (hace falta un
  resto mayor que 0, nunca queda negativa). Tres fases deducidas del tiempo
  (`AttackPhase`: WINDUP, ACTIVE, RECOVERY) en vez de estados aparte; la hitbox solo
  existe en ACTIVE. Atacando uno apenas se mueve (`ATTACK_MOVE_FACTOR`) y no cambia de
  rumbo; no se puede rodar hasta la recuperación, ni atacar rodando.
- Cada tajo golpea a cada enemigo **una sola vez**: los alcanzados se apuntan en
  `player.attack_hits`, que se vacía al empezar cada ataque.
- El cruce jugador-enemigos lo resuelve `combat.resolve_player_attack()` desde el bucle,
  no las entidades: así `Player.update()` no necesita conocer a los enemigos.
- Al golpear: daño, retroceso (sin atravesar muros) y fogonazo blanco. A vida 0 el
  enemigo desaparece de la lista.
- Barras de vida (roja) y estamina del jugador apiladas abajo a la izquierda, y barrita
  sobre cada enemigo herido. Tajo ASCII (`-`, `|`, `/`, `\`) delante del jugador durante
  la fase activa.
- **F1** activa el modo depuración: cajas de colisión en azul y hitboxes en rojo.
- `Level.move_with_collision()` trocea ahora el desplazamiento en pasos no mayores que
  un tile. Antes, un movimiento muy largo en un solo fotograma (un empujón fuerte)
  aterrizaba al otro lado de la pared sin comprobar las casillas que cruzaba.
- Tests: 104 en verde (se suma `tests/test_combat.py`).

Fase 3b — IA del esqueleto y daño al jugador:
- `EnemyState`: IDLE, CHASING, WINDUP, ATTACKING, RECOVERY, STUNNED, RETURNING. Un
  método por estado (`_update_idle`, `_update_chasing`...), todos con la misma firma,
  para que un tipo nuevo redefina solo el que le interese.
- `EnemyProfile`: dataclass con todos los números de un tipo (vida, velocidad, radios,
  tiempos del ataque, aturdimiento). Crear una variante es escribir un perfil; el
  esqueleto no redefine ningún método. `PROFILES` asocia carácter del mapa -> perfil.
- `Level.has_line_of_sight()`: trazado de rayo muestreando el segmento cada
  `SIGHT_RAY_STEP` de tile. Aproximado pero suficiente, y mucho más simple que un DDA.
- Detecta por radio **y** línea de visión. Se planta a `attack_range`, avisa en amarillo
  (`skeleton_windup`) durante `SKELETON_WINDUP`, golpea con la dirección **fijada al
  empezar el aviso**, y se queda vendido en la recuperación. Si te alejas del radio de
  abandono o te pierde de vista más de `ENEMY_SIGHT_GRACE`, vuelve a su sitio.
- **Aturdimiento**: un golpe tuyo cancela el aviso y lo deja `STUNNED`. Se controla con
  `can_be_stunned` por perfil, pensando en enemigos que no se interrumpan.
- **Daño al jugador**: `PlayerState.HURT`, retroceso, aturdimiento corto e
  invulnerabilidad (`PLAYER_HURT_INVULNERABILITY`) con parpadeo del `@`. Los i-frames
  del rodar y esa invulnerabilidad se consultan juntos en `is_invulnerable`;
  `is_roll_invulnerable` queda para el color del rodar. Cada ataque enemigo acierta una
  sola vez (`attack_has_hit`).
- `combat.separate_enemies()`: empuje suave que deshace solapamientos entre enemigos y
  contra el jugador, respetando muros. Al jugador no se le mueve: de los dos cede el
  enemigo.
- `GameState` (PLAYING / DEAD): al morir sale "HAS MUERTO" unos segundos. Lo que pasa
  después lo define la Fase 4.
- **F1** añade el radio de detección y el nombre del estado sobre cada enemigo.
- Tests: 133 en verde (se suman `tests/test_enemy_ai.py` y `tests/test_game_states.py`).

Primer nivel (`data/levels/nivel_01.txt`):
- Leyenda ampliada en el cargador: `A` arquero, `D` élite y `*` objeto. Los enemigos se
  guardan por **carácter** y es `PROFILES` en `enemy.py` quien decide el perfil.
- El élite usa el comportamiento del esqueleto con su propio bloque de `config.py`:
  260 de vida, 34 de daño, radios mayores, aviso más largo y mucho más difícil de
  interrumpir. Se dibuja en morado.
- Los objetos `*` son decorado azul; todavía no se recogen ni tienen efecto.
- `nivel_01.txt` (64x72 tiles, 2048x2304 px) es el nivel por defecto: 6 esqueletos,
  1 arquero, 1 élite, 1 hoguera y 5 objetos. `test.txt` y `test_big.txt` se mantienen
  para los tests.
- Tests: el nivel es válido, está cerrado por muros, todo su suelo es alcanzable desde
  el `@` (inundación) y todo carácter de enemigo tiene perfil.

Esqueleto arquero (`A`) y proyectiles:
- `game/systems/projectiles.py`: `Projectile` (posición, dirección, velocidad, daño y
  quién lo disparó) y `update_projectiles()`. Vuela troceando el paso en medios tiles,
  así que no atraviesa paredes finas por rápido que vaya. Al acertar desaparece, de modo
  que golpear una sola vez sale solo. Sin pygame.
- Si el objetivo es invulnerable (i-frames del rodar o el respiro tras un golpe), la
  flecha **le atraviesa sin consumirse**: esquivar es esquivar.
- `game/entities/archer.py`: `Archer` hereda de `Enemy` y solo redefine cómo se coloca
  y qué hace al acabar el aviso. Mantiene las distancias (retrocede si te acercas a
  menos de `ARCHER_MIN_DISTANCE`, se aproxima si estás fuera de `ARCHER_SHOOT_RANGE`),
  tensa el arco más tiempo que el esqueleto, dispara **adonde apuntaba al empezar a
  tensar** y respeta un tiempo mínimo entre flechas. Acorralado, le queda un golpe
  cuerpo a cuerpo flojo. Muere en 2 golpes ligeros.
- El `sprite_id` de la flecha es genérico (`"arrow"`); qué carácter le toca según su
  dirección lo decide el renderer en `draw_projectile()`, no la lógica.
- **F1** dibuja además la trayectoria prevista mientras el arquero tensa.
- Tests: 157 en verde (se suma `tests/test_archer.py`).

Fijado de objetivo (lock-on):
- `game/systems/targeting.py`: `LockOn` (fijar, soltar, ciclar y mantenimiento por
  fotograma) y funciones puras de selección. Sin pygame.
- **Tab** fija al enemigo válido —vivo, dentro de `LOCK_ON_RADIUS` y con línea de
  visión— con mejor puntuación: la distancia penalizada por el ángulo respecto a la
  mirada (`LOCK_ON_FRONT_BIAS`), de modo que lo que está delante gana salvo que lo de
  atrás esté bastante más cerca. Con algo fijado, Tab lo suelta.
- **Flechas izquierda/derecha** recorren los candidatos ordenados por ángulo. La `y`
  crece hacia abajo, así que el ángulo crece en sentido horario en pantalla.
- **El jugador no sabe qué es un objetivo fijado**: `Intent` gana `look_at`, un punto
  del mundo. Si viene, la mirada apunta ahí y ni andar, ni rodar, ni atacar la pisan
  (`facing_is_locked`). WASD pasa a ser movimiento lateral, el rodar va hacia las
  teclas sin perder el encare y la hitbox del ataque sale hacia el objetivo.
- **Correr suelta el fijado**, como en Dark Souls.
- Se suelta solo al pasar de `LOCK_ON_BREAK_RADIUS` o al perder la vista más de
  `LOCK_ON_SIGHT_GRACE`. Si el objetivo muere o desaparece, salta al siguiente mejor
  candidato; si no queda ninguno, se suelta.
- La cámara sigue un punto desplazado hacia el objetivo (`camera_focus()`, con
  `LOCK_ON_CAMERA_BIAS`), sin dejar de centrarse en el jugador.
- ASCII: el objetivo se dibuja entre corchetes, `[s]`.
- Tests: 180 en verde (se suma `tests/test_targeting.py`).

Fase 4 — almas, muerte y mancha de sangre:
- `Souls` en `systems/stats.py`: guarda el total real y un `shown` que lo persigue, de
  modo que el contador de la HUD sube rodando en vez de saltar (`SOULS_COUNTER_*`).
  Se ve abajo a la derecha.
- Cada perfil de enemigo trae sus `souls` y un `respawns`. El esqueleto da 30, el
  arquero 55 y el élite 300. Las almas se cobran en `Game.collect_the_dead()`, al
  retirar a los caídos, así que da igual cómo hayan muerto.
- **Reaparición selectiva**: cada enemigo lleva su `spawn_index`. Al morir uno con
  `respawns=False` (el élite) su índice va a `defeated_for_good` y `spawn_from_level()`
  lo salta para siempre. Los demás vuelven enteros y en su sitio.
- **Muerte**: sale "HAS MUERTO" en rojo, la acción se detiene y tras
  `DEATH_SCREEN_DURATION` el jugador reaparece. No se recrea: `Player.revive()` lo
  restaura en su `respawn_point`, que de momento es el `@` del mapa y en la Fase 5
  moverán las hogueras.
- **Mancha de sangre** (`entities/bloodstain.py`): nace en el instante de morir —así se
  ve ya durante el cartel— con todas las almas que llevabas, y el contador queda a 0.
  Solo puede haber una: morir otra vez destruye la anterior para siempre. Morir con 0
  almas no crea mancha pero sí borra la vieja. Se recoge con **E** a menos de
  `BLOODSTAIN_PICKUP_RADIUS`. Si caes en un muro o encima de un enemigo,
  `Bloodstain.drop()` la coloca en la casilla libre más cercana
  (`Level.nearest_free_tile()`, por anillos). Se dibuja como `&` verde parpadeante.
- `GameState` pasa a tener un `update` por estado, listo para sumar el menú de hoguera
  y la pausa. `start_level()` (partida nueva) y `respawn_player()` (morir) son cosas
  distintas.
- Tests: 205 en verde (se suma `tests/test_souls.py`).

Decisiones y pendientes:
- La hoguera sigue siendo decorado dibujado desde los datos del nivel; los esqueletos ya
  son entidades.
- Los esqueletos no patrullan: en reposo se quedan quietos en su sitio. La patrulla
  por rutas se verá cuando haga falta.
- La estamina se actualiza al principio del fotograma, antes de resolver la acción. Por
  eso basta con que haya un resto —aunque sea el que acaba de regenerarse— para rodar.
- `level.py` importa `config` para conocer el tamaño de tile, así que arrastra pygame de
  forma indirecta (por las constantes de teclas). Sigue sin dibujar nada.
- Sigue sin haber máquina de estados del juego; el bucle solo distingue "ejecutándose" o no.

Siguiente paso: Fase 5 (hogueras: descanso, reaparición de enemigos, Estus y menú de
subida de nivel). La hoguera moverá `player.respawn_point` y `Souls.spend()` ya está
listo para pagar los niveles.
