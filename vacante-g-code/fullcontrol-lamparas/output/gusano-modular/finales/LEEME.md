# Gusi: las 12 piezas finales, para sacar costos

Son todas las piezas que ofrece el creador de la web: **2 tamaños (Ø150,
Ø244) x 3 patrones (lisa, árbol, zigzag) x módulo y tapa**. Cada una tiene su
g-code, su `.params.json` (el comando que la rehace) y su verificación en
`verif/`. Los costos están en `costos.csv` (una fila por pieza) y en
`costos_presets.csv` (las tres pilas de la web); de ahí salen los números de
`vacante/src/data/gusi-costos.ts`.

    python gen_gusi_finales.py                         # las 12, verif/ y los CSV
    python gen_gusi_finales.py 150 --patron zigzag     # sólo esas
    python gen_gusi_finales.py --solo-costos           # rehace los CSV y verif/apilado.txt

## Qué cambió (23-10-2026)

- **Sin Ø60.** Al lado de los grandes se leía como un cuello y no como un
  lóbulo. Las 18 piezas de antes, con él, están en `anteriores-cuello38/`
  con su LEEME (ahí está el detalle de los patrones, que no cambió).
- **El labio del Ø150 original.** El cuello común era el del Ø60 (r 19.215,
  Ø38.4) porque el chico mandaba. Ahora es el del módulo Ø150 del gusano
  modular (`../modulo_D150_92mm_labio6`): boca r 48.04 (Ø96.1), labio r 46.24
  (Ø92.5), 6 mm de alto, holgura 0.6, hombro de 70° como mucho. Los lóbulos
  ya no quedan unidos por un cuello de botella, y las piezas son más bajas:
  el Ø150 sube la pila 79.3 mm (antes 102.8) y el Ø244, 155.0 (antes 176.0).
- **El patrón** se apaga por debajo de r 48.3 (antes 19.5): ahí entra el
  labio del vecino. La web usa el mismo tope (`gusi-geometria.ts`).
- Los presets de la web: Gusanito = 4 módulos Ø150 lisos + tapa; Torre =
  244/150/244/150 + tapa Ø150 en zigzag; Árbol no cambia.

## Resultado

| pieza | Ø150 | Ø244 |
|---|---|---|
| módulo liso | 1.90 h · 66 g | 5.97 h · 209 g |
| tapa lisa | 2.13 h · 73 g | 6.11 h · 214 g |
| módulo árbol | 4.55 h · 135 g | 13.96 h · 424 g |
| tapa árbol | 4.70 h · 142 g | 14.04 h · 428 g |
| módulo zigzag | 2.24 h · 79 g | 6.69 h · 235 g |
| tapa zigzag | 2.47 h · 86 g | 6.83 h · 239 g |

Horas sobre el recorrido (lo real, ~35 % más) y gramos teóricos (1.27 g/cm³).

Todas IMPRIMIBLE salvo las de árbol, que son IMPRIMIBLE\* por el caso ya
documentado del grumo colgando (contacto contra las piezas de árbol
laminadas, 12–21 %). **El módulo Ø150 árbol queda justo en el tope: 21.0 %**
(antes 18.4): con el cuello más ancho el patrón cubre más panza de abajo,
donde más cuelga el grumo. Si sale mal, bajar `OCUPACION_ARBOL[150]` de 0.30
a 0.25, como se hizo con el Ø244.

Apilado (`verif/apilado.txt`): ningún par se toca; el más justo es un
zigzag Ø150 bajo un Ø244, 1.43 mm (se tocan por debajo de 0.8).
