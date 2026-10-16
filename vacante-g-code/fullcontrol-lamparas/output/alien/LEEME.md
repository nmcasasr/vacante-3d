# Lámpara alien: el cuerpo

El platillo con la cúpula (`cuerpo_alien.stl`, en `gcodes/reference/alien/`),
en **una sola línea**, con la receta del hongo: pared lisa sobre el perfil del
STL, piso con hueco y capas que se adaptan a la inclinación.

| pieza | medidas | tiempo* |
|---|---|---|
| `cuerpo_alien.gcode` | Ø251.7 × 125 mm, hueco abajo de Ø100 | ~2.7 h |

| `chiqui_alien_40.gcode` | la misma pieza al 40 %: Ø100.7 × 50 mm, hueco de Ø40 | ~27 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

**El chiqui** es la prueba del grande. Las capas son las mismas en mm y las
pendientes también, así que cada vuelta se corre lo mismo que en el grande y
pasa por las mismas partes difíciles: el asiento, los dos conos, el ala, el
escalón debajo de la cúpula y la punta. Lo que no prueba es el enfriamiento:
las vueltas del grande son 2.5 veces más largas, así que cada una tiene más
tiempo para enfriarse antes de que le apoye la siguiente. Verificador:
imprimible, 0.02 % sin apoyo, el peor tramo al aire 3.9 mm.

En la cama va de X 2.1 a 253.9: entra con 2 mm de margen. La línea de purga
del frente queda debajo del ala, que pasa 37 mm más arriba.

## Cómo sale cada parte

El perfil es un platillo simétrico arriba y abajo, con la cúpula encima:

- **El asiento de abajo** (de r50 a r78 en los primeros 7 mm, casi
  horizontal). El primer tramo es el piso: un anillo plano de Ø100 a Ø110
  sobre la cama. Después las vueltas salen muy bajas y se corren 0.76 mm hacia
  afuera, cada una apoyada un tercio sobre la de abajo. Ahí la pieza queda
  hasta ~3 mm más angosta que el STL y lo alcanza a los ~30 mm de alto.
- **Los dos conos del platillo** (~58° desde la vertical): capas de ~0.42 mm
  que se corren ~0.68 por vuelta, lo mismo que el hombro del Gusi.
- **El ala** (Ø251.7, a 37 mm): casi vertical, capas de 0.76.
- **El escalón debajo de la cúpula** (de r80 a r50 entre 67 y 75 mm, casi
  horizontal): igual que el asiento, vueltas bajas que se meten 0.76 mm cada
  una. Sale como un redondeo un poco más suave que el del STL, hasta ~4 mm
  más afuera en el último milímetro.
- **La cúpula**: cierra arriba como la del hongo y la del gusanito, hasta un
  agujerito de ~3 mm en la punta.

Verificador: imprimible. 0 % de línea fina, 0 % de muestras sin apoyo y
ningún tramo al aire. Con capa máxima 0.8 aparecía un tramo "al aire" de
19 mm en el ala: es el límite del criterio (0.8 sobre 0.8 da contacto justo
1.0) y con 0.76 desaparece, a costa de 16 vueltas más.

El generador avisa que donde el radio se corre 0.76 por vuelta el solape es
del 37 %: es lo mismo que el hongo, impreso con esta receta (sin ventilador
hasta el 89 % de la altura).

## Generar de nuevo

El chiqui es el mismo comando con `--perfil-escala 0.4 --piso 40 --nombre alien/chiqui_alien_40`.

    python -m lamparas.bowls zigzag --perfil ../gcodes/reference/alien/cuerpo_alien.stl --piso 100 --piso-refuerzo 0 --altura-capa 0.76 --ancho-linea 1.2 --material PETG --temperatura 245 --velocidad 960 --ventilador 0 --ventilador-desde 0.89 --p mascara=ninguna --p amplitud=0 --p dientes=0 --segmentos 240 --nombre alien/cuerpo_alien
