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
| Q | Beber Estus |
| E | Interactuar (hoguera, puertas) |
| Esc | Pausa |

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
- [ ] **Fase 2**: estamina y rodar con invulnerabilidad.
- [ ] **Fase 3**: enemigo básico (patrulla, persigue, ataque con aviso previo), ataque del jugador, vida y muerte de enemigos.
- [ ] **Fase 4**: almas, muerte del jugador y mancha de sangre.
- [ ] **Fase 5**: hogueras (descanso, reaparición de enemigos, Estus) y menú de subida de nivel.
- [ ] **Fase 6**: HUD completo y pantalla de "HAS MUERTO".
- [ ] **Fase 7**: más tipos de enemigos, puertas y atajos, primer jefe.
- [ ] **Fase 8**: guardado de partida.
- [ ] **Fase 9**: sustituir el ASCII por sprites o tiles.

## Estado actual

**Fases 0 y 1 terminadas.**

Hecho en la Fase 0:
- Entorno virtual en `.venv/`, `requirements.txt` (pygame-ce 2.5.8, pytest 9.2.0) y `.gitignore`.
- `main.py` + `game/game.py`: ventana de 960x540 y bucle a 60 FPS con `dt` en segundos,
  que se cierra con Esc o con la X.
- `game/config.py`: tamaño de tile, FPS, ventana, rutas, controles y balance del jugador.
- `game/render/`: interfaz `Renderer`, `AsciiRenderer` (glifos monoespaciados cacheados)
  y `ascii_theme.py` (glifos y colores por `sprite_id`).

Hecho en la Fase 1:
- `game/entities/entity.py`: clase base con posición continua en float (el centro de la
  caja), tamaño y `sprite_id`, con los bordes `left/right/top/bottom` como propiedades.
- `game/entities/player.py`: el jugador nace en el `@` del mapa, se mueve con WASD a
  `PLAYER_SPEED` px/s multiplicado por `dt` y normaliza la diagonal para que no sea
  más rápida.
- `Level.move_with_collision()`: colisión AABB contra los muros resolviendo **un eje
  cada vez**, de modo que al empujar en diagonal contra una pared el jugador se desliza
  por ella en vez de quedarse clavado. `Level` conoce ahora su `tile_size` y expone
  `pixel_width`/`pixel_height` y `tile_center()`.
- `game/render/camera.py`: sigue al jugador y se recorta a los bordes del mapa; si el
  mapa cabe entero en la ventana, lo centra. Es aritmética pura, sin pygame.
- El renderer dibuja solo los tiles visibles y recibe la cámara; los enemigos pasan a
  rojo en `ascii_theme.py`.
- `data/levels/test_big.txt`: cuatro salas unidas por pasillos, 56x32 tiles
  (1792x1024 px), más grande que la ventana. Es el nivel por defecto.
  `data/levels/test.txt` se mantiene como la sala pequeña que usan los tests.
- Tests: 34 en verde entre `tests/test_level.py`, `tests/test_player.py` y
  `tests/test_camera.py`.

Decisiones:
- La hoguera y los esqueletos siguen siendo decorado dibujado desde los datos del nivel;
  todavía no son entidades.
- `level.py` importa `config` para conocer el tamaño de tile, así que arrastra pygame
  de forma indirecta (por las constantes de teclas). Sigue sin dibujar nada.
- Sigue sin haber máquina de estados; el bucle solo distingue "ejecutándose" o no.

Siguiente paso: Fase 2 (estamina y rodar con invulnerabilidad).
