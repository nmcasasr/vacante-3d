# Gusi: las 18 piezas finales, para sacar costos

Son todas las piezas que ofrece el creador de la web: **3 tamaños (Ø60, Ø150,
Ø244) x 3 patrones (lisa, árbol, zigzag) x módulo y tapa**. Cada una tiene su
g-code, su `.params.json` (el comando que la rehace) y su verificación en
`verif/`. Los costos están en `costos.csv` (una fila por pieza) y en
`costos_presets.csv` (las tres pilas de la web).

Todo lo genera `gen_gusi_finales.py` (en `fullcontrol-lamparas/`):

    python gen_gusi_finales.py                         # las 18, verif/ y los CSV
    python gen_gusi_finales.py 150 --patron zigzag     # sólo esas
    python gen_gusi_finales.py --solo-costos           # rehace los CSV y verif/apilado.txt

## Qué es cada pieza

Todas son el **gusano universal** (`vacante-3d-gusanito`, rama
`gusanito-grande`, `output/gusano-universal/`): la misma boca abajo (r 19.215,
Ø38.4) y el mismo labio arriba (r 17.415, 6 mm de alto), hombro de 70° y
holgura de 0.6. Por eso encastran en cualquier orden. En esta rama
`siluetas.gusano_modulo` todavía no tiene `cuello` ni `hombro`, así que el
script lleva una copia de la función de la otra rama (`gusano_universal`) y la
registra al correr. No se tocó ningún archivo de la librería.

- `modulo_D{60,150,244}_{patron}`: el lóbulo con el labio arriba.
- `tapa_D{60,150,244}_{patron}`: el lóbulo cerrado en cúpula. La Ø60 va
  cerrada y la Ø150 y la Ø244 abiertas al 20 % (bocas de Ø30 y Ø49).

**Las lisas son exactamente las del gusano universal.** En las seis, el
cuerpo del g-code (todo lo que no es comentario) es idéntico instrucción por
instrucción a su par de `gusano-universal/`, y dan los mismos tiempos y gramos
que su LEEME (0.4, 0.4, 2.5, 2.4, 6.5 y 6.4 h; 11, 12, 84, 84, 227 y
224 g).

## Los patrones

Los dos salen de `lamparas/bowls/puas.py` (el de esta rama, que es el más
nuevo). Las piezas con patrón usan la misma silueta, capa (0.8), cordón (1.2)
y marcha que la lisa. Lo que cambia:

| | lisa | árbol | zigzag |
|---|---|---|---|
| generador | `zigzag` sin dientes (la receta del universal) | `puas` | `puas` |
| de dónde sale | `gusano-universal/` | `arbol/` (cupón de velocidades, mini lámpara, puck) | `florero-kadzi/1-cupones/grumo-crece/largos_1.2a3.6mm` (el cupón impreso) |
| cadencia | — | 3 vueltas lisas + 1 con grumos | 3 lisas + 3 con turupe |
| cómo sale | — | el grumo sale de una y se cuelga (`crecer=0`) | el turupe crece en sus 3 vueltas (`crecer=1`), siempre apoyado |
| filas | — | corridas media púa (tresbolillo), cantidad fija | corridas media púa entre bandas (el zigzag), cantidad fija |
| por vuelta | — | 54 / 135 / 144 | 96 / 192 / 192 |
| largo / alto | — | 3 / 7 / 9 mm | 1.2 / 0.9 / 0.9 mm |
| ocupación, filo | — | 0.30 / 0.30 / **0.20**, filo 0.34 | 0.30, filo 0.34 |
| velocidad | 8 mm/s | lisa 16, grumo 8, punta 3 (la subida entera frenada) | 8 mm/s |
| boquilla | 250 la primera capa, 245 | 250 y 240 (la de los cupones) | 250 y 240 |
| ventilador | 0 hasta el 89 % de la altura, después 100 | 0 en las dos primeras capas (z < 1.6), después 100 | ídem árbol |

