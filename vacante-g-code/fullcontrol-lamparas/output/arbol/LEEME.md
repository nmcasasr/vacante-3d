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
- `paso_mm` saca la cantidad de púas de cada fila del radio. Queda para quien
  prefiera el paso parejo al intercalado perfecto.
- Con `banda_por_vuelta=1` la cadencia cuenta VUELTAS de verdad y las bandas
  de `barrido_puas`/`barrido` se leen en el `t` real donde arranca el ciclo.
  En la bola hace falta: con paso adaptativo las vueltas no suben lo mismo, y
  `vuelta x dt_capa` no es la altura.
