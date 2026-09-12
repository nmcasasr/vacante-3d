# Florero Kadzi — qué es cada archivo

**La carpeta dice CÓMO está hecho. El nombre del archivo dice CON QUÉ NÚMEROS.**

    hoja_fondo5_pico9mm      ->  el pico del fondo mide 5 mm, el de la figura 9

Todo es cordón **1.2 mm**, capa 0.4, modo vaso, Ø50 salvo donde diga.
Las recetas están en `recetas/florero-kadzi/`, con el mismo árbol.

---

## Los números salen de Squeezy, que está impreso y funciona

`Squeezy Fidget Toy.gcode` es **PETG**, y es la referencia contra la que este
proyecto calibra todo. Medido sobre su g-code:

| | Squeezy | estas piezas |
|---|---|---|
| boquilla | 250 la primera capa, 240 el resto | 240 |
| cama | 70 | 70 |
| ventilador | 0 hasta z 27.5, después **100 %** | 100 % |
| altura de capa | ≈ 0.76 mm | 0.8 |
| ancho de cordón | ≈ 1.27 mm | 1.2 |
| sección | 0.960 mm² | 0.96 |
| **velocidad** | **8 mm/s** en el 93.9 % del recorrido | **8 mm/s** |
| **frenado** | **4 mm/s**, la mitad exacta, en el 5 % | barrido alrededor de 0.5 |

Dos cosas que conviene no olvidar. Una: el ventilador de PETG **no** va al 40 %
que pone `--material PETG` — la referencia usa 100, apagado sólo al principio
para que agarre. Dos: el frenado de la punta es **la mitad** de la velocidad
normal, no menos; por eso el barrido corre alrededor de 0.5 y no más abajo.

A 8 mm/s todo tarda el doble que a 15: el cupón de matriz pasa de ~35 min a
~70, y un florero de ~1.5 h a ~3.

## Las tres maneras de hacer el grumo

Es la decisión que separa las carpetas, y sale de una sola regla física: **en
modo vaso cada vuelta se apoya en la de abajo, y la boquilla deja un cordón de
1.2 mm.** Si la vuelta nueva sale más de eso hacia afuera, esa punta queda al
aire.

### `grumo-crece` — el grumo sale de a poco

Después de las vueltas lisas, el grumo crece un escalón por vuelta hasta salir
entero. Todo apoya siempre.

- **Techo:** `pico <= con_patron x 1.2 mm`. Un pico de 9 mm necesita 8 vueltas.
- **Costo:** esas vueltas separan una fila de grumos de la siguiente, y esa
  separación es el alto del "punto" con el que se dibuja la figura. Más pico,
  dibujo más borroso.
- Todas dan **IMPRIMIBLE**.

### `grumo-puentea` — el grumo sale de una y se cuelga

Sale entero en la primera vuelta después de las lisas, tendiéndose al aire, y
el cabezal frena sólo en la punta (`puente_lento`) para pararse y dejar
material. Es lo que hace la pieza de referencia: los grumos se descuelgan un
poco y eso es parte de cómo se ve.

- **Sin techo de pico** y con la mejor resolución de dibujo.
- `verificar_pieza.py` lo da **NO IMPRIMIBLE**: 12 % de muestras sin apoyo
  contra 1.88 % de la referencia. Eso no es un error del archivo — es que el
  criterio supone que no querés puentes, y acá sí los querés. El peor puente
  mide 11.2 mm, por debajo de los 12 que la referencia aguanta.
- **Bajar la velocidad no adelgaza la línea**: la sección la fija la geometría
  y no el `F`, así que deposita lo mismo en más tiempo.

**Hay que imprimir el cupón antes de comprometer un florero acá.**

### `sin-cadencia` — sin vueltas lisas

Todas las vueltas pulsan en la misma fase, así que el pico se apila sobre el
pico: no hay salto, el largo sale gratis y el dibujo queda nítido. Pero los
picos dejan de ser grumos apilados y pasan a ser **crestas verticales
continuas**, que no es el aspecto del video.

---

## `hoja-degradada` — la hoja que no se ve cuadrada

