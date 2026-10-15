# Pruebas del clic: Gusi Ø95

El clic es **llave y cerradura**:

- **la base** de cada módulo, la parte de abajo, lleva **dos cuñas hacia
  adentro** en sus dos primeras vueltas, las que se apoyan en la cama;
- **la boca**, la parte de arriba, lleva **dos muescas hacia adentro** en el
  mismo ángulo. Son el lugar donde caen las cuñas del módulo de arriba cuando
  está apoyado.

Las dos van en +Y y −Y de la cama, así que dos módulos apilados como salen de
la cama quedan alineados. Fuera de las cuñas y las muescas, cada pieza es
**punto por punto el módulo original**, costuras incluidas.

| pieza | qué es | tiempo* |
|---|---|---|
| `prueba_boca_D95_clic1` | **la base**: las primeras vueltas del módulo, con las dos cuñas de ~0.85 mm | ~6 min |
| `prueba_labio_D95_muescas1.2_1.4_1.6` | **la boca**: el hombro y el labio del módulo con base chica, con las tres profundidades de muesca | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

**La boca trae las tres profundidades**, en mm hacia adentro. Como la base
tiene dos cuñas enfrentadas, cada profundidad es un par enfrentado, uno cada
60°. Mirando la pieza en la cama, desde adelante:

    adelante y atrás                     1.4 mm
    adelante-derecha y atrás-izquierda   1.6 mm
    adelante-izquierda y atrás-derecha   1.2 mm

(en ángulos: 90°/270° → 1.4, 150°/330° → 1.6, 30°/210° → 1.2)

**Marcar la de adelante con un punto de marcador antes de sacarla de la
cama:** después no hay cómo distinguirlas a ojo, son 0.2 mm de diferencia.
Para probar, se gira la base hasta que sus cuñas caigan en un par, y se pasa
al siguiente.

Las muescas van **sólo en el labio**, desde donde arranca para arriba. El
hombro, la parte de la esfera, queda liso.

**Entran y salen en rampa.** La primera versión entraba de un salto: la vuelta
donde arranca el labio se metía 1.2-1.6 mm respecto de la de abajo, más que el
cordón (1.2), quedaba en el aire y se imprimía derretida hacia adentro. Arriba
volvía igual de golpe. Ahora la pared se corre como mucho 0.55-0.60 mm por
vuelta (lo mismo que el hombro, que sale bien): dos vueltas de bajada, una o
dos a fondo y tres de subida. El labio de la prueba mide **7.6 mm** (dos
vueltas más que los 6 de antes) para que arriba de la muesca queden 2-3 vueltas
lisas y el borde no quede pegado a ella. Medido en el g-code:

| vuelta del labio | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| muesca de 1.2 | 0.36 | 0.91 | 1.20 | 1.20 | 0.95 | 0.40 | 0 | 0 | 0 | 0 |
| muesca de 1.4 | 0.45 | 1.00 | 1.40 | 1.40 | 1.26 | 0.71 | 0.16 | 0 | 0 | 0 |
| muesca de 1.6 | 0.54 | 1.09 | 1.60 | 1.60 | 1.56 | 1.01 | 0.46 | 0 | 0 | 0 |

Verificador: muestras sin apoyo de 0.83 % a 0.07 %, tramos al aire de 20 a 1.

La rampa de abajo no cambia dónde asienta la base: la cuña entra sólo
~0.25 mm más que el juego, y ya en la primera vuelta del labio la muesca
tiene 0.36 o más. La de arriba sí cambia el tope: ya no es un escalón sino una
rampa de ~35°, que es la que tiene que subir la cuña para salir.

## Cómo funciona, según la simulación

Apoyé la base sobre la boca con los cordones reales de los dos g-code:

- **Al bajar, la cuña roza el labio ~0.23 mm.** El juego entre base y labio es
  0.6 y la cuña entra 0.85. Para pasar, el plástico tiene que ceder esas
  décimas, y al llegar abajo la cuña cae en la muesca: **ese es el clic**.
- **Ya abajo, la base queda 0.4 mm más alta que sin clic.** La cuña está en
  las dos primeras vueltas de la base, y la de más abajo apoya en el borde del
  hombro, justo debajo de donde arranca el labio y la muesca.

La simulación es rígida y en un corte, así que no sabe cuánto cede el PETG:
eso lo dice la prueba.

**Qué mirar:**

- si baja con un clic o hay que forzarla;
- si una vez abajo no gira, porque la cuña está en la muesca;
- si se sostiene al levantar la boca;
- si sale con un tirón razonable.

Verificador: las dos dan 0 % de línea fina y puentes de 4.6 mm como máximo.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 1.2 1.4 1.6 --boca-adentro 1.0 --labio 7.6

Y el módulo entero con la profundidad que gane:

    python gen_gusano_modular.py 95 --solo-modulos --clic 1.4 --labio 7.6

(`--labio 7.6`: el módulo con el mismo labio que la prueba; la base no depende
del labio y sale igual con 6 o 7.6.)