Los números van por tamaño, Ø60 / Ø150 / Ø244.

**Dónde no hay patrón.** Es la misma regla que dibuja la web
(`gusi-geometria.ts`): no hay patrón donde el radio baja de **19.5 mm** (el
cuello y el labio, que quedan metidos en el módulo vecino) ni donde el paso
entre púas baja de **1.5 mm** (se funden). Con la cantidad fija, la segunda
regla manda en casi todos los casos:

| pieza | radio de corte | patrón entre z (de la silueta) | sup. con patrón | paso en el ecuador |
|---|---|---|---|---|
| árbol Ø60 | 19.5 | 0.9 – 30.4 (de 38.7) | 87 % | 3.49 mm |
| árbol Ø150 | 32.2 | 4.9 – 97.2 (de 109.5) | 90 % | 3.49 mm |
| árbol Ø244 | 34.4 | 6.0 – 169.4 (de 182.7) | 96 % | 5.32 mm |
| zigzag Ø60 | 22.9 | 4.0 – 27.4 (de 38.7) | 72 % | 1.96 mm |
| zigzag Ø150 | 45.8 | 11.5 – 91.6 (de 109.5) | 77 % | 2.45 mm |
| zigzag Ø244 | 45.8 | 10.4 – 165.0 (de 182.7) | 92 % | 3.99 mm |

Las z son las medidas en el g-code, no las pedidas. En las tapas el patrón
empieza igual y termina donde la cúpula baja del radio de corte.

## El encastre queda igual que en la lisa

Se mide sobre el g-code y no sobre la silueta, comparando cada punto contra la
lisa del mismo tamaño. Con `--pendiente-silueta` y sin la mezcla de las
primeras capas, la pieza con patrón sube exactamente igual que la lisa: las
mismas z, vuelta por vuelta.

- **La cara de adentro no cambia**: el punto más metido respecto de la lisa
  está a −0.003 mm en las 12 piezas con patrón. El patrón sale sólo hacia
  afuera.
- **La boca y el hombro no llevan relieve**: 0.00 mm en los primeros 2 mm de
  cada pieza y desde 2 mm por debajo del asiento hasta el labio. La excepción
  es el árbol Ø60, cuyo radio de corte es el de 19.5: sus grumos empiezan a
  0.9 mm de la boca y terminan 1.35 mm por debajo del asiento.
- **Apiladas no se tocan** (`verif/apilado.txt`). Se miden los 72 pares
  posibles (cualquier módulo abajo, cualquier pieza arriba) y la menor
  distancia vertical entre un grumo o turupe y el eje del cordón de la otra
  pieza es de **2.71 mm**: es el árbol Ø60 arriba de un Ø244. El mínimo para
  no tocarse es 0.8, un cordón. Para medir el peor caso cada fila cuenta como
  un anillo entero. Los "—" de esa tabla son pares en los que la otra pieza no
  llega al radio de los grumos (un Ø60 no pasa de r 30 y los grumos del Ø150
  arrancan en r 32), así que no se pueden tocar.

## Qué se ajustó respecto de la web (para que la web dibuje lo imprimible)

Los conteos y los largos de la web se mantienen: árbol {54, 135, 144} con
grumos de {3, 7, 9} mm, zigzag {96, 192, 192}. También quedan iguales la
cadencia, `RADIO_MIN` y `PASO_MIN`. Cambian dos cosas:

