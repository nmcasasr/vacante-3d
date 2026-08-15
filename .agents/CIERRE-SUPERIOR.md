# Cerrar la parte de arriba sin que se hunda

Hallazgos del 12-08-2026. **Nada de esto está probado en impresión todavía** —
son mediciones sobre el g-code más lo que publicó el autor de la pieza de
referencia. Cuando se pruebe, lo que sobreviva se pasa a `SKILL.md` y `MAPA.md`
y este archivo se borra.

Fuente: *"Can You Print a Fully Enclosed Shape Without Sagging?"*, Claywoven —
el mismo autor del `Squeezy Fidget Toy.gcode` que usamos como referencia. El PDF
está en `~/Downloads/Claywoven _ Publicaciones _ Patreon.pdf`.

## Lo que él probó, y qué falló en cada intento

Imprimió la misma forma cerrada tres veces cambiando una cosa por vez:

| intento | qué hizo | qué salió |
|---|---|---|
| 1 | 20 mm/s constante en toda la pieza | **se hunde la punta**: el cabezal pasa por encima cuando el material todavía está blando |
| 2 | bajar a 4 mm/s hacia el centro | **sobre-extrusión**: a poca velocidad el plástico se endurece antes de que la boquilla lo desplace, y queda un bulto |
| 3 | ver abajo | casi perfecto |

Los dos fallos son opuestos, y eso importa: **el problema no se arregla con "más
lento" a secas**. Hay una ventana.

## Las cuatro cosas del intento que funcionó

1. **Darle una inclinación LEVE a la tapa.** No dejarla plana.
   > *"When the enclosed section is completely flat, it becomes much harder to
   > get the layers to stack correctly. The pattern has to work within a very
   > small vertical space, making the toolpath more difficult to control."*

2. **Cortar el patrón antes de llegar al centro.** A medida que las pasadas se
   juntan, el material de cada una es una fracción cada vez mayor del área que
   queda, y la sobre-extrusión se vuelve incontrolable.

3. **Bajar la velocidad hacia el centro con un GRADIENTE, no un escalón.** Lo
   pinta con aerógrafo sobre los vértices; el mínimo es **0.18 × la velocidad
   normal** (3.6 mm/s sobre 20). El intento 2 falló por bajar de golpe a 4; el 3
   funciona con el mismo valor mínimo pero llegando gradualmente.

4. **Declarar la boquilla un poco MÁS GRANDE que la real** (0.82 contra 0.8).
   > *"Overextrusion seems better than underextrusion so the newly printed layer
   > adheres better to previous layer."*

Y como dato de proceso: capa de **0.81 mm** con boquilla de 0.8 — coherente con
los 0.800 de separación que ya medimos en su g-code.

## Cómo estamos nosotros (medido sobre `hongo_squeezy.gcode`)

    z        radio    dr/dz    inclinación   velocidad
    29.61    26.69    -0.68      55.7°       7.0 mm/s
    33.61    23.12    -1.04      44.0°       7.0 mm/s
    36.61    19.22    -1.47      34.2°       7.0 mm/s
    38.61    15.35    -2.12      25.3°       7.0 mm/s
    39.61    12.52    -2.83      19.4°       7.0 mm/s
    40.61     7.81    -4.71      12.0°       7.0 mm/s
    41.11     4.99    -5.58      10.2°       7.0 mm/s
    41.61     4.73    -3.08      18.0°       7.0 mm/s

Tres diferencias concretas con lo que él recomienda:

- **Velocidad constante hasta la punta.** 7.0 mm/s de la primera vuelta a la
  última. Eso es literalmente su intento 1, el que se hunde. Y es justo el
  tramo donde el usuario ve el hundimiento.
- **La tapa termina casi plana.** 10.2° en el último milímetro. Él avisa que
  plano es el caso difícil y que hay que darle inclinación a propósito.
- **La extrusión no se reduce hacia el centro.** Área constante 0.960 mm² hasta
  el final, cuando el área disponible se achica hasta un círculo de Ø9.4 mm.

## Lo raro de nuestra parte de arriba

La pieza **no cierra**: termina en radio 4.68 mm, o sea un agujero de **Ø9.4 mm**.
Eso sale de la silueta del DXF (`hongis.dxf`, z 124.4..241.0 da radio
20.38 → 4.68 a escala 0.35). El cráter que se ve en el preview no es un defecto
del generador: es la forma que pedimos.

Pero tiene dos consecuencias que sí son nuestras:

- Las últimas vueltas corren a 10-12° de inclinación con el cordón entero y a
  velocidad plena. Es el peor caso de los tres factores a la vez.
- El corrimiento por vuelta en esa zona llega al **68.5 % del ancho de cordón**
  (z 40-44), por encima del 55 % que `SKILL.md` pone como límite sano. Squeezy
  en sus cúpulas se queda en 64.8 % pero **con la velocidad bajando**.

## Qué probar, en este orden

Una cosa por vez, y midiendo. El artículo es explícito en que dos de los tres
ajustes por separado empeoran la pieza.

1. **Rampa de velocidad hacia el ápice.** Ya tenemos la herramienta:
   `--velocidad-en ALTURA:MM_MIN`. Para la chica, con 420 mm/min de base, el
   0.18 del artículo da ~76 mm/min en el centro. Empezar a bajar donde la
   inclinación cruza los ~30° (z ≈ 37) y llegar al mínimo en el borde del
   agujero (z ≈ 41).
   **Ojo**: `hongo_latest` ya trae una rampa (900/600/380 en z 95/106/112) y
   `hongo_squeezy` NO la trae — la sacamos cuando se pidió velocidad constante.
   La pieza chica que se hunde es justamente la que quedó sin rampa.

2. **Reducir el área de extrusión en las últimas vueltas.** Hoy es constante.
   Es el punto 2 de él, y ataca el bulto que aparece cuando uno solo baja la
   velocidad.

3. **Inclinación de la tapa.** Es lo más invasivo porque toca la silueta, que
   viene del DXF. Antes de tocarla, ver si 1 y 2 alcanzan.

## Lo que NO hay que hacer

- **Bajar la velocidad de golpe.** Es su intento 2 y produce el bulto. El
  gradiente es la parte que hace que funcione, no el valor mínimo.
- **Asumir que la pieza grande se comporta igual.** El ángulo de la tapa es el
  mismo (la escala no cambia ángulos), pero el radio del agujero pasa de 4.7 a
  13.4 mm y la velocidad de 7 a 16 mm/s. Los dos factores empujan en contra.

## Preguntas abiertas

- ¿El 0.18 es transferible? Su baseline es 20 mm/s con boquilla 0.8; el nuestro
  es 7 mm/s. Puede que lo que importe sea el tiempo por vuelta y no el factor.
- No sabemos si su "cortar el patrón antes del centro" tiene equivalente en
  nuestra geometría, que no tiene patrón en estas piezas.
