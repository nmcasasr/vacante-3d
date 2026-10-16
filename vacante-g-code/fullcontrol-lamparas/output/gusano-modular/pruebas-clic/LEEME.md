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

## Ronda 3: sólo bases nuevas (la boca de la ronda 2 sirve)

La ronda 2 quedó **muy suelta con los tres huecos**: la base bailaba de lado y
la cuña no trababa. La boca no cambia; se imprimen sólo bases, que tardan
~6 min cada una:

| pieza | base más angosta | juego de costado (simulado) |
|---|---|---|
| `prueba_boca_D95_clic1.05_cierra0.3` | 0.3 mm | ~0.4 mm |
| `prueba_boca_D95_clic1.05_cierra0.45` | 0.45 mm | ~0.3 mm |
| `prueba_boca_D95_clic1.05_cierra0.6` | 0.6 mm | ~0.1 mm |

(La ronda 2, `prueba_boca_D95_clic1.05`, tenía ~0.7 mm.)

Toda la boca de la base es **más angosta, pareja**, para que la pared no tenga
lugar de irse de lado. Creo que por eso no trababa: con 0.7 mm libres, el
labio se ovala bajo las dos cuñas y las deja pasar. La simulación no lo ve
porque trata las piezas como rígidas.

La cuña **mide lo mismo en total** (1.0 mm hacia adentro desde la boca
original), así que entra en los huecos de la boca de la ronda 2 con el mismo
juego de antes: 0.02, 0.07 y 0.12 mm. Al estar más angosta, la base apoya un
poco más arriba en el hombro (~0.3-0.4 mm); con cuña pasaba lo mismo. Las
tres pasan el verificador: 0 % sin apoyo.

Si la de 0.6 no entra, o hay que forzarla, la buena está entre esa y la de
0.45. Para el módulo entero, el mismo cierre va en su base y se apaga en las
vueltas de arriba, ~0.1 mm por vuelta.

    python gen_gusano_modular.py 95 --prueba --boca-adentro 1.05 --boca-cierra 0.3 0.45 0.6 --labio 7.6

## Qué imprimir (ronda 2)

| pieza | qué es | tiempo* |
|---|---|---|
| `prueba_boca_D95_clic1.05` | **la base**: las primeras vueltas del módulo, con las dos cuñas | ~6 min |
| `prueba_labio_D95_muescas0.3_0.35_0.4` | **la boca**: el hombro y el labio del módulo, con tres pares de muescas | ~19 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

**La boca trae tres muescas**, en mm hacia adentro. Como la base tiene dos
cuñas enfrentadas, cada una es un par enfrentado, uno cada 60°. Mirando la
pieza en la cama, desde adelante:

    adelante y atrás                     0.35 mm
    adelante-derecha y atrás-izquierda   0.40 mm   (la más floja)
    adelante-izquierda y atrás-derecha   0.30 mm   (la más justa)

(en ángulos: 90°/270° → 0.35, 150°/330° → 0.40, 30°/210° → 0.30)

**Marcar la de adelante con un punto de marcador antes de sacarla de la
cama.** Para probar, se gira la base hasta que sus cuñas caigan en un par, y se
pasa al siguiente.

## Qué cambió desde la ronda 1

La ronda 1 (en `ronda1/`) imprimió bien, pero no trababa: la cuña quedaba
chica para cualquiera de las muescas. Simulado con los cordones de los dos
g-code, la base se podía **levantar 3 mm y girar hasta 4 mm sin que la cuña
tocara nada**. Las muescas eran mucho más grandes que la cuña: de 4 vueltas
de alto y 8 mm de ancho, contra una cuña en punta que sólo llegaba a fondo en
1 mm de sus 6.

Ahora:

- **La cuña es más grande:** plana, 1.0 mm hacia adentro en 3.4 mm de ancho.
  Antes era una punta de 0.95.
- **Las muescas son más chicas:** de 0.30 a 0.40 de hondo (antes 1.2 a 1.6),
  de 7 mm de ancho (antes 8) y del alto de la cuña. Con la base apoyada, la
  cuña ocupa **una sola vuelta del labio**, la primera entera. La segunda
  vuelta de la base ya se abrió y no llega, así que la muesca es esa vuelta a
  fondo y la de arriba, que vuelve en rampa.
- **Menos juego.** Simulado:

  | muesca | juego entre cuña y muesca | se levanta sin tocar | gira sin tocar |
  |---|---|---|---|
  | ronda 1 (las tres) | 0.13-0.31 mm | más de 3 mm | hasta 4 mm |
  | 0.30 | 0.02 mm | 0.7 mm | ~1.5 mm |
  | 0.35 | 0.07 mm | 0.7 mm | ~1.5 mm |
  | 0.40 | 0.12 mm | 0.8 mm | ~1.5 mm |

Las muescas dan menos que la cuña porque entre las dos piezas ya hay 0.72 mm
de juego. La cuña se mete 0.3 mm en la pared del labio, contra 0.2 antes, y
eso es lo que cede para que pase al bajar: **ese es el clic**.

**Por qué no más hondas:** donde el hombro se vuelve labio, esa vuelta ya
se corre 0.77 mm, y la cuña cae justo en la siguiente. Una muesca de 0.40 ahí
corre esa vuelta hasta 0.71, lo mismo que el hombro, que sale bien. Más honda,
volvería a quedar en el aire y a salir derretida hacia adentro.

**La base queda ~0.4 mm más alta que sin clic.** Pasaba igual en la ronda 1:
la cuña apoya en esa última vuelta del hombro. Es así con cualquier cuña que
llegue a trabar, porque la muesca no puede bajar al hombro.

**La prueba de la boca es el módulo.** Antes la pieza corta arrancaba media
vuelta corrida respecto del módulo entero, justo donde va la muesca. Ahora
arranca 3.38 mm debajo del labio, y sus vueltas caen donde las del módulo con
una diferencia de 0.01 mm. La muesca de 0.35 del módulo da lo mismo que la de
la prueba.

Verificador: las dos piezas son imprimibles. La boca tiene 0.04 % de muestras
sin apoyo y un tramo al aire de 3.7 mm; la base, 0 %.

**Qué mirar:**

- si baja con un clic o hay que forzarla;
- si una vez abajo no gira, porque la cuña está en la muesca;
- si se sostiene al levantar la boca;
- si sale con un tirón razonable.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 0.3 0.35 0.4 --boca-adentro 1.05 --labio 7.6

Y el módulo entero con la que gane, ahora **con las cuñas abajo y las muescas
arriba** (antes `--clic` sólo ponía las muescas):

    python gen_gusano_modular.py 95 --solo-modulos --clic 0.35 --boca-adentro 1.05 --labio 7.6

`ronda1/` salió del commit `e5882dd`; con el código de ahora no se regenera
igual.