`2-floreros/hoja-degradada/hoja_fondo1.25_pico7mm` — **IMPRIMIBLE**, contacto
0.00 %.

Dos cambios sobre las otras hojas:

- **El relieve baja hacia el centro** (`degradado=0.2`). En las demás la hoja es
  una meseta pareja de canto vivo y se lee cuadrada; acá el borde sale entero
  —los 7 mm— y el centro apenas por encima del fondo, así que la hoja se ve
  abombada hacia adentro. La nervadura y la K se leen igual, porque son huecos.
- **Pico de 7 mm** sobre un fondo de 1.25.

Tres alturas, con la hoja encogida en proporción para que no quede apretada
(el ancho se deja en 28 mm en las tres: es lo que la K necesita para leerse):

| archivo | alto | hoja + tallo | tiempo estimado |
|---|---|---|---|
| `alto65_pico7mm` | 65 mm | 45 + 11 mm | **~1.5 h** |
| `alto70_pico7mm` | 70 mm | 48 + 12 mm | **~1.6 h** |
| `hoja_fondo1.25_pico7mm` | 75 mm | 52 + 13 mm | ~1.75 h |

Los tiempos son estimados por recorrido y velocidad con un 1.4x por
aceleración. `ESTADO.md` ya avisa que este estimador sale corto —son segmentos
de décimas de milímetro y ahí manda la aceleración, no el `F`—, así que
tomalos como piso. El de Orca al laminar da el bueno.

## `hoja-degradada-puente` — el grumo que puentea, con la hoja degradada

| archivo | alto | punto del dibujo | tiempo | contacto sin apoyo |
|---|---|---|---|---|
| `alto65_pico5a9mm` | 65 mm | **1.64 x 1.60 mm** | ~4.0 h | 15.9 % |
| `alto70_pico5a9mm` | 70 mm | **1.64 x 1.60 mm** | ~4.4 h | 16.6 % |

Las dos dan **NO IMPRIMIBLE** contra el criterio de `verificar_pieza.py`: 16 %
de muestras sin apoyo contra 1.88 % de la referencia. Es el puenteo, buscado a
propósito — el peor puente mide 10.9 mm, por debajo de los 12 que la referencia
aguanta. Pero 16 % es OCHO VECES la referencia y nadie imprimió todavía nada
con esta técnica: **va el cupón antes**
(`1-cupones/grumo-puentea/largos_3a9mm`).

Pico de **5 mm de base y 9 en la figura**, cadencia **2 lisas + 2 con patrón**,
el grumo sale de una y puentea, y el tallo con el degradado INVERTIDO: alto en
el medio y fino en los cantos.

La cadencia de 2+2 en vez de 3+2 es lo que da la resolución: el punto del
dibujo mide 1.60 mm de alto contra los 4.40 de la versión que crece. Se puede
porque el grumo no necesita vueltas para crecer — sale entero y se cuelga.

**Lo que cuesta: contraste.** La figura se lee por la DIFERENCIA entre el pico
del fondo y el de la figura, y con 5 contra 9 esa diferencia es el 44 % del
relieve. En `hoja-degradada` (1.25 contra 7) es el 82 %, y las hojas saltan
mucho más. No es la técnica de puente: es el fondo alto. Si el dibujo importa
más que el relieve al tacto, hay que bajar el fondo.

## El piso: dos arreglos, los dos vistos en impresiones

Todos los archivos llevan `--base-borde 4` y `--base-solape 0.92`. Los dos
defectos por defecto están APAGADOS (`0` y `1.0`): una perilla que cambia una
calibración no puede venir encendida, o regenerar una pieza vieja con su
comando de siempre da otra pieza. El hongo, el peine y el gusanito se regeneran
byte a byte con sus comandos originales.

### El piso no se pegaba A SÍ MISMO — `--base-solape 0.92`

Las pasadas del piso se separan `ancho - 0.215 x altura_capa`, y esa fórmula
depende de la ALTURA DE CAPA:

