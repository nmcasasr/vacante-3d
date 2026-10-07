# Matera Kadzi — la final

**`matera_kadzi.gcode`** · Ø50 × 50 mm · **66 min** · 18 g · IMPRIMIBLE · trazo
continuo · contacto 0.28 % · peor puente 0.47 mm · **57 % de solape**.

Cuatro hojas de piso a techo y el **isotipo de Kadzi abajo**, dibujado sobre la
rejilla de púas.

## Los números, todos atados entre sí

```
pieza       Ø50 × 50 mm, capa 0.4, cordón 1.2, PETG
56 púas     columna de 2.81 mm   <- 56 y no 60: ver abajo
hoja        14.02 mm = 5 columnas · vena 2.81 = 1 columna
            largo 44 + tallo 12 = 56 > 50, para que el corte lo haga la pieza
hueco       9 columnas entre hoja y hoja
patrón      9 × 9 · fila de 4.4 mm = (2 lisas + 9 con patrón) × 0.4
pico        0.8 mm de fondo, 3 mm en la figura · ocupacion 0.60, filo 0.50
```

**Por qué 56 púas y no 60.** Con 4 hojas, el centro del hueco cae en la púa
`puas/8`. Con 60 eso da **7.5** —entre dos púas— y el dibujo queda siempre medio
paso descentrado, sin arreglo posible moviéndolo. Con 56 cae en la púa 7 exacta.
El número de púas tiene que ser divisible por 8.

**Por qué el pico bajó a 3 mm.** Con el dibujo cayendo limpio en una sola púa las
transiciones se afilan: a 4 mm el solape se iba a **5 %**. A 3 mm vuelve a 31–57.

**Por qué `ocupacion=0.60` y no 0.30.** A 0.30 la púa mide 0.84 mm, menos que el
cordón de 1.2: sale un filo y chuza. A 0.60 mide 1.68 con una punta plana de
0.84 — una onda. Y no cuesta solape porque el pico es corto.

**Por qué `tomas=1`.** El promediado vertical deja púas a media altura en el
límite entre bandas. Sacándolo el logo queda limpio y el solape SUBE de 31 a 57.

**Por qué `suave_mm=2` y no 10.** La rampa de entrada y salida del patrón apaga
los primeros y últimos N mm. Con 10, la punta de la hoja y el tallo se
desvanecían y la hoja no llegaba ni al piso ni al techo.

## El dibujo se escribe, no se interpreta

```
--p patron="....0..../...000.../....0..../..0...0../.000.000./........./.0000000./..00000../...000..."
```

Un carácter por púa, una línea por fila, `/` las separa, `0` pone púa. La fila se
alinea sola a las bandas de la cadencia (`patron_fila0` dice en cuál arranca la
de abajo). Verificado: sale **81/81 caracteres** cuando la ventana de medición no
toca la hoja.

Esto existe porque un polígono muestreado NO es lo mismo que la rejilla: los
huecos del isotipo miden menos que una púa y el patrón se los come, así que el
logo salía como una mancha alta y pareja.

## El ruido: qué era y cómo se arregló

**`matera_kadzi_prueba2.gcode`** · 65 min · 17 g · IMPRIMIBLE · trazo continuo ·
contacto 0.27 % · peor puente 0.47 mm · **72 % de solape** (era 57).

El ruido alrededor del logo y la asimetría de la hoja eran **tres lecturas de la
máscara hechas en el lugar equivocado**, las tres de la misma familia: el dibujo
está cuantizado a celdas de púa × banda, pero se leía punto por punto.

```
--p peso_por_pua=1      la máscara se lee en el CENTRO de la púa
--p peso_por_banda=1    y una sola vez por banda, no por punto
--p banda_por_vuelta=1  y el número de vuelta viene de comun.py, no de floor(t)
```

**1. `peso_por_pua`** — el pulso de la púa `k` ocupa la fase `[k, k+ocupacion)`.
Leyendo el peso punto a punto, una púa sobre el borde del dibujo tiene sus
primeras muestras en el fondo y las últimas en la figura. Medido evaluando la
máscara al arranque, al centro y al final de cada púa: **20 de 56 púas partidas
a z=10 y 28 de 56 a z=25**.

El centro es `k + ocupacion/2` = 0.30, **no `k + 0.5`**. Con 0.5 la rejilla de
`patron` —que numera con `int(x + 0.5)`— devuelve la columna `k+1`, y el logo
sale corrido una columna entera. Ése fue el intento fallido anterior. Con 0.30
las dos numeraciones coinciden y no hace falta alinear nada más: se probó un
`patron_alineado` para quitarle el `+0.5` a la rejilla y da **0 diferencias**.

**2. `peso_por_banda`** — lo mismo en el otro eje. Una vuelta sube 0.4 mm, así
que el último cuarto de vuelta ya cae en la fila de arriba: el grumo apunta a
una figura hasta la mitad y a otra después. Es la objeción que el código ya le
hacía al barrido de amplitud, sin aplicarla a la figura. **Es el que más paga:
el salto radial por vuelta baja de 0.524 a 0.333 mm, o sea 57 % -> 72 % de
solape.**

**3. `banda_por_vuelta`** — `floor(t / dt_capa)` NO es el número de vuelta. `t`
sale de la marcha y el arranque de la pared no cae en un múltiplo exacto de la
altura de capa: medido, la parte fraccionaria vale **0.6012 en todas las
vueltas**, o sea que el índice cambia al **40 % de la vuelta —la púa 22 de 56—**
y no en la costura. Eso es un segundo escalón helicoidal en un ángulo fijo.
`comun.py` sabe el índice de verdad y ahora lo deja en `radio.capa_actual`.

