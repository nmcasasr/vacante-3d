# Pruebas del clic: Gusi Ø95

Piezas cortas para probar el clic de Gusi Ø95 en minutos, sin imprimir
módulos enteros (~1 h cada uno). Se prueba **boca clic contra labio clic**.

| pieza | qué es | tiempo* |
|---|---|---|
| `prueba_boca_D95_clic1` | la base: la parte de abajo del módulo, igual a la original, con dos cuñas de ~0.85 mm **hacia adentro** sólo en las **dos primeras vueltas** (las que se apoyan en la cama) | ~6 min |
| `prueba_labio_D95_clic0.8` | la boca: la parte de arriba del módulo, hombro y labio con base chica, con dos bolitas **hacia afuera** de 0.7 mm | ~18 min |
| `prueba_labio_D95_clic1.1` | ídem, bolitas de 1.05 mm | ~18 min |
| `prueba_labio_D95_clic1.4` | ídem, bolitas de 1.4 mm | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

Las cuñas van enfrentadas y miden ~6 mm de ancho. Las de la boca van en +Y y
−Y de la cama. Fuera de las cuñas, la boca es punto por punto la del módulo
original, costuras incluidas. Las bolitas del labio van en el mismo ángulo
(+Y y −Y), así que dos módulos apilados como salen de la cama quedan
alineados. Arrancan justo encima de donde se apoya el anillo de la base y
ocupan 4 vueltas; fuera de ellas el labio es punto por punto el original. Los labios son tramos exactos del módulo: comparados contra el
módulo entero con clic, la bolita queda a la misma altura, con menos de
0.1 mm de diferencia.

## Cómo probar

Apoyar la boca sobre cada labio de dos maneras:

- **con las protuberancias alineadas**, la de la boca encima de la del labio:
  la de la boca tiene que pasar por encima de la del labio y quedar trabada
  debajo;
- **giradas 90°**: cada protuberancia aprieta contra la pared lisa de la otra
  pieza.

Qué mirar: si hace clic, si la boca se sostiene al levantar el labio, si sale
con un tirón razonable, y si las protuberancias salieron limpias.

Ojo con la boca: sus protuberancias caen a la altura del hombro curvo del
labio. Si la boca queda levantada sobre ellas y cabecea, en vez de bajar hasta
apoyarse, el problema es ese.

## Lo que no se puede

- **Una bolita de labio más petisa.** El radio no puede crecer más de ~0.6 mm
  por vuelta: cada vuelta sube 0.8 y, si se corre más, ya no apoya en la de
  abajo.
- **Que el clic del labio no tenga juego vertical.** Entre el tope del anillo
  de la boca y donde la bolita ya agarra quedan ~0.9 mm.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 0.8 1.1 1.4 --boca-adentro 1.0