| | capa | separación | solape del cordón |
|---|---|---|---|
| hongo (pega bien) | 0.8 mm | 1.029 mm | **14.2 %** |
| cupón, antes | 0.4 mm | 1.118 mm | **6.8 %** |
| cupón, ahora | 0.4 mm | 1.028 mm | **14.3 %** |

Con la mitad de solape las pasadas **se rozan en vez de fundirse**. El hongo
cae del lado bueno sin que nadie lo haya elegido: imprime su piso a 0.8.

No hubo que inventar nada — `lamparas/recorrido.py` ya usa este mismo margen
sobre esta misma fórmula, con el mismo nombre y el mismo valor calibrado (0.92)
para su relleno concéntrico.

### La pared se apoyaba en el CANTO del piso — `--base-borde 4`

La última pasada del piso y la primera vuelta de la pared compartían eje, y al
enfriarse la pared levantaba el borde. Ahora el piso sigue 4 mm hacia afuera y
la pared cae ~4.1 mm por dentro del canto, con más área contra la cama.

**El reborde no se ve en los floreros**: el piso queda en Ø58.2 y los picos
llegan a Ø63.7 (hoja-degradada) o Ø67.9 (la de puente), así que el reborde
queda POR DENTRO. Sólo asoma en los dos cupones de pico corto —`largos_1.2a3.6mm`
(1 mm) y `extrusion_1.0a1.8x` (3.4 mm)— porque ahí la pieza es casi lisa, y en
un cupón no importa.


## 1-cupones — imprimí estos primero

### `velocidad` — a qué velocidad sale mejor el puente

**Ø50 x 40 mm.** Cinco bandas con la punta del grumo a distinta velocidad:

| banda | factor | velocidad en la punta |
|---|---|---|
| 1 | 1.00 | 15 mm/s (sin frenar) |
| 2 | 0.60 | 9 mm/s |
| 3 | 0.40 | 6 mm/s |
| 4 | 0.25 | 4 mm/s |
| 5 | 0.15 | 2 mm/s |

El resto de la vuelta va siempre a 15 mm/s: **se frena sólo en la punta**, que
es el vértice donde la boquilla se para y vuelve. Frenar todo el vuelo hace lo
contrario de lo que hay que hacer — cuanto menos tiempo al aire, menos se
descuelga el grumo. Está medido en la referencia (ver `puente_lento`).

Alrededor lleva los cinco gajos de largo (3 a 9 mm), así que también dice si la
velocidad que sirve depende del largo.

**El ventilador va al 100 % en la punta** (`ventilador_pua`). Es la otra mitad
de tender un puente y la que más pesa: bajar la velocidad le da tiempo al
cordón, pero lo que lo endurece antes de llegar al otro lado es el aire. Fuera
de la punta vuelve al del perfil —no a 0— porque el ventilador tarda en
responder y apagarlo entre grumo y grumo lo dejaría llegando tarde a la punta
siguiente.

### `matriz` — las dos variables cruzadas en una pieza

**Ø50 x 40 mm, ~35 min.** Es el que reemplaza a los cupones sueltos de
separación: 25 combinaciones en un solo cilindro.

- **A lo ALTO, la separación** (`barrido_puas`): cinco bandas de 8 mm.
- **A lo ANCHO, el largo del pico** (máscara `sectores`): cinco gajos.

| | sector 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| banda 1 — 36 púas, hueco 3.16 mm | 3.0 | 4.5 | 6.0 | 7.5 | 9.0 mm |
| banda 2 — 44, hueco 2.37 | 3.0 | 4.5 | 6.0 | 7.5 | 9.0 |
| banda 3 — 52, hueco 1.82 | 3.0 | 4.5 | 6.0 | 7.5 | 9.0 |
| banda 4 — 60, hueco 1.42 | 3.0 | 4.5 | 6.0 | 7.5 | 9.0 |
| banda 5 — 72, hueco 0.98 | 3.0 | 4.5 | 6.0 | 7.5 | 9.0 |

Girás la pieza y comparás largos; subís la vista y comparás separaciones.