1. **El turupe del zigzag baja de 1.2 a 0.9 mm en el Ø150 y el Ø244.** Con
   1.2 mm el Ø60 sale IMPRIMIBLE (contacto 1.44 %; la referencia, Squeezy,
   tiene 1.88 %), pero el Ø150 da 1.94–1.99 % y el Ø244 2.40–2.51 %: NO
   IMPRIMIBLE. El turupe crece 0.4 mm por vuelta. Con un paso de 2.5 a 4 mm
   sus dos patas quedan separadas y cada una vuela sola, mientras que en el
   Ø60 (paso 1.96) se funden en un solo bulto. Se probó en el módulo Ø150:

   | variante | contacto | tiempo | material |
   |---|---|---|---|
   | 1.2 mm, 192 turupes (la web) | 1.94 % ✗ | 2.99 h | 103 g |
   | 1.2 mm, 240 turupes (paso 1.96, como el Ø60) | 1.53 % | 2.97 h | 102 g |
   | 1.2 mm, ocupación 0.24 | 1.15 % | 2.96 h | 102 g |
   | 1.2 mm, crece en 4 vueltas (cadencia 3 + 4) | 1.00 % | 3.03 h | 105 g |
   | **0.9 mm (éste)** | **0.94 %** | **2.83 h** | **98 g** |

   Se eligió 0.9 porque deja el mayor margen sin tocar la cadencia, el conteo
   ni el radio de corte. Con 240 turupes el radio de corte sube de 45.8 a 57.3
   y se pierde patrón. **En la web: `ALTO_KADZI` pasa a ser por tamaño,
   {60: 1.2, 150: 0.9, 244: 0.9}.**

2. **El grumo del árbol Ø244 ocupa el 0.20 del paso, no el 0.30.** En el
   cupón el paso es 3.49 mm y 0.30 deja un grumo de 1.05 mm de ancho. El Ø60
   y el Ø150 de la web caen en ese mismo paso, pero el Ø244 con 144 grumos
   queda en 5.32 mm: a 0.30 el grumo mide 1.6 mm y el contacto sube a 24.6 %,
   más que cualquier pieza de árbol laminada (12–21 %). En el módulo Ø244:

   | variante | contacto | puente | tiempo | material |
   |---|---|---|---|---|
   | 144 grumos, 0.30 (la web) | 24.6 % | 11.8 mm | 15.98 h | 470 g |
   | 216 grumos (paso 3.55, como el cupón), 0.30 | 19.9 % | 11.6 mm | 19.46 h | 541 g |
   | **144 grumos, 0.20 (éste)** | **16.5 %** | **11.6 mm** | **15.64 h** | **469 g** |

   0.20 x 5.32 = 1.06 mm, que es el mismo grumo del cupón, sólo que más
   espaciado. **En la web**, la gota del árbol del Ø244 tiene que ser más
   angosta en la misma proporción: su `medio` (hoy 0.32 del paso en los tres
   tamaños) pasa a ~0.21 en el Ø244. Ojo: el Ø244 de la web es **más ralo
   que el cupón** (5.3 mm entre grumos contra 3.5). Para que tenga la
   densidad del cupón hacen falta 216 grumos, que cuestan 3.8 h y 72 g más
   por pieza.

## Costos

`tiempo_h` es el del recorrido, el largo de cada movimiento dividido por su
F: es la misma cuenta del LEEME del gusano universal. `tiempo_h_mas35` le
suma el 35 % que suelen tardar de más las piezas reales. Ojo: con grumos el
recorrido son miles de segmentos cortos y la aceleración pesa más, así que en
el árbol el +35 % puede quedar corto. El LEEME del árbol usa x1.4 y avisa que
también sale corto; el de Orca al laminar es el bueno. Material: PETG de
1.75 mm a 1.27 g/cm³. `alto_mm` es la altura del g-code, o sea la de la
silueta más los 0.8 de la primera capa.

