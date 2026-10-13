# Árbol — la copa

La bola del hongo (`hongis.dxf`, espejada en la panza, paso adaptativo) cubierta
con los grumos del florero-kadzi que salen de una y se cuelgan
(`grumo-puentea`). Sólo la copa: el tronco es el palo de la lámpara, que entra
por el hueco de abajo.

Todo es cordón **1.2 mm**, capa **0.8**, PETG a 240 °C, cama 70, ventilador 100,
8 mm/s con `puente_lento=0.35` en la punta.

## Los cupones

**La carpeta dice CÓMO está hecho. El nombre del archivo dice CON QUÉ NÚMEROS.**

Los dos son la misma bola **Ø80 x 59 mm** (`--perfil-escala 0.45`), hueco abajo
Ø20, boca arriba Ø12, con los mismos cinco largos. Cambia cómo se ordenan los
grumos:

- **`1-cupones/intercalado/largos_1.2a9mm`** — EL QUE VA. **3 vueltas lisas + 1
  con patrón**, como la matera, y cada fila de grumos corrida media púa
  respecto de la anterior: cada grumo cae entre los dos de abajo, al
  tresbolillo. **72 púas en TODAS las filas.** Filas cada ~3.2 mm. ~1.8 h.
- `1-cupones/columnas/largos_1.2a9mm` — el primer intento: 2 + 1, grumos
  apilados en columnas como el florero. Queda de comparación.

### Por qué 72 púas fijas, y no una cantidad que siga al radio

La primera versión intercalada (la que se imprimió) cambiaba la cantidad de
púas en 12 bandas para que el paso quedara parejo, y **falló justo en los
cambios de banda**: con n abajo y n+Δ arriba la diferencia de fase crece con el
ángulo, así que la fila queda intercalada en un lado de la bola y apilada en el
otro. Medido con `verificar_intercalado.py`:

| versión | en el medio | apilados |
|---|---|---|
| bandas a mano (la impresa) | 70.9 % | 14.2 % |
| cantidad por radio, cada fila armada desde la de abajo | 86.1 % | 6.6 % |
| **72 fijas** | **99.1 %** | **0.4 %** |

Si la cantidad cambia entre filas, **siempre** quedan grumos encima: cada grumo
que se agrega tiene que pasar por arriba de uno de abajo en algún lado. Con la
cantidad fija cada fila es exactamente la de abajo corrida media púa, y el
99.1 % es 100 % en todas las filas salvo la primera (los grumos están naciendo
en la rampa de `desde`) y el borde de arriba.

Lo que cuesta: el paso sigue al radio, como los meridianos de un globo.
Ecuador (r 40) 3.5 mm, r 24 → 2.1 mm, r 17 → 1.5 mm. Por debajo de ~1.5 mm se
funden, así que el patrón se apaga en la tapa casi plana de arriba
(`hasta=0.95`); abajo ya arranca en `desde=0.03`.

**Los largos van en GAJOS alrededor de la bola, no en bandas a lo alto.** En una
bola cada altura es otra situación —abajo voladizo, en el medio pared parada,
arriba cierre—, y con bandas cada largo caería en una sola. En gajos cada largo
recorre las tres.

    gajo 1  (0–72°)     1.2 mm   sólo el fondo: la referencia
    gajo 2  (72–144°)   3.2 mm
    gajo 3  (144–216°)  5.1 mm
    gajo 4  (216–288°)  7.1 mm
    gajo 5  (288–360°)  9.0 mm

El ángulo 0 es +X de la cama y crece antihorario visto desde arriba. El corte
entre gajos es duro a propósito: tiene que poder leerse "el tercero sirve y el
cuarto no".

En `columnas/` la cantidad sí sigue al radio, en 12 bandas
(`barrido_puas=45,68,83,90,97,99,98,93,83,70,50,35`); sin intercalar no importa.

Verificador, los dos: línea fina 0.00 % · peor puente 11.3–11.9 mm (el tope es 12) ·
contacto ~12 % — el mismo número que `florero-kadzi/1-cupones/grumo-puentea`:
es el grumo colgando, buscado. Dan NO IMPRIMIBLE por eso y sólo por eso.

Los tiempos son por recorrido x1.4 y salen cortos; el de Orca al laminar es el
bueno.

**Qué mirar al imprimirlo:** qué largo se lee como follaje y no como púa; si en
la mitad de abajo (voladizo) los grumos cuelgan como cordones o se caen; y si
arriba, donde la copa cierra casi plana, los grumos se ven o se aplastan.

