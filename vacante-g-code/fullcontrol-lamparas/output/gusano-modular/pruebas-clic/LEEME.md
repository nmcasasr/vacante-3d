# Pruebas del clic: Gusi Ø95

Piezas cortas para probar el clic de Gusi Ø95 en minutos, sin imprimir
módulos enteros (~1 h cada uno). Se prueba **boca clic contra labio clic**.

| pieza | qué es | tiempo* |
|---|---|---|
| `prueba_boca_D95_clic1` | la parte de abajo del módulo: **3 vueltas planas** con dos protuberancias de ~0.9 mm **hacia adentro**, y después la espiral de siempre | ~6 min |
| `prueba_labio_D95_clic0.8` | la parte de arriba del módulo, hombro y labio con base chica, con dos bolitas **hacia afuera** de 0.7 mm | ~18 min |
| `prueba_labio_D95_clic1.1` | ídem, bolitas de 1.05 mm | ~18 min |
| `prueba_labio_D95_clic1.4` | ídem, bolitas de 1.4 mm | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

Las protuberancias van enfrentadas y miden ~6 mm de ancho. Las de la boca van
en +Y y −Y de la cama, y **sólo en las vueltas planas**: anillos a z fija (0.80,
1.24 y 1.68) apilados antes de que arranque la espiral, que es contra lo que
se hace el clic. El módulo liso tiene una sola vuelta plana; esta lleva tres
para que la protuberancia quede más alta. Las del labio van en +X y −X. Las del labio arrancan justo encima de donde se apoya el anillo
de la boca. Los labios son tramos exactos del módulo: comparados contra el
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