| pieza | alto | tiempo | +35 % | gramos | metros | veredicto |
|---|---|---|---|---|---|---|
| módulo Ø60 lisa | 39.5 | 0.35 h | 0.48 h | 11.5 | 3.76 | IMPRIMIBLE |
| tapa Ø60 lisa | 37.3 | 0.37 h | 0.50 h | 11.9 | 3.90 | IMPRIMIBLE |
| módulo Ø60 árbol | 39.5 | 0.42 h | 0.57 h | 15.9 | 5.19 | IMPRIMIBLE* |
| tapa Ø60 árbol | 37.3 | 0.44 h | 0.59 h | 16.3 | 5.34 | IMPRIMIBLE* |
| módulo Ø60 zigzag | 39.5 | 0.43 h | 0.58 h | 14.3 | 4.68 | IMPRIMIBLE |
| tapa Ø60 zigzag | 37.3 | 0.45 h | 0.61 h | 14.7 | 4.83 | IMPRIMIBLE |
| módulo Ø150 lisa | 110.3 | 2.46 h | 3.32 h | 84.3 | 27.58 | IMPRIMIBLE |
| tapa Ø150 lisa | 102.8 | 2.42 h | 3.26 h | 83.5 | 27.34 | IMPRIMIBLE |
| módulo Ø150 árbol | 110.3 | 6.08 h | 8.21 h | 177.2 | 58.01 | IMPRIMIBLE* |
| tapa Ø150 árbol | 102.8 | 6.09 h | 8.22 h | 176.4 | 57.76 | IMPRIMIBLE* |
| módulo Ø150 zigzag | 110.3 | 2.83 h | 3.82 h | 97.6 | 31.94 | IMPRIMIBLE |
| tapa Ø150 zigzag | 102.8 | 2.79 h | 3.76 h | 96.8 | 31.69 | IMPRIMIBLE |
| módulo Ø244 lisa | 183.5 | 6.51 h | 8.79 h | 226.7 | 74.23 | IMPRIMIBLE |
| tapa Ø244 lisa | 171.1 | 6.40 h | 8.64 h | 224.1 | 73.36 | IMPRIMIBLE |
| módulo Ø244 árbol | 183.5 | 15.64 h | 21.11 h | 469.2 | 153.61 | IMPRIMIBLE* |
| tapa Ø244 árbol | 171.1 | 15.51 h | 20.94 h | 465.3 | 152.32 | IMPRIMIBLE* |
| módulo Ø244 zigzag | 183.5 | 7.25 h | 9.79 h | 252.7 | 82.74 | IMPRIMIBLE |
| tapa Ø244 zigzag | 171.1 | 7.13 h | 9.63 h | 250.2 | 81.89 | IMPRIMIBLE |

### Las pilas de la web

| preset | piezas | tiempo | +35 % | gramos | metros | alto |
|---|---|---|---|---|---|---|
| **Gusanito** | 4 x módulo Ø60 lisa + tapa Ø60 lisa | 1.79 h | 2.41 h | 57.8 | 18.93 | 163 mm |
| **Árbol** | módulo Ø244 árbol + módulo Ø150 árbol + tapa Ø150 árbol | 27.81 h | 37.54 h | 822.9 | 269.38 | 381 mm |
| **Torre** | Ø150 zigzag + Ø60 zigzag + Ø150 zigzag + Ø60 zigzag + tapa Ø60 zigzag | 6.97 h | 9.40 h | 238.5 | 78.06 | 306 mm |

Alto de la pila = la suma de los pasos de los módulos más el alto de la tapa,
en el eje del cordón.

## Los veredictos

- **IMPRIMIBLE**: `verificar_pieza.py` lo da tal cual. Las lisas, con los
  números del gusano universal. Los zigzag tienen contacto de 0.94 a 1.49 %
  (la referencia es 1.88 %) y un peor puente de 1.0 a 1.4 mm.
- **IMPRIMIBLE\*** (las seis de árbol): `verificar_pieza.py` dice **NO
  IMPRIMIBLE**, y lo dice por el contacto y sólo por eso. Es el mismo caso que
  documenta `arbol/LEEME.md`: el grumo que sale de una y se cuelga está al
  aire a propósito. Las otras dos condiciones dan bien: línea fina 0.00 % y
  peor puente por debajo de los 12 mm (5.7 mm el Ø60, 9.7 el Ø150, 11.6 el
  Ø244). El contacto (11.1–12.9 % el Ø60, 18.4–18.7 % el Ø150, 16.5–16.9 % el
  Ø244) cae dentro de lo que dan las piezas de árbol laminadas: 12 % el
  cupón, 17 % el de velocidades, 18–21 % la mini lámpara y 13 % la puck. El
  puente del Ø244 (11.6 mm) es el que menos margen deja: queda pegado a los
  11.2–11.9 de los cupones.