Resultado sobre el dibujo: **316/324 -> 320/324 celdas correctas**, y las cuatro
copias del logo ahora son idénticas entre sí (la simetría de 4 es exacta).

## La asimetría de la hoja: era PARIDAD

**`matera_kadzi_prueba3.gcode`** · 65 min · 17 g · IMPRIMIBLE · trazo continuo ·
72 % de solape · logo **324/324** · asimetría de la hoja **0.00 mm**.

Los tres bultos que salían de un lado de la hoja y no del otro no eran ruido:
era que **la rejilla de muestreo no era simétrica respecto del eje de la hoja**.

Dos cosas más, encima de los tres arreglos de arriba:

```
--p patron_alineado=1   la celda de la púa k es [k, k+1), no [k-0.5, k+0.5)
--p giro_celdas=0.5     las hojas corridas media celda de púa
```

**El punto de lectura correcto es `k + 0.5`, no `k + ocupacion/2`.** La celda de
la púa `k` es la fase `[k, k+1)`; el pulso ocupa sólo `[k, k+ocupacion)` dentro
de ella. El espejo de `k+0.30` es `-k-0.30`, que no cae en ningún otro punto de
lectura: la rejilla de muestreo queda torcida. El espejo de `k+0.5` es
`(-1-k)+0.5`, que sí lo es. Medido sobre la máscara: **con 0.30 la asimetría
llega a 1.00; con 0.50 es 0.00 exacto.**

Mover la lectura a `k+0.5` obliga a `patron_alineado`: con la rejilla vieja ese
punto cae EXACTO sobre la frontera de `int(x + 0.5)` y el error de coma flotante
decide la columna púa por púa. Medido: el logo se desploma a **275/324** y las
cuatro copias dejan de coincidir. Con la celda alineada, `k+0.5` queda en su
centro, lo más lejos posible de cualquier frontera.

**Y la paridad, que es lo que faltaba.** Con la hoja centrada en un BORDE de
celda —donde cae sola, en `c/columnas · TAU`— ninguna celda es su propio espejo
(la 0 se refleja en la -1), así que la hoja cubre un número PAR de celdas y al
hueco le quedan PAR. El logo mide 9 columnas, impar: no encaja centrado nunca.
Corriendo la hoja media celda el eje pasa por el CENTRO de una celda, esa celda
es su propio espejo, y los dos números pasan a impares. De regalo el centro del
hueco cae exacto en el centro de la celda `kc`, que es donde va la columna del
medio del logo, así que el dibujo no hay que moverlo.

Resultado: logo **312 -> 324/324** y asimetría **1.96 -> 0.00 mm**.

## Las tres pruebas, para comparar

```
prueba1   57 % solape · logo 316/324 · asimetria 1.88 mm   (la que guardaste)
prueba2   72 % solape · logo 320/324 · asimetria 1.96 mm
prueba3   72 % solape · logo 324/324 · asimetria 0.00 mm   <- esta
```

## Cómo medir esto sin equivocarse

Tres mediciones dieron falsos negativos durante el diagnóstico:

- **Agrupar por franjas de Z** parte la vuelta a la fuerza (la espiral sube
  0.4 mm por vuelta) e inventa dos niveles donde hay uno.
- **Partir las vueltas en el ángulo 0** es falso: la costura está en la púa
  ~14.85, así que la copia del logo que cae antes de la costura pertenece a otra
  vuelta real. Hay que tomar cada púa con su propia Z.
- **Ajustar `t` contra la máscara** se desliza a otra fila del patrón y da un
  residuo bajo por el motivo equivocado.

La medición que sí sirve es evaluar la máscara directamente en el arranque, el
centro y el final de cada púa, y contar cuántas cambian de valor por dentro.

## Historial: el diagnóstico viejo (ya resuelto)

**Las púas del arranque de cada tira salen deformes**, y la hoja es asimétrica
(~1.45 mm entre su lado izquierdo y el derecho). Es el mismo defecto.

**La causa está identificada** (`bowls/puas.py`, función `radio`):

```python
amp = amplitud_fondo + (amp_de(...) - amplitud_fondo) * peso(angulo, t)
```

`peso` se evalúa **en el ángulo de cada punto del recorrido**, no por púa. Una
púa que cae sobre el borde del dibujo tiene sus primeras muestras leyendo el
fondo y las últimas la figura: sale mitad y mitad.

**El arreglo está implementado pero NO funciona todavía**: `--p peso_por_pua=1`
lee el peso en el centro de la púa. Probado, deja el dibujo cortado y con MÁS
ruido. El problema es que hay **dos numeraciones de púa distintas**: el pulso usa
`floor(fase)` y la rejilla de `patron` usa `round(...)`, y se cruzan medio paso.
Alinearlas (las dos con `floor`) tampoco lo arregló: el patrón cae a 7/9 filas y
las medias tintas siguen en 15 %.

Descartado midiendo, por si sirve para no repetirlo: ancho de hoja contra la
rejilla, giro de costura (no se aplica en este generador), resolución de
muestreo, `borde_mm`, borde de hoja en la frontera de columna, segmentos
múltiplo exacto de púas, y `degradado=0` (que además deja el solape en 0 %).

## Generar de nuevo

El comando exacto está en `matera_kadzi.params.json`.
