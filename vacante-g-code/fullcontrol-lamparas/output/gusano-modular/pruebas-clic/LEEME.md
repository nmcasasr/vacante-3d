# Pruebas del clic: Gusi Ø95

Tres piezas cortas: el hombro y el labio de un módulo Ø95 con las dos bolitas
del clic. Se prueban contra un módulo Ø95 **ya impreso**, que se apoya encima:
su boca es la misma de siempre.

| pieza | cuánto sale la bolita | traba por lado | tiempo* |
|---|---|---|---|
| `prueba_labio_D95_clic0.8` | 0.7 mm | ~0.1 mm: casi sólo roce | ~18 min |
| `prueba_labio_D95_clic1.1` | 1.05 mm | ~0.45 mm | ~18 min |
| `prueba_labio_D95_clic1.4` | 1.4 mm | ~0.8 mm: firme | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

La traba es lo que la bolita sobresale por encima del juego de 0.6 mm que hay
entre la boca y el labio. La primera capa del módulo sale aplastada y se mete un
poco hacia adentro, así que en la realidad traba algo más que el número.

Son tramos exactos del módulo. Comparado contra el módulo entero con clic, la
bolita queda a la misma altura sobre el anillo de la boca, con menos de 0.1 mm
de diferencia: lo que se siente en la prueba es lo que va a dar el módulo.

Las bolitas van enfrentadas, una en +X de la cama y otra en −X. Miden ~6 mm de
ancho y ~3 mm de alto, y arrancan justo encima del anillo de la boca.
Verificador: 0 % de línea fina, sin puentes.

**Qué mirar:**

- si hace clic;
- si el módulo de arriba se sostiene al levantar la prueba;
- si sale con un tirón razonable;
- si las bolitas salieron limpias, sin hilos ni colgados debajo.

**Lo que no se puede:**

- **Una bolita más petisa.** El radio no puede crecer más de ~0.6 mm por
  vuelta: cada vuelta sube 0.8 y, si se corre más, ya no apoya en la de abajo.
  Con 1.1 mm de bolita eso da dos vueltas de subida y dos de bajada.
- **Sin juego vertical.** Entre el tope del anillo y la altura donde la bolita
  ya agarra quedan ~0.9 mm. El módulo puede subir eso antes de trabar.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 0.8 1.1 1.4

Y el módulo entero con el clic que gane, compatible con los ya impresos:

    python gen_gusano_modular.py 95 --solo-modulos --clic 1.1