- **Tresbolillo** (`verificar_intercalado.py`): 100 % en el medio en las seis
  de árbol. En las de zigzag da ~40 % en el medio y ~55 % apilados, y está
  bien así: ese medidor cuenta cada vuelta como una fila, y el turupe del
  zigzag ocupa 3 vueltas en la MISMA fase (crece apilado). Medido aparte por
  fase en el módulo Ø60: las bandas alternan 0.65 / 0.15 de púa, o sea media
  púa exacta entre una banda y la siguiente.
- **`verificar_tumbado.py`** (de la rama del gusano universal) da 82–84° en
  el árbol Ø150 y Ø244 abajo, cuando la lisa no pasa de 70°. Lo que mide no es
  la pared: el tumbado saca el radio medio de cada vuelta, y una vuelta con
  grumos de 7–9 mm tiene un radio medio mayor que la lisa de al lado. La
  silueta es la misma que la de la lisa (sus 70° valen) y las mismas z lo
  confirman.

## Lo que el verificador no ve

- **Nada de esto está impreso.** Las lisas son las del gusano universal, que
  tampoco se imprimió entero. Los grumos y turupes son técnicas de los cupones
  (árbol y florero) sobre una pared nueva.
- **El árbol Ø60 lleva grumos desde 0.9 mm sobre la cama**, con la pieza
  apoyada en un solo cordón de Ø38. Sus grumos de 3 mm son cortos, pero es la
  primera vez que van tan abajo.
- **El árbol imprime lo liso a 16 mm/s** (la receta de los cupones y de la
  puck), y la lisa a 8. Por eso el módulo Ø60 árbol tarda apenas 0.07 h más
  que el liso. Si se quiere el árbol entero a 8 mm/s, hay que esperar más
  tiempo en las grandes.
- **El zigzag de 0.9 mm no se probó en ningún cupón.** El impreso
  (`largos_1.2a3.6mm`) arranca en 1.2. Con 0.9 se lee menos.
- **El Ø244 árbol con grumos a 5.3 mm** también es nuevo: ningún cupón tuvo
  tanta separación.

## Qué imprimir primero

1. **Módulo Ø60 zigzag y módulo Ø60 árbol** (~25 min cada uno, 14–16 g).
   Sirven para ver si el turupe de 1.2 y el grumo de 3 mm se leen, si el
   árbol aguanta los grumos tan cerca de la cama y si encastran con un Ø60
   liso.
2. **Módulo Ø150 zigzag** (2.8 h, 98 g). Es el turupe de 0.9 y el que más
   lleva la Torre.
3. **Módulo Ø150 árbol** (6.1 h, 177 g). Grumo de 7 mm a la densidad del
   cupón.
4. Recién ahí, **el Ø244 árbol** (15.6 h, 469 g por pieza). Es el más caro y
   el que menos respaldo tiene, porque tiene el puente más largo y la
   separación nueva.

## Archivos

- `{modulo,tapa}_D{60,150,244}_{lisa,arbol,zigzag}.gcode` y `.params.json`:
  las 18 piezas. El `.params.json` y la cabecera de cada g-code traen el
  comando que la rehace (`python gen_gusi_finales.py --bowls ...`).
- `costos.csv`, `costos_presets.csv`.
- `verif/<pieza>.verif.txt`: `verificar_pieza`, `verificar_continuidad`,
  `verificar_tumbado` y, en las que tienen patrón, `verificar_intercalado`.
- `verif/<pieza>.gen.txt`: lo que dijo el generador.
- `verif/<pieza>.med.json`: los números de los CSV y del encastre.
- `verif/apilado.txt`: la distancia entre piezas apiladas, par por par.
