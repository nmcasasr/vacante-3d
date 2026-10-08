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
| `prueba_labio_D95_clic1.2` | **la boca**: el hombro y el labio del módulo con base chica, muescas de 1.2 mm | ~18 min |
| `prueba_labio_D95_clic1.4` | ídem, muescas de 1.4 mm | ~18 min |
| `prueba_labio_D95_clic1.6` | ídem, muescas de 1.6 mm | ~18 min |

\* Calculado sobre el recorrido; el que da Orca es el bueno.

**El número es qué tan honda es la muesca**, en mm hacia adentro. Las tres
cubren el mismo lugar: el final del hombro, que es donde cae la cuña con el
módulo apoyado. El labio arranca ~1 mm más arriba.

## Cómo funciona, según la simulación

Apoyé la base sobre la boca con los cordones reales de los dos g-code:

- **Al bajar, la cuña pisa el labio ~0.23 mm.** El juego entre base y labio es
  0.6 y la cuña entra 0.85. Para pasar, el labio o la base tienen que ceder
  esas décimas, y al llegar abajo la cuña cae en la muesca: **ese es el clic**.
  Si no cede, la base queda apoyada arriba del labio.
- **Muescas de 0.8 y 1.0 no alcanzaban:** la cuña quedaba ~1.9 mm más alta,
  apoyada en el hombro, porque ahí el hombro todavía se está abriendo.
  Recién con **1.2** la cuña cabe y la base asienta donde siempre. Por eso
  las pruebas van de 1.2 a 1.6.

La simulación es rígida y en un corte, así que no sabe cuánto cede el PETG:
eso lo dice la prueba.

**Qué mirar:**

- si baja con un clic o hay que forzarla;
- si una vez abajo no gira, porque la cuña está en la muesca;
- si se sostiene al levantar la boca;
- si sale con un tirón razonable.

Verificador: las cuatro dan 0 % de línea fina y puentes de 4.6 mm como
máximo.

## Generar de nuevo

    python gen_gusano_modular.py 95 --prueba --clic 1.2 1.4 1.6 --boca-adentro 1.0