### `1-cupones/velocidades/grumo9mm_punta3a8`

Del cupón de largos el que más gustó fue el de 9 mm, así que esto va con
**grumos de 9 mm en toda la bola**. Misma bola y misma densidad que el
intercalado (72 púas, 3 + 1). Lo liso va a **16 mm/s** (como el hongo
impreso) y el grumo a **8** en todo el cupón; lo único que cambia por gajo es
la PUNTA:

    gajo 1  (0–60°)     punta 3 mm/s   la de siempre: la referencia
    gajo 2  (60–120°)   punta 4        la de Squeezy, la mitad del grumo
    gajo 3  (120–180°)  punta 5
    gajo 4  (180–240°)  punta 6
    gajo 5  (240–300°)  punta 7
    gajo 6  (300–360°)  punta 8        sin frenado extra: igual que el grumo

El ángulo 0 es +X de la cama y crece antihorario visto desde arriba. ~1.8 h.
Verificador: línea fina 0.00 %, peor puente 9.9 mm, contacto 17 % (más que el
de largos porque acá todos los grumos miden 9). Intercalado 99.1 %. Sin pausas.

**Por qué la punta y no el grumo.** En la copa real de 9 mm (lo liso a 16):

| | punta 3 | punta 4 | punta 6 | punta 8 |
|---|---|---|---|---|
| grumo 8 | 23.0 h | 19.9 h | 16.8 h | 15.2 h |
| grumo 16 | 21.0 h | 17.9 h | 14.8 h | 13.3 h |

La punta ahorra ~8 h, el grumo ~2. Con punta 3, grumo 8 y liso 16 la punta se
lleva el **54 % del tiempo** (12.5 h de 23): 96 m de recorrido lento en ~19 700
puntas, ~5 mm cada una. No es sólo el extremo: el grumo tiene pocas muestras,
el movimiento que LLEGA a la punta arranca a media subida, y el `F` vale para
todo ese movimiento. O sea que hoy media subida de cada grumo va a 3 mm/s —así
eran también los floreros, y es lo que funcionó—.

Sin el 1.4 de aceleración y todo a 8 mm/s, la copa grande era ~29.6 h; pasar
lo liso a 16 ya la deja en 23. Con 150 púas y 5 lisas entre filas (menos
densa, intercalado 100 %) va de ~10.8 h (punta 3) a ~7.6 h (punta 8, grumo 16).
Ojo, abrir más el paso no siempre ahorra: con 110 púas tardaba MÁS que con 150,
porque la ocupación es fracción del paso y cada grumo se hace más ancho.

## `2-copas/` — los tamaños del hongo, para ver el tiempo

Las dos medidas del hongo, con la técnica del cupón intercalado (3 + 1, cantidad
fija, el patrón apagado en la tapa con `hasta=0.95`) y UN solo largo por pieza:

- **`copa_D245_grumoNmm`** — el tamaño de `hongo_latest`, el impreso: escala
  1.38, corte en 109.2, espejo, hueco Ø65. **Ø244 x 183 mm.** 221 púas.
- **`copa_mini_grumoNmm`** — el tamaño de `hongo_mini`: escala 0.35, corte en
  124.4, hueco Ø11.55. **Ø62 x 41 mm.** 56 púas.

La cantidad de púas escala con el tamaño (72 x escala / 0.45) para que el
espacio entre grumos sea el del cupón.

| pieza | 3 mm | 6 mm | 9 mm | el hongo liso |
|---|---|---|---|---|
| Ø244 (real) | ~16.3 h | ~22.9 h | ~29.6 h | `hongo_latest` ~4.9 h |
| Ø62 (mini) | ~1.0 h | ~1.3 h | ~1.6 h | `hongo_mini` ~1.5 h |

Estimados por recorrido x1.4: salen cortos, el de Orca es el bueno. Ojo al
comparar con el hongo: `hongo_latest` va a **16 mm/s** y las copas a **8**, la
velocidad de Squeezy que usa todo lo de grumos. A la misma velocidad el hongo
liso sería ~9.8 h, así que los grumos le suman entre 6.5 h (3 mm) y 20 h (9 mm).

**El tiempo lo domina el viaje de los grumos**, no la pared: cada mm de largo
suma ~2.2 h en la grande. Las palancas, de más a menos efecto: el largo del
grumo, la cantidad de púas (paso más abierto), más vueltas lisas entre filas, y
subir la velocidad de las vueltas lisas al 16 mm/s del hongo (frenando sólo en
el grumo).

