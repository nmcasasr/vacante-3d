# Pruebas del clic: Gusi Ø95

Piezas cortas para probar el clic de Gusi Ø95 en minutos. Se prueban de a
dos: **la boca encima de un labio**.

- **`prueba_boca_D95`** — la parte de abajo de un módulo: sus primeras 4
  vueltas, lisa (la boca no cambia con el clic). ~6 min.
- **`prueba_labio_D95_clicN`** — la parte de arriba de un módulo: el hombro y
  el labio con las dos bolitas, con una base chica para que se pare.

Se apoya la boca sobre cada labio y se elige el que mejor cierra. La boca
también se puede reemplazar por un módulo Ø95 ya impreso: es la misma.

| labio | cuánto sale la bolita | traba por lado | tiempo* |
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
- si la boca se sostiene al levantar el labio;
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