Funciona porque las dos variables usan ejes distintos: la separación sólo puede
barrerse a lo alto —las columnas tienen que apilarse dentro de una banda— así
que el largo se barre por ÁNGULO, con una máscara en escalera. El patrón
convierte el peso de la máscara en amplitud, así que una escalera de pesos es
una escalera de largos.

Lleva todo lo nuevo: **capa 0.8**, piso de 0.8, reborde de 4 mm, solape 0.92,
cordón 1.2 y el grumo que puentea con el frenado en la punta.



Cilindros cortos sin dibujo: son para leer el grumo, no la figura. Cinco bandas
de abajo hacia arriba.

| archivo | alto | bandas |
|---|---|---|
| `grumo-crece/largos_1.2a3.6mm` | 36 mm | 1.2 · 1.8 · 2.4 · 3.0 · 3.6 mm |
| `grumo-crece/largos_5a13mm` | 40 mm | 5 · 7 · 9 · 11 · 13 mm |
| `grumo-crece/extrusion_1.0a1.8x` | 36 mm | 1.0 · 1.2 · 1.4 · 1.6 · 1.8 x de material |
| **`grumo-puentea/largos_3a9mm`** | 40 mm | 3 · 4.5 · 6 · 7.5 · 9 mm |

`grumo-crece/largos_1.2a3.6mm` ya se imprimió: **la técnica salió bien pero los
picos son cortos**. Los otros dos de largos son la continuación.

El que decide el estilo es **`grumo-puentea/largos_3a9mm`**: dice a partir de
qué largo el grumo se descuelga más de lo que te gusta.

En `extrusion_*` el preview va a pintar el cordón de ancho uniforme — la
anotación `; LINE_WIDTH:` lleva el ancho nominal por contrato con Orca (ver
`.agents/MAPA.md`). Lo que cambia es la E, y eso sí se imprime.

## 2-floreros — Ø50 x 75 mm, 4 hojas con la K inscrita

| archivo | fondo | figura | punto del dibujo |
|---|---|---|---|
| `grumo-crece/hoja_fondo0.6_pico2.4mm` | 0.6 | 2.4 mm | 1.64 x 2.40 mm |
| `grumo-crece/hoja_fondo1.25_pico5mm` | 1.25 | 5.0 mm | 1.64 x 3.60 mm |
| `grumo-crece/hoja_fondo2.5_pico6mm` | 2.5 | 6.0 mm | 1.64 x 4.00 mm |
| `grumo-crece/hoja_fondo5_pico7mm` | 5.0 | 7.0 mm | 1.64 x 4.00 mm |
| `grumo-puentea/hoja_fondo5_pico9mm` | 5.0 | 9.0 mm | **1.64 x 2.00 mm** |
| `sin-cadencia/hoja_crestas_fondo5_pico9mm` | 5.0 | 9.0 mm | **1.64 x 0.40 mm** |

`grumo-crece/hoja_fondo5_pico7mm` tiene el fondo que pediste (5 mm) pero **el
dibujo casi no se ve**: el contraste es 2 mm sobre un relieve de 7, así que
todo se lee igual de alto. Es el que muestra el problema, no la solución.

`grumo-crece/flores_fondo0.6_pico2.4mm` es el otro florero, Ø68 x 200 mm, con
la máscara de flores en vez de hojas.

## 3-hueco-abierto — la variante descartada

Lo mismo pero con `ocupacion=0.5`: el hueco del pico mide 1.12 mm contra un
cordón de 1.2, o sea que se abre y el grumo sale hueco. Con 0.30 mide 0.67 y
las dos patas se funden desde la base, que es la bolita de la referencia.

## 0-3mf-viejos — NO IMPRIMIR

Injertos hechos antes de dos arreglos (el muestreo de la meseta y el borde
entre bandas). Hay que volver a injertar desde el g-code de arriba.

---

## Lo que todavía no está medido

1. **Ninguna está impresa** salvo `grumo-crece/largos_1.2a3.6mm`.
2. **El largo de pico no está calibrado**, ni el estilo. Los dos salen de los
   cupones.
3. **Que la pared de un cordón aguante agua no está medido.**
