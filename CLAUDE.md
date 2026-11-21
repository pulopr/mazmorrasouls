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
| `+` | Puerta |

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
  - [ ] **3b**: IA del esqueleto (patrulla, persigue, ataca con aviso) y daño al jugador.
- [ ] **Fase 4**: almas, muerte del jugador y mancha de sangre.
- [ ] **Fase 5**: hogueras (descanso, reaparición de enemigos, Estus) y menú de subida de nivel.
- [ ] **Fase 6**: HUD completo y pantalla de "HAS MUERTO".
- [ ] **Fase 7**: más tipos de enemigos, puertas y atajos, primer jefe.
- [ ] **Fase 8**: guardado de partida.
- [ ] **Fase 9**: sustituir el ASCII por sprites o tiles.

## Estado actual

**Fases 0, 1, 2 y 3a terminadas.**

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
- `data/levels/test_big.txt` (56x32 tiles, cuatro salas con pasillos) es el nivel por
  defecto; `data/levels/test.txt` es la sala pequeña que usan los tests.

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

Decisiones y pendientes:
- La hoguera sigue siendo decorado dibujado desde los datos del nivel; los esqueletos ya
  son entidades.
- `is_invulnerable` y la vida del jugador ya funcionan, pero todavía nada le hace daño:
  se usarán en la Fase 3b.
- La estamina se actualiza al principio del fotograma, antes de resolver la acción. Por
  eso basta con que haya un resto —aunque sea el que acaba de regenerarse— para rodar.
- `level.py` importa `config` para conocer el tamaño de tile, así que arrastra pygame de
  forma indirecta (por las constantes de teclas). Sigue sin dibujar nada.
- Sigue sin haber máquina de estados del juego; el bucle solo distingue "ejecutándose" o no.

Siguiente paso: Fase 3b (IA del esqueleto: patrulla, persecución y ataque con aviso
previo, y daño al jugador).