Verificador (las de 6 mm): línea fina 0.00 % las dos, peor puente 8.4–8.5 mm.
Contacto 15.5 % la mini y 18.8 % la grande, contra el ~12 % del cupón: es el
grumo colgando, pero en la grande es más. Intercalado: 99.2 % la mini, 99.7 % la grande.

## Lo que hizo falta en el código

`--pendiente-silueta` ahora gobierna también la MARCHA adaptativa, no sólo la
extrusión. Sin eso la marcha leía cada grumo como pared acostada y achicaba la
subida hasta el piso: el primer intento salió con cordón de 1.2 x 0.223, 19 %
de línea fina y puentes de 130 mm. Ninguna receta vieja cambia: las 114 que
usaban la opción son de paso fijo y no pasan por la marcha (comprobado con
`matriz`; el hongo sale byte a byte igual).

`puas.py`, todo apagado por defecto (las recetas viejas salen byte a byte
iguales: matriz, largos_3a9mm, velocidad, matera60_romo_piso_kadzi, hongo):

- `intercalar=1` arma cada fila con patrón desde la de abajo: sus púas arrancan
  en los puntos medios de las de abajo. Con la cantidad fija eso es media púa
  exacta. Si la cantidad cambia (`barrido_puas`, `paso_mm`) agrega o saca
  púas de a una, repartidas y rotando con el ángulo de oro; es lo mejor que se
  puede con cantidad variable (86 %), y por eso el árbol va con cantidad fija.
- `grumo_lento` frena el cuerpo del grumo (ida y vuelta) aparte de la punta,
  para subir la velocidad de la pieza sin subir la del grumo.
  `gajos_grumo`/`gajos_punta` hacen lo mismo por gajo alrededor de la pieza.
- `paso_mm` saca la cantidad de púas de cada fila del radio. Queda para quien
  prefiera el paso parejo al intercalado perfecto.
- Con `banda_por_vuelta=1` la cadencia cuenta VUELTAS de verdad y las bandas
  de `barrido_puas`/`barrido` se leen en el `t` real donde arranca el ciclo.
  En la bola hace falta: con paso adaptativo las vueltas no suben lo mismo, y
  `vuelta x dt_capa` no es la altura.

## `3-mini-lampara/` — la copa con hueco de Ø83.5

La técnica del cupón intercalado con **grumos de 9 mm en toda la pieza** y un
**hueco libre de Ø83.5** en el piso, para que asiente sobre la base. Lo liso a
16 mm/s, el grumo a 8, la punta a 3 (`grumo_lento=0.5`, `puente_lento=0.1875`).
La cantidad de púas sigue al tamaño (72 x escala / 0.45), así que el paso es
2.79 mm en todas.

El hueco no cabe en la bola del cupón (Ø80, piso Ø24): hay que agrandarla y
cortarla más arriba, cerca de la panza. Dos familias:

- **`mini_`**: bola cortada abajo de la panza, todavía se cierra un poco hacia el piso.
- **`media_`**: media esfera, cortada un poco por debajo de la panza. Pared casi
  recta abajo y cúpula arriba. Menos altura, menos tiempo.

| pieza | escala · corte | alto | piso (vueltas alrededor del hueco) | tiempo |
|---|---|---|---|---|
| `media_D92` | 0.52 · 163 | 41 mm | Ø90.6 (2.7) | ~2.0 h |
| `media_D97` | 0.55 · 160 | 45 mm | Ø95.0 (4.9) | ~2.5 h |
| `media_D106` | 0.60 · 160 | 49 mm | Ø103.6 (9.1) | ~2.9 h |
| `mini_D97` | 0.55 · 150 | 50 mm | Ø90.7 (2.8) | ~2.9 h |
| `mini_D106` | 0.60 · 140 | 61 mm | Ø91.5 (3.2) | ~3.5 h |
| `mini_D124` | 0.70 · 128 | 79 mm | Ø92.2 (3.5) | ~5.2 h |

Tiempos por recorrido x1.4; el de Orca es el bueno. Verificador, las seis:
línea fina 0.00 %, peor puente 11.2–11.8 mm, contacto 18–21 % (el grumo
colgando, como en el cupón de velocidades). Intercalado 100 %.

**`lento_alcance=subida`, nuevo.** Con `"punta"` lo que se frena dependía de
dónde caía la rejilla de muestras contra el grumo: en esta misma receta iba de
0.5 mm por grumo (la bola Ø97) a 8 mm (la Ø124), y los tiempos no se podían
comparar. `"subida"` frena la ida entera y la meseta, y la vuelta va a 8:
~9 mm a 3 mm/s por grumo en todas. Es lo más parecido a "media subida
lenta", que es como salían los floreros. El cupón de velocidades regenerado
sale idéntico.

`--capas-transicion 0`: la mezcla de las primeras capas dejaba un puente de
67 mm a z 2.1 en la media esfera más chica, igual que en la matera de
corazones.

## `4-lampara-puck/` — la media esfera que tapa una lámpara puck

**`puck_D86_grumo9mm`** encierra una lámpara puck de Ø83.2 x 18 mm: piso
macizo y una **pausa de 20 s al terminar la capa 16** (z 12.0, como la muestra
Orca) para meterla. ~1.4 h "por F" (el tiempo "por F" coincide con el de Orca
en los `.gcode.3mf` laminados).

- **Piso**: disco macizo de 0.8 mm (sin `--piso`), con pie de 2.4 mm
  (`--base-borde`). La lámpara apoya en z 0.8.
- **Pausa** (`--pausa 12.0:20`): retrae, sube 10 mm, corre el cabezal a X10 y
  adelanta la cama, espera 20 s y vuelve sola. OJO: en ese momento la lámpara
  (hasta z 18.8) asoma ~7 mm por encima de la boquilla, que pasa a ~1 mm de su
  borde. Pedida así.
- **Zócalo** (`--zocalo 20`): cilindro recto, liso, a **20 mm/s**. Por dentro
  Ø84.6.
- **Cúpula**: el hongo espejado (corte 174, escala 0.4855), 32.5 mm. En total
  52.5 mm. 78 púas, grumos de 9 mm, 3 + 1, punta frenada en la subida.
- **Ventanas**, alturas desde la mesa con el piso sumado:
  - switch en **0°**: z 8.3–14.9, 16 mm de ancho (el techo a 15.3 dejaba un
    puente de 12.8 mm; a 14.9, 11.75).
  - micro USB en **180°**: z 5.8–13.8, 13 mm de ancho.
  Al meter la lámpara, el switch va hacia +X de la cama.

**Cómo sube (`--p giro_fila=25`): espiral pura en TODA la pieza.** Ninguna
vuelta tiene escalón: el mayor salto de z entre dos puntos seguidos es 0.05 mm.
Cada fila de grumos es exactamente UNA vuelta (una capa en Orca), arranca en un
valle y tiene sus 78 grumos. Lo único que deja la espiral es que el último
grumo de la fila queda una capa más arriba que el primero; ese punto gira 25
púas (115°) por fila, así que no forma una línea. Las 3 lisas absorben el giro
estirándose a 1.1 vueltas: su espesor baja a ~0.72, sin escalón, y las filas
siguen a 3.2 mm.

Por qué no capas planas (era `--escalon 0.7`, commit bf65c9e): con una sola
línea continua, cada tramo de 360° tiene que subir lo que mide la capa —el
espesor en un punto es lo que subió la boquilla en la vuelta anterior—. Una
fila 100 % plana sube todo en un solo lugar, y las vueltas de arriba y de abajo
tienen que subir en ese mismo lugar o el espesor se va a 0.16 / 1.4 mm. Por eso
salía la costura alineada con escalones. Plana y sin costura no existe; sin
escalón, la fila sube de a poco.

Medido: filas de 78 grumos, cada una en una vuelta, arranques a 115° uno del
otro. Espesor 0.8 en el zócalo, 0.7–0.8 en las filas y lisas de abajo, y baja
en la cúpula como siempre (paso adaptativo). Verificador: línea fina 0 %, peor
puente 11.75 mm, contacto 11.4 % (igual que antes). La versión plana, la media
`media_D92` y el cupón de velocidades regenerados salen idénticos.

`verificar_pieza.py` ahora mide el contacto entre CENTROS de cordón. Antes
usaba la distancia entre trayectorias con el alto promedio de los dos cordones,
que da bien sólo si los dos altos son iguales. Con caudal punto por punto
daba por suelto un cordón de 1.2 apoyado en uno de 0.6. Sobre las piezas
viejas cambia el contacto en 0.1 punto y los puentes no se mueven.
