# Sesión del 10-09-2026 (c) — el florero hoja de Kadzi, y la meseta que las muestras esquivaban

## ARREGLADO, y es el hallazgo de la sesión: `muestras` era lotería

La rejilla angular es pareja y **no arranca en la fase de la púa** — arranca en
el ángulo donde terminó la espiral del piso, que es cualquiera. Si la meseta de
la púa es más angosta que el paso de muestreo, las muestras la ESQUIVAN y el
turupe no llega nunca a la altura pedida.

Con `ocupacion=0.30` la meseta mide `0.30 x 0.34 = 0.102` del paso contra un
muestreo de `1/6 = 0.167`. El g-code depositaba **1.78 mm de los 2.40 pedidos**.

Y lo peor: era LOTERÍA. Con 95 púas la fase caía bien y salían los 2.40; con 70
caía mal y salían 1.78. La misma pieza, dos alturas, según un ángulo que nadie
eligió. Las tres piezas `_oc30` de la sesión anterior salieron con ese defecto
adentro y se regeneraron.

`construir()` ahora sube `muestras` hasta garantizar una muestra en la meseta
(10 para `ocupacion=0.30`) y lo dice en la corrida. Es la misma cuenta que
`bowls/peine.py` hace con `muestras_diente`, y por el mismo motivo — estaba
escrita en el repo desde la otra rama y no se leyó a tiempo. **Con la meseta por
defecto (`ocupacion=0.5`) da 6, así que ninguna pieza anterior se mueve**:
`cupon_largos` regenera con 0 instrucciones distintas.

## NUEVO: la máscara `hoja`, con tallo, y la K en la nervadura

El logo de Kadzi es un rombo alto partido por una hendidura vertical, con dos
brazos que salen del medio hacia la derecha. Una hoja ya tiene esa hendidura y
se llama nervadura. Así que **la marca no se estampa encima de la hoja: la
nervadura ES el asta de la K** y los brazos son dos nervios más. Por eso
`hoja(k=1)` no dibuja asta propia.

El tallo y la panza —el ensanchamiento por debajo del medio— no son adorno:
una lente simétrica no tiene arriba ni abajo y se lee como una almendra o un
ojo. Son las dos cosas que la vuelven hoja.

Trabaja en milímetros de superficie, como `flores` y a diferencia de `carita`.

## Y un tercer caso de lo mismo: los rasgos del tamaño de la rejilla

Con `puas=70` y `columnas=4`, las hojas caen cada 17.5 púas: dos quedan sobre
una púa y dos entre púas. El TALLO mide dos puntos de ancho, así que aparecía
en dos de las cuatro hojas y en las otras no. Es el mismo defecto que la meseta
—un rasgo del tamaño de la rejilla a merced de una fase que nadie eligió— con
otra cara.

La salida es que `puas` sea DIVISIBLE por `columnas`: con 96 y 4, las cuatro
hojas reparten 24 púas exactas y caen las cuatro igual. De paso 96 púas suben
la resolución a 1.64 mm sin perder relieve, porque con `ocupacion=0.30` sobra
valle (100 % hasta 96, 74 % a 104).

    punto        2.24 x 2.40  ->  1.64 x 2.40 mm
    hoja         13 x 30      ->  28 x 54 mm
    media hoja   2.9 puntos   ->  8.5 puntos
    vena         0.9 puntos   ->  1.8 puntos

## Lo que hizo fracasar el primer intento: la rejilla del dibujo

El patrón no puede dibujar más fino que un turupe. Un "punto" del dibujo mide

    ancho = 2·pi·radio / puas          alto = (lisas + con_patron) · altura_capa

En el Ø50 con 70 púas y cadencia 3+3 son **2.24 x 2.40 mm**: la pieza entera son
70 x 31 puntos. Con las medidas del croquis a mano —hojas de 13 x 30 mm, venas
de 2 mm— la media hoja donde va la K son 2.9 puntos y la vena **0.9 puntos**,
menos de uno. No se leyó nada.

Con hojas de 20 x 34 la media hoja pasa a 4.5 puntos y la K aparece. Queda la
regla: **antes de elegir el tamaño de una figura, dividir sus rasgos por esos
dos números**, y mirarla a la resolución del patrón. El
`python -m lamparas.superficie` dibuja la máscara ideal y MIENTE sobre lo que la
pieza va a poder.

## La pieza

`output/florero-kadzi/florero_hoja.gcode` — Ø50 x 75 mm, cuatro hojas altas con
tallo. IMPRIMIBLE, trazo continuo, 8 % de solape entre vueltas, turupe de
2.400 mm clavado.

## Lo que queda abierto

1. **La amplitud no está calibrada.** 2.4 mm es el medio del barrido del cupón,
   elegido a ojo. El número sale de imprimir `cupon_largos_oc30`.
2. **El solape entre vueltas quedó en 8 %.** Es el mínimo de todo lo hecho hasta
   ahora (el jarrón impreso mide 39.5 %). Sale de sumar el crecimiento del grumo
   (2.4/3 = 0.8 mm) con el borde de la figura. Da IMPRIMIBLE y sin puentes, pero
   es el número a vigilar si la pieza sale mal: se sube con `con_patron=4` o
   bajando `amplitud`.
3. Sigue abierto todo lo de la sesión anterior: `peor_salto_radial` con `abs()`,
   `SOLAPE_MINIMO` más estricto que el jarrón impreso, y el contador de púas de
   `vista_relieve.py` que da 0 con la cadencia encendida.

---

# Sesión del 10-09-2026 (b) — el florero de turupes, y las dos ramas juntas

## Lo primero: NADA ESTÁ IMPRESO

Lo verificado es el g-code. Las tres piezas de `output/florero-kadzi/` pasan los
tres criterios contra `Squeezy Fidget Toy.gcode`, y ninguna salió de la
impresora todavía. Los dos cupones existen justamente para eso.

## Qué pidió el usuario, en tres correcciones

La técnica quedó definida a lo largo de la sesión y las dos primeras versiones
estaban mal. Vale la pena el orden, porque cada corrección tiró abajo una
suposición:

1. **El dibujo lo hacen los turupes**, no las zonas lisas. En modo vaso, vueltas
   normales, y donde va la figura la boquilla sale y entra.
2. **El pulso está en TODA la pieza**; lo que cambia es la INTENSIDAD. En la
   figura sale más, en el fondo sale menos. Con el fondo liso el dibujo queda
   flotando y se ve el recuadro — que es exactamente lo que decía el encabezado
   de `bowls/peine.py`, escrito por la otra rama. Se leyó tarde.
3. **Se alternan vueltas lisas y vueltas con patrón**: 3 y 2 en la foto. Las
   lisas son las costillas continuas que atan las columnas entre sí.

Y una cuarta, mirando el primer cupón: **los turupes eran demasiado cortos para
verse**. 0.6 mm no se percibe. El rango subió a 1.2..3.6 mm y las púas bajaron
de 150 a 70-95 para que quede valle.

## Lo que decidió que la pieza se imprimiera: el grumo CRECE

Con la cadencia encendida, la primera vuelta con patrón se corre la amplitud
entera respecto de la vuelta lisa de abajo. Con 1.30 mm contra un cordón de 1.0
la punta del grumo queda al aire, y está medido:

    salto entero de una vez     contacto 5.90 %   -> NO IMPRIMIBLE
    repartido en 2 vueltas      contacto 1.38 %   -> IMPRIMIBLE

(la referencia mide 1.88 %). `crecida()` reparte la amplitud a lo largo de las
`con_patron` vueltas de la banda. La BAJADA de vuelta a la pared lisa no
necesita rampa: correrse hacia adentro no deja nada al aire.

De ahí sale la regla de tamaño de esta pieza: **el salto por vuelta es
`amplitud / con_patron`, y tiene que caber en un cordón.** Con cordón de 1.2 y
`con_patron=3`, la amplitud máxima es 3.6 mm.

## ARREGLADO: el aviso medía |Δ| y gritaba sobre una pieza sana

`_avisar` comparaba `abs(radio(t2) - radio(t))`. Cuando la banda de patrón
termina, la vuelta lisa de arriba se corre 1.3 mm HACIA ADENTRO, y eso no deja
nada al aire: se apoya en el valle, que vale la silueta en todas las vueltas.
Con `abs()` los dos sentidos daban 1.30 y el aviso salía igual con la pieza ya
arreglada. Ahora mide el salto CON SIGNO, hacia afuera, que es el único que
produce voladizo.

**El mismo `abs()` está en `comun.peor_salto_radial`, y ahí NO se tocó.** Es
criterio compartido con `gen_rosca.py` y calibrado contra el jarrón. Se
comprobó que cambiarlo sería seguro —las nueve variantes de rosca deciden lo
mismo con `abs` y con signo, la diferencia es 0.269 contra 0.263— pero es una
decisión que no corresponde tomar de paso en una pieza nueva. Ver "lo que
queda abierto".

## ARREGLADO: la banda empezaba a media vuelta de donde cierra la espiral

`int(t/dt_capa + 0.5)` cambia de capa en `t = (k+0.5)·dt_capa`, o sea medio giro
corrido del punto donde el recorrido ya tiene su costura. Eso agrega un SEGUNDO
escalón helicoidal en vez de esconder el cambio en el que ya existe. Con
`math.floor` los dos coinciden.

## NUEVO: `funcion_flujo` en `generar_pieza`

Multiplicador del ancho de cordón punto a punto, `(angulo, t) -> factor`. Es
cuánto material se deposita, no dónde va la boquilla: engorda el turupe sin
moverlo. Se emite como `ExtrusionGeometry` sólo cuando el factor CAMBIA —
emitirlo en cada punto duplicaría las líneas del archivo para repetir el mismo
número.

Con None no emite nada: el hongo se regenera BYTE A BYTE idéntico al impreso, y
el peine también.

**Ojo con el preview.** `; LINE_WIDTH:` sigue llevando el ancho nominal
constante, que es lo que `MAPA.md` fija como contrato con Orca. O sea que el
cupón de extrusión se va a ver de ancho uniforme en el preview aunque la E sí
varíe. Medido sobre el archivo: banda 1 pico 0.2993, banda 5 pico 0.4789, que
es exactamente 1.6x. Lo que se imprime está bien; lo que se ve, no.

## NUEVO: `verificar_continuidad.py`

El usuario preguntó si los cambios de capa son fluidos y no había con qué
contestarle: `verificar_pieza.py` mide apoyo y sección, y `verificar_capas.py`
lee las marcas `; CHANGE_LAYER`, que las emite el INJERTO y no el cuerpo.

Sobre el florero: **el cuerpo entero es UNA línea de 453 973 movimientos
seguidos**, 0 viajes, 0 retracciones, 0 bajadas de Z, y la subida es 0.00044 mm
pareja. El paso de XY máximo es el turupe y nada lo excede.

Las dos trampas al escribirlo, las dos pisadas primero:

- **La extrusión es RELATIVA** (`M83`). Cada `E0.166` es lo que se empuja en ese
  segmento, no la posición del filamento. Comparando contra el `E` anterior
  salían 90 299 "retracciones" en una pieza que tiene dos.
- **El cuerpo no empieza en la primera línea.** Adelante hay purga y homing, y
  esos son los movimientos MÁS GRANDES del archivo: descartarlos por tamaño
  escondería el defecto que se busca. Ahora el cuerpo se define por lo que es,
  la tirada más larga de movimientos que extruyen seguidos.

Es la tercera vez en la sesión que el número raro era el medidor y no la pieza.

## Las dos ramas juntas: `feature/florero-kadzi-final`

`kadzi1` hizo las púas, `kadzi2` el peine, y las dos tocaron los mismos tres
registros. Los dos g-code se regeneran byte a byte después de juntarlos. Lo que
se unificó está en el mensaje del commit del merge; lo que importa acá:

- **El modelo del cordón de kadzi2 se conectó a las púas.** Contesta la
  pregunta del usuario —"cuánto se ve"— con un número en vez de una regla. El
  aviso viejo era `paso < 1.0 mm`, y a 180 púas, donde ya se pierde la mitad
  del relieve, no decía nada.
- **El hallazgo de kadzi1 (`--capas-transicion 0`) cura la pieza de kadzi2.** El
  peine nunca pasó por `verificar_pieza.py` y daba NO IMPRIMIBLE, con un puente
  de 21.2 mm. Con la transición apagada: 0.00 e IMPRIMIBLE.
- **`caritas`, `feliz` y `triste` reventaban en la rama de kadzi2.** Un
  `**kwargs` que reenvía no es una promesa de aceptar todo.

## Los dos cupones, que es lo que hay que imprimir

Ø50 x 36 mm, cordón 1.2, ~21 min de recorrido cada uno (contá 25-35 reales: son
40 000 segmentos cortos y ahí manda la aceleración, no el `F`).

- `cupon_largos.gcode` — cinco bandas de 7.2 mm con el turupe a 1.2, 1.8, 2.4,
  3.0 y 3.6 mm. La quinta está a propósito en el límite: salto 1.2 contra
  cordón 1.2, 0 % de solape, y es la única con tramos al aire (0.15 %, el peor
  0.65 mm). Si esa banda sale y las otras también, el techo es más alto de lo
  que dice el modelo.
- `cupon_extrusion.gcode` — amplitud fija en 2.4 y el flujo del turupe a 1.0,
  1.2, 1.4, 1.6 y 1.8. IMPRIMIBLE en las cinco.

Los dos van con `--p mascara=ninguna`: son para leer el turupe, no el dibujo.

## Lo que queda abierto

1. **`comun.peor_salto_radial` mide `abs()`.** Está comprobado que pasarlo a
   signo no mueve ninguna decisión de la rosca, pero es criterio compartido y
   calibrado: la decisión es del usuario. Mientras tanto, el florero necesita
   `--paso fijo` a mano; con `--paso medir` da ADAPTATIVO y la pieza se rompe
   (fue medido: puentes de 92 mm).
2. **`SOLAPE_MINIMO` es 0.5 y el jarrón impreso mide 0.395.** El umbral es más
   estricto que una pieza que funciona, así que `medir` va a decir ADAPTATIVO
   en cosas que se imprimen bien. Es el mismo punto 1 visto de costado.
3. **El contador de púas de `vista_relieve.py` da 0 en los cupones.** Con la
   cadencia encendida su detección de "vuelta más texturada" no encuentra el
   período. Da bien en el florero (75) y en una pieza sin cadencia (150 clavadas
   sobre `puas=150`). Es el medidor, no la pieza.
4. **El choque del arranque, 0.2 %, sigue sin arreglar y a propósito.** Está
   todo en los 3 mm de abajo y no lo trae este patrón: un cilindro liso
   generado con el mismo código da 4.99 % en esa franja.
5. **Que la pared de un cordón aguante agua no está medido.**

---

# Sesión del 10-09-2026 — el florero de púas

## Lo primero: NO ESTÁ IMPRESO

Lo que está verificado es el g-code. `output/florero_puas.gcode` (y su receta en
`recetas/florero_puas/v001/`) pasa los tres criterios contra
`Squeezy Fidget Toy.gcode`:

    línea fina    0.00 %   contra 0.26 % de la referencia
    contacto      0.00 %   contra 1.88 %
    peor puente   0.00 mm  contra 12.00 mm
    -> IMPRIMIBLE

Y los 453 973 segmentos extruyen la sección nominal exacta: el más fino mide
0.400 mm, 2.5:1. No hay un solo cordón comprometido en la pieza.

## Qué se pidió y qué es

Réplica de un FLORERO de las fotos —no una lámpara— : un tubo Ø68 x 200 mm
cubierto de púas, con flores dibujadas en las zonas donde la púa se apaga. La
técnica es la que dijo el usuario y es exactamente lo que hace el g-code: sacar
y meter levemente la boquilla, 150 veces por vuelta, a lo largo de todo el tubo.

Piezas nuevas:

- `lamparas/bowls/puas.py` — el patrón. `--p puas` por vuelta, `--p amplitud` en
  mm, `--p ocupacion` y `--p filo` la forma del pulso.
- `superficie.flores()` — la máscara, en MILÍMETROS de superficie y no en grados
  como `carita()`: una flor tiene que salir redonda en cualquier diámetro.
- `vista_relieve.py` — la pieza desenrollada a PNG, para ver el dibujo antes de
  imprimirlo.

## Lo que decidió que la pieza saliera: el borde de la figura

En modo vaso el paso vertical es **uno solo por vuelta** y `marcha_vertical` lo
achica mirando el peor ángulo. El borde de una flor es donde la púa deja de
existir, así que con borde duro dos vueltas vecinas se llevan el milímetro
entero de diferencia en ese ángulo y el paso de LA PIEZA ENTERA se desploma. No
es un defecto local: es la propiedad del paso.

Suavizar la máscara en el plano NO alcanza, y la cuenta dice por qué: entre dos
pétalos el contorno corre casi horizontal, así que subir 0.4 mm lo corre 1.7 mm
de costado. Harían falta ~11 mm de desvanecido —una flor sin contorno— y encima
dependería de la forma de cada figura, así que el próximo dibujo lo rompe otra
vez.

La salida es promediar la máscara a lo largo de N alturas repartidas en
`suave_borde` milímetros. Eso **acota por construcción** cuánto puede cambiar el
peso al subir una vuelta, sea cual sea la figura, y deja intactos los bordes
verticales, que no cuestan nada porque el ángulo no cambia entre vueltas.

    máscara punto a punto        0.550 mm de radio por vuelta
    promediada en 5 mm           0.140 mm

Y es lo que se ve en la foto de referencia: las púas se acortan al acercarse a
la flor en vez de cortarse de golpe.

## Se trajo la rama `rosca-paso-fijo`, y hacía falta

El usuario avisó que ahí ya estaba resuelto, y tenía razón: sus cuatro arreglos
de `comun.py` son exactamente lo que le pasa a una pared vertical con relieve
angular, que es este florero.

- **`paso_fijo`**. `marcha_vertical` está pensada para cúpulas; acá el
  corrimiento entre vueltas es RADIAL y lo lee como si fuera vertical. Con
  `--paso-fijo auto` la altura de capa queda en **0.4000 mm con desvío 0.0001**
  en las 492 vueltas, en vez de bandearse.
- **`N_ANG` adaptativo**. Con 32 ángulos fijos y 150 púas por vuelta el "peor
  ángulo" era moiré, no pieza.
- El **anillo plano** y el **piso de la rampa** en media capa.

Copiar esos hunks en vez de traer la rama habría dejado dos versiones del mismo
arreglo en el mismo archivo, que es la trampa que abre `MAPA.md`.

Lo que se agregó encima: el criterio de si conviene el paso fijo estaba dentro
de `gen_rosca.py`. Ahora vive en `comun.conviene_paso_fijo()` y lo usan los dos,
porque una regla calibrada duplicada se separa. `gen_rosca.py` da el mismo
número que antes.

## `capas_transicion` había que apagarla, y el motivo importa

Con la transición encendida, las primeras vueltas del florero subían 0.067 mm
—cordones de 15:1, el mismo anillo imposible en la base que este archivo ya
documenta más abajo— y de ahí salían el único puente de 29.4 mm y el 0.13 % de
línea fina de la pieza.

El motivo: la transición atenúa el paso para que el patrón nazca de a poco, pero
en esta pieza el patrón **a esa altura todavía no existe** — las púas arrancan
en `desde` y suben en `suave_mm`, en milímetros. La transición estaba atenuando
por un patrón que no estaba. Con `--capas-transicion 0`: puente 0.00, línea fina
0.00.

## Dos controles que se corrieron

- **El hongo sale byte a byte idéntico.** Regenerado desde
  `hongo_latest.params.json` con todo lo de esta sesión adentro: 0 instrucciones
  distintas contra `hongo_latest.gcode`, que es el que está impreso. Sólo cambia
  el comentario de receta del encabezado.
- **El contador de púas está calibrado.** Sobre una pieza sin figura generada
  con `puas=150`, `vista_relieve.py` cuenta 150. Antes contaba 33, y el roto era
  el medidor: sus filas medían 0.09 mm de alto contra los 0.4 que sube una
  vuelta, así que cada fila veía un cuarto de vuelta. Una fila = una vuelta.

## ARREGLADO: la CLI de los bowls no generaba NINGUNA pieza del catálogo

`'str' object is not callable` en `__main__.py:607`. La silueta seguía siendo el
NOMBRE cuando `--segundos-vuelta` —que viene encendido por defecto— le pedía el
radio a una altura. El propio comentario de esa línea decía "silueta ya
resuelta" y no lo estaba. Sólo se salvaban las piezas que vienen de un
`--perfil`, que es por donde entra el hongo. Ahora la silueta se resuelve a
función apenas se elige.

## ARREGLADO: `test_verificar.py` daba 12 de 13, y era el banco

Es el punto 2 de "LO QUE SIGUE" de la sesión de la rosca. El caso buscaba
`"100.00%"` pegado y `verificar_pieza` lo imprime `"100.00 %"` con la unidad
separada. El criterio estaba bien desde siempre. **13 de 13.**

Un banco con un rojo permanente enseña a ignorarlo, que es lo contrario de para
lo que existe.

## Lo que queda abierto

1. **El choque de la base, sin arreglar y a propósito.** El florero mide 0.21 %
   y está TODO en los 3 mm de abajo: la vuelta plana que arranca la pared se
   deposita encima de la última pasada de la espiral del piso, mismo radio y
   misma Z. **No lo trae este patrón** — un cilindro liso generado con el mismo
   código da 4.99 % en esa franja (control corrido). Arreglarlo es tocar el
   traspaso piso-pared de `generar_pieza`, que afecta a todas las piezas; no se
   hace de paso en una pieza nueva.
2. **`ver_rosca.py` y `vista_relieve.py` se pisan.** Los dos desenrollan un
   g-code a PNG y los dos llegaron por su cuenta a "una fila de píxeles por
   vuelta". `vista_relieve.py` no depende de numpy ni de PIL, mide el relieve
   contra la pared de cada vuelta (no contra el radio global), respeta la escala
   en los dos ejes y cuenta el período de la textura; `ver_rosca.py` tiene el
   paso de la rosca metido adentro. Habría que quedarse con uno. No se borró
   ninguno porque el de la rosca es de un trabajo en curso ajeno.
3. **El tiempo de impresión no está estimado, y el estimador del injerto va a
   mentir.** Son 900 segmentos por vuelta de 0.14 mm cada uno: a esa longitud
   manda la ACELERACIÓN de la máquina, no el `F` que se le pide, y
   `bambu.ts` calcula largo/velocidad. El número que anuncie va a salir corto.
4. **El florero es de una pared de un cordón.** Que aguante agua no está
   medido y no se afirma.

---

# Sesión del 25-08-2026 — altura de capa, primera vuelta y render sólido

## ARREGLADO: la primera vuelta flotaba 0.2 mm sobre la cama

Estaba en **todas** las roscas y era el único motivo por el que daban NO
IMPRIMIBLE: 146 mm de recorrido seguido sin apoyo a z 0.7.

`generar_pieza` tenía la guarda

    anillo_plano = espiral and base_solida and capa == 0

Una vuelta plana no consume altura, así que no hay que descontarla de `z_vuelta`.
Pero la condición sólo contemplaba el piso macizo. Una pieza HUECA con
`capas_base >= 1` también tiene su primera vuelta plana —`rampa` es falsa
mientras `capa < capas_base`— y sí descontaba. Resultado: el anillo se imprime a
z=0.4 y la espiral arranca a 0.6.

Ahora:

    anillo_plano = espiral and capa == 0 and (base_solida or capas_base >= 1)

`cupon_v2400`: de NO IMPRIMIBLE (puente de 153.7 mm) a **IMPRIMIBLE**, 0 de
96 486 muestras sin apoyo.

**Control:** el hongo se regenera BYTE A BYTE idéntico a `hongo_latest.gcode`
—el que está impreso— porque tiene `base_solida` y ya entraba por esa rama.

## ARREGLADO: el "peor ángulo" se muestreaba con 32 muestras fijas

`N_ANG = 32` dentro de `generar_pieza` gobierna `_pendiente` y `_delta_radio`.
Con 9 caritas por vuelta eso son 3.5 muestras por cara: la rejilla de 32 y las
9 caras baten entre sí y el resultado depende de dónde caigan las muestras, no
de la pieza.

    N_ANG=32   pendiente  72.0..173.6  ->  extrusión 1.048..1.253   19.6 %
    N_ANG=128  pendiente 144.6..173.6  ->  extrusión 1.181..1.253    6.1 %
    N_ANG=720  pendiente 168.1..173.6  ->  extrusión 1.239..1.253    1.1 %

Ese 19.6 % es el bandeado del mapa de CAUDAL de Orca, y explica por qué las
bandas no coinciden con los ojos ni con la boca: son moiré, no geometría.

Ahora `N_ANG = max(32, min(segmentos_por_capa, 360))`. No mueve ninguna pieza
sin variación angular —un sólido de revolución devuelve lo mismo en 32 ángulos
que en 360—, verificado con el hongo byte a byte.

## NUEVO: `paso_fijo` en `generar_pieza`

`marcha_vertical` está pensada para CÚPULAS: acorta el paso donde la pared se
tumba. En una pared VERTICAL con relieve angular el corrimiento entre vueltas es
RADIAL, y ahí su criterio `hypot(dz, dR) <= altura_capa` mide mal — trata el
corrimiento radial como si fuera vertical, cuando el cordón mide 1.2 mm de
ancho radial contra 0.4 de alto.

Es la misma sospecha que quedó abierta más abajo en este archivo ("la regla
Δradio por vuelta < ancho de cordón es más estricta que lo que hace la pieza
real"). `paso_fijo` NO la cierra: es una salida opt-in y medida para las piezas
donde se puede comprobar que las vueltas siguen solapando.

`gen_rosca.py` decide sola, midiendo el peor salto radial a paso 0.30:

    clásico, perlas, ondas, círculos, cuadros, lienzos   0.27 mm   78 %  FIJO
    chevron                                              0.32 mm   73 %  FIJO
    moleteado                                            0.36 mm   70 %  FIJO
    caritas en relieve                                   0.39 mm   68 %  FIJO
    sellos de corazón                                    1.92 mm  -60 %  ADAPTATIVO
    sellos de estrella                                   1.67 mm  -39 %  ADAPTATIVO

Los sellos tienen cantos vivos en `d` —el eje vertical— y ahí ninguna vuelta de
paso fijo alcanza a solapar: se quedan con la marcha adaptativa. El umbral es
50 % de solape; el jarrón, impreso y funcionando, mide 39.5 %.

Resultado en las caritas: altura de capa 0.300 mm clavada (desvío 0.0074, era
0.0275 entre 0.230 y 0.383) y sección extruida plana al 2 % en el 98 % central,
contra el 0 % del hilo liso.

El paso se REDONDEA para que entre entero (`n = round(altura/paso)`). Marchando
de `paso` en `paso` y agregando el resto quedaba una última vuelta muñón: en un
cupón de 40 mm a 0.30 sobraban 0.10, o sea un cordón de 12:1 en el borde de
arriba.

## ARREGLADO: `verificar_rosca.py` no corría

Dos cosas, las dos de arrastre:

1. El módulo se cargaba por ruta suelta y `rosca.py` hace
   `from .envolvente_hembra import ...`. Sin paquete padre, el import relativo
   revienta. Ahora se registra un `lamparas` de mentira con sólo `__path__`, que
   no ejecuta el `__init__` real (el que arrastra fullcontrol).
2. El cuerpo hablaba del riel redondo de Ø11 (`perfil_maestro`, `A_MAESTRO`,
   `R_BARRENO`, `R_CRESTA_MAX`), que ya no existe: la hembra real se midió de
   `tuerca.stl`. Reescrito contra la envolvente.

Dos trampas al medir, por si vuelve a pasar:

- Hay que pedirle a `rosca()` `ancho_cordon=0`, o sea la SUPERFICIE. Con el
  medio cordón descontado se mide el eje del recorrido contra el techo del riel
  y da contención -0.59 mm y apoyo 0.0 % en las nueve variantes.
- La tolerancia de contención es 0.01 mm, no cero. La envolvente y el perfil
  clásico son dos tablas de 270 muestras interpoladas y evaluadas en 720
  ángulos: el propio STL de referencia da +0.0088 mm.

## ARREGLADO: el render sólido rayaba las cúpulas (extensión gcode-preview)

`buildSolid` dibujaba una cinta VERTICAL por segmento. Eso cierra una pared
vertical y nada más: en una cúpula la vuelta siguiente sube 0.15 mm y se corre
1.26 en radio, así que la cinta tapa los 0.15 y deja el corrimiento al aire. Por
eso el rayado aparecía en TODOS los modos de color — el defecto era de la malla.

Ahora la cinta va hasta la vuelta de arriba, con dos correcciones que hacen
falta y que explican por qué el intento anterior rompió el piso:

- **Sólo las componentes radial y vertical.** El puntero de ángulo acumulado
  para en el primer punto PASADA la vuelta, o sea hasta un segmento entero de
  más: sobre R=115 mm son 3 mm de cuerda contra 0.3 de corrimiento radial real.
  Con el vector crudo la cinta sale torcida de costado por discretización.
- **Un solo límite, el largo del vector.** La guarda vieja era `dz <= 4*decl`,
  y donde la pared se acuesta `decl` cae a 0.05 mientras la vuelta de arriba
  sigue a 0.15: saltaba en unos segmentos sí y otros no, mezclaba cintas
  inclinadas con verticales que se cruzan, y el z-buffer alternaba. Moteado.

El piso plano (uz = 0) sigue con cinta vertical, igual que antes.

Comprobado ejecutando la `buildSolid` real en node sobre `hongo_latest.gcode` y
rasterizando con fondo magenta: los agujeros desaparecen, y el piso —que antes
se veía de canto, o sea nada, mirado desde abajo— ahora es una superficie.

## ABIERTO: el sombreado agrupa mal las capas en piezas de paso adaptativo

La malla está sana —comprobado ejecutando la `buildSolid` real en node sobre
`hongo_latest.gcode`, con su `computeSombra` y su material, y sale una esfera
limpia—. Pero el usuario sigue viendo mal el hongo en SOLID, y hay un sitio
donde mi reproducción no es fiel: **de dónde salen las capas**.

El lector de la extensión NO usa las marcas `;Z:`. Agrupa por Z real con UNA
sola altura estimada (`estimateLayerHeight`):

    let l = Math.round((segZ[s] - bbox.minz) / layerH);

En el hongo el paso adaptativo va de 0.05 a 0.8 mm. Con una altura única, cerca
del ápice —donde el paso se desploma— **muchas vueltas caen en la misma capa**.
Y `computeSombra` se apoya en esa numeración para todo:

- el ajuste de circunferencia por capa (con vueltas de radios distintos
  mezcladas, el centro no significa nada),
- `dr/dz`, que toma `zCapa[L] - zCapa[L-1]` del primer segmento que ve,
- el anillo `(capa, sector)`, que se queda con el radio MÁXIMO del sector.

`buildSolid` no depende de `layerAt` —usa `;HEIGHT:` y el ángulo acumulado— así
que la malla se salva; lo que se ensuciaría es el COLOR, y sólo en la zona donde
el paso colapsa.

**Es una hipótesis, no está confirmada.** Falta reproducirla con el binning real
(quedó a medias: `estimateLayerHeight` llama a `extrusionCentre`, que hay que
extraer también) y, sobre todo, falta una captura del modo SOLID + SOMBRA para
saber qué se está viendo.

## LO QUE SIGUE

1. **Imprimir `cupon_v2400`.** 40 mm, ~20 min, ahora sí IMPRIMIBLE. Es el único
   número que ningún script da: si el hilo hueco de un cordón aguanta. De eso
   depende que `ondas` (30 % de apoyo) y `perlas` (42 %) sirvan.
2. `test_verificar.py` tiene 1 de 13 casos fallando —"el piso de altura de
   cordón se mide sobre el recorrido"— y viene de antes. Hasta arreglarlo, los
   veredictos de `verificar_pieza.py` cargan esa duda.
3. El centrado de los rasgos de las caritas en la meseta del riel (v0 = +1.68)
   mide mejor en todo y DESHACE el dibujo. Sigue sin entenderse; está anotado
   en `rosca.caritas_relieve`.

---

# Estado al cerrar la sesión del 11-08-2026 (segunda parte)

## Lo primero: NADA se imprime todavía

Durante esta sesión escribí en este mismo archivo que la lámpara glitch
"FUNCIONA". **Era falso.** El verificador que lo respaldaba tenía cuatro bugs, y
el usuario lo desmintió en diez segundos abriendo el modo solape del preview: la
pieza salía roja entera. Con el verificador arreglado, esas mismas lenguas miden
**48.8 % sin apoyo y 307 puentes de hasta 62 mm**.

## ARREGLADO: la línea imposible del hongo

`comun.py` escalaba la sección de extrusión con la componente VERTICAL de la
vuelta:

    fc.ExtrusionGeometry(width=perfil.ancho, height=subida)      # mal

El razonamiento que lo puso ahí era que con altura fija "se empujaba plástico
para 0.40 mm en un hueco de 0.20". Pero ese hueco no es `subida`: donde la pared
se tumba, la vuelta siguiente no se apoya encima sino AL LADO, y el hueco real
es la separación medida SOBRE LA SUPERFICIE, `hypot(subida, Δradio)`. Y esa
separación es justamente lo que `marcha_vertical` mantiene constante: para eso
divide por `sqrt(1+tan²)`. Escalar la extrusión con la componente vertical
descuenta dos veces el mismo coseno.

Ahora se reconstruye la separación desde la propia subida:

    tan_v = _pendiente(ts[capa]) / altura
    separacion = min(subida * sqrt(1 + tan_v**2), 1.5 * altura_capa)

**Lo encontró la comparación vuelta por vuelta con `Squeezy Fidget Toy.gcode`**,
que el usuario señaló como la referencia correcta:

    Squeezy   separación 0.800 constante · área 0.960 CONSTANTE
    hongo     separación 0.400 constante · área 0.330 -> 0.063

Las dos mantenían bien la separación. La única diferencia era la extrusión.

Resultado, medido (`output/hongo_fix.gcode`):

    recorrido con cordón < 0.10 mm     área mediana    área arriba
    hongo antes     4.07 %                0.366        0.100 .. 0.063
    hongo ahora     0.20 %                0.480        0.480 constante
    Squeezy         0.22 %                0.960        0.960 constante

La geometría no se tocó: solo cuánto material se deposita. `hongo` queda con el
mismo comportamiento que la referencia y algo mejor en el número.

**Esto afecta a TODA pieza generada por `generar_pieza`**, no solo al hongo.

## Cómo es Squeezy, que hay que tener en cuenta al medirla

Son DOS CÚPULAS con una celosía en el medio, no una espiral simple. La celosía
cruza, así que **el ángulo no avanza de forma monótona** (6898 pasos adelante,
16346 atrás) y cualquier detección de vueltas por acumulación de ángulo da
basura sobre la pieza entera. Hay que medir cada cúpula por separado (z 0..28 y
z 70..97); el área lo confirma: 0.969 abajo, 0.501 en la celosía, 0.960 arriba.

Con eso se sostiene una afirmación anterior que era falsa y queda RETIRADA: dije
que Squeezy "corre 2.2 mm de radio por vuelta con 1.17 mm de capa, 62° de
voladizo". Salía del detector de vueltas roto. Lo real en la cúpula superior es
dz de 0.794 a 0.202 y dr de -0.091 a -0.774, con la separación clavada en 0.800.

## Lo que sigue sin estar calibrado, y bloquea los veredictos

El criterio de CONTACTO todavía no sirve: sobre `Squeezy`, que es un objeto
impreso y viable, mide **56.32 % sin apoyo**. Hasta que la herramienta diga que
Squeezy está bien, ningún veredicto suyo sobre otra pieza vale.

Pista de por dónde va: en modo vaso la vuelta de arriba queda EXACTAMENTE
tangente a la de abajo (dv = alto por construcción), o sea justo sobre el borde
del elipse, y el criterio es un filo de cuchillo que cualquier ruido cruza. Los
percentiles del elipse en las piezas conocidas están medidos y guardados en el
razonamiento de esta sesión: Squeezy p50 1.29, vase p50 1.03, hongo p50 1.04.
Un umbral fijo en 1.0 reprueba a las tres.

## La cabeza del hongo: arreglada y verificada

`output/hongo_fix.gcode`. Dos defectos reales de la pieza y varios de las
etiquetas del visor.

### Lo que afecta a la pieza impresa

1. **La extrusión seguía la subida vertical en vez de la separación sobre la
   superficie.** Dejaba 0.157 mm de pared en la cúpula —papel de seda— y el
   4.07 % del recorrido con cordón por debajo de 0.10 mm, contra el 0.26 % de
   `Squeezy Fidget Toy.gcode`. Ahora: **0.480 mm²/mm constante en 106 021
   segmentos**, y 0.00 % de recorrido fino.
2. **`capas_transicion` atenuaba el paso en piezas sin patrón**, dejando las
   primeras cinco vueltas en 0.067–0.333 mm: un anillo de cordón imposible en la
   base. Ahora solo se atenúa si hay variación angular.

La silueta NO cambió: el radio máximo cada 8 mm difiere entre −0.86 y +1.59 mm
respecto del original.

### Lo que es solo visual

Todo lo demás fueron comentarios. **Comprobado: los 110 102 movimientos del
g-code aparecen idénticos en el 3mf injertado, 0 distintos.** Ver `MAPA.md` para
los nombres exactos de las etiquetas de Orca — el que costó horas fue
`; LINE_WIDTH:`, que no es `;WIDTH:`.

## Herramientas nuevas

- `verificar_capas.py` — coherencia de las marcas de capa. **Correrlo sobre el
  3mf injertado, no solo sobre el g-code crudo**: los tres bugs de etiquetas
  vivían en el injerto y este verificador existía sin que yo lo apuntara ahí.
  Su invariante original (`Z_HEIGHT[i]−Z_HEIGHT[i−1] == LAYER_HEIGHT[i]`) estaba
  mal: suponía que las capas embaldosan, y en modo vaso con la pared acostada el
  cordón mide más que la separación y se solapan a propósito. Marcaba 421 capas
  "rotas" que estaban bien.
- `npm run reinstall` **arreglado**: tenía una ruta de macOS desde el commit que
  lo creó, así que nunca corrió en esta máquina. Ahora actualiza las dos
  instalaciones de VS Code (servidor WSL y Windows), que era otra fuente de
  confusión: `code --install-extension` toca solo una.

## La lámpara glitch: `output/glitch9.gcode` pasa los tres criterios

Es **la forma exacta de `glitch2`** —mismos parámetros de `glitch2.params.json`,
`--pe solo_afuera=1`— generada con `recorrido.pasos_pantalla_glitch`, que rellena
el hueco radial con pasadas planas concéntricas en vez de comprimir la espiral.

    línea fina   0.00 %   contra 0.26 % de la referencia
    contacto     0.02 %   contra 1.88 %
    puentes      0        contra 1
    -> IMPRIMIBLE

**No está impresa.** Lo verificado es el g-code.

### Las tapas que faltaban, por fin medidas bien

`verificar_tapas.py`. Corta la pieza en rebanadas de un cordón de alto por
sectores de 1°, ordena los radios con material dentro de cada celda, y un hueco
mayor que un cordón entre dos radios consecutivos es un anillo destapado.

    hongo_fix (cúpula lisa, control)                 0 anillos ·    0 cm²
    glitch7  espiral, sectores adentro y afuera    851 anillos · 194.4 cm²
    glitch8  espiral, solo hacia afuera            632 anillos ·  80.6 cm²
    glitch9  pasadas planas                        305 anillos ·  20.4 cm²

Los intentos anteriores medían la separación entre vueltas **ordenadas por z**, y
eso da el resultado al revés: donde hay relleno plano conviven muchos puntos a la
misma altura, el orden por z los mezcla, y la pieza rellena medía PEOR que la que
tiene el agujero. Por eso una medición dijo que las pasadas planas empeoraban.

Queda un residuo de 20.4 cm² sin explicar. Es el próximo hilo.

## El criterio de contacto, calibrado y en el script

Modelo de cordón: **rectángulo con los lados redondeados** —un núcleo plano de
`(ancho - alto)` con semicírculos— no un elipse. El núcleo plano es lo que hace
que un corrimiento horizontal chico no cueste margen vertical, que es lo que hace
el modo vaso. Con el elipse la tangencia del modo vaso caía sobre el borde del
criterio y la referencia buena daba 56 % sin apoyo.

Las dos direcciones no son simétricas y tratarlas igual fue el error caro:

- **vertical**: holgura de 1.10, porque `dv = alto` es tangencia de construcción.
- **lateral**: se exige solape real. Dos cordones a un ancho exacto se ROZAN.

Validado: aprueba el jarrón (0.11 % sin apoyo) y las cúpulas de Squeezy (1.88 %),
y `hongo_fix` sale mejor que los dos (0.00 %). 13 casos sintéticos, 0 fallando.

### El criterio de CHOQUE queda fuera del veredicto

Marca el **39.51 % del jarrón**, que está impreso y funciona. Un criterio que
condena a la referencia no sirve para juzgar. Se sigue informando, porque es útil
para comparar dos versiones de la misma pieza, pero no decide. Arreglarlo o
enterrarlo es trabajo pendiente.

## Los cuatro bugs del verificador, y cómo se encontró cada uno

Ninguno se veía mirando una pieza de 180 000 segmentos. Por eso ahora existe
`test_verificar.py`: doce casos de cuatro líneas de g-code con la respuesta
sabida de antemano. **Antes de creerle un número al verificador, se corre.**

1. **El `M83` vive en el start gcode**, y el lector empezaba después del
   marcador de fin. El archivo parecía de extrusión absoluta y TODOS los
   cordones daban 0.000 mm de alto. Lo encontró la referencia.
2. **La holgura aplicada también en horizontal.** Con cordón de 1.8 aceptaba
   ejes separados 1.98 mm, o sea cordones que no se tocan. Lo encontró el
   usuario con el preview.
3. **La rejilla indexaba solo los extremos de cada segmento y la búsqueda
   preguntaba por el punto medio.** Un segmento de 20 mm cae en siete celdas y
   no está en la del medio: era invisible. Con cordones de 1 mm casi no se
   notaba, pero los cruces radiales de un sector duro miden 38 mm — justo los
   que hay que medir. Lo encontró el banco de pruebas.
4. **Las fracciones de solape estaban elegidas a ojo** (0.85, 0.25, 0.70) y se
   contradecían: una exigía 35 % de sobre-extrusión para dar "apoyado", y otra
   llamaba choque a esa misma sobre-extrusión. Ahora sale de la geometría del
   cordón: dos pasadas planas se funden a `ancho - 0.215*alto`, que es lo que
   usa cualquier slicer para el relleno sólido.

**El patrón, que ya estaba anotado y volví a repetir:** cada vez que un número
salía bien, lo creí. Los cuatro bugs eran del medidor, no del generador.

## Dónde está cada pieza, medido con el verificador arreglado

    pieza      fabricab.  contacto   choque   puentes    veredicto
    hongo        5.45%      0.16%     0.13%      4       referencia
    glitch2     26.02%      3.80%     8.21%    237       NO
    glitch5      0.00%      6.53%     0.01%     62       NO  (lenguas)
    glitch6      0.00%      2.75%    20.85%    104       NO  (forma de glitch2)

## Lo que el usuario pidió, y es lo que hay que hacer

**La forma exacta de `glitch2.gcode`, funcionando.** No una forma nueva. Las
lenguas de `glitch5` fueron un desvío: aunque hubieran verificado, no son lo
que se pidió.

`glitch6` es esa forma —mismo campo de deformación, sacado de
`glitch2.params.json`— generada con pasadas planas en vez de espiral apretada.
Va por buen camino en lo que importaba:

- **Fabricabilidad resuelta.** Todos los cordones a 0.400 mm, contra 26 % de
  irrealizables en `glitch2`. El paso vertical no se comprime nunca porque la
  pared no se tumba: el hueco radial se rellena de costado.
- Falta el **choque**: 20.85 %. Las pasadas de relleno se reparten dividiendo el
  salto en partes iguales, y cuando el resto cae mal quedan demasiado juntas.
  La ventana entre "no se tocan" y "se pisan" es estrecha (1.2 a 1.71 mm con
  cordón de 1.8) y el reparto uniforme no la respeta siempre. Lo que hace un
  slicer de verdad en ese caso es **variar el ancho de extrusión** de la última
  pasada. Eso es lo que falta implementar.
- Y los **puentes**: 104 tramos, los peores de ~160 mm, en `base` y en los
  cambios de bloque. Sospecha a confirmar: cuando el patrón de sectores cambia,
  la cara radial aparece en un ángulo nuevo y no tiene nada debajo. **No está
  verificado, es una hipótesis.**

## Sobre el paso adaptativo: la pregunta del usuario que hay que terminar

El usuario preguntó por qué `hongo` necesita líneas tan finas cuando
`Squeezy Fidget Toy.gcode` —básicamente la misma figura— no. Medido:

- `hongo`: 83 de 459 vueltas por debajo de 0.10 mm de altura de capa, todas
  en z 113-116, donde el ala se acuesta. Verificado midiendo el ascenso por
  vuelta, sin dividir extrusión.
- `Squeezy`: 155 vueltas, mediana 0.484 mm, **solo 2** por debajo de 0.10.
  En su zona más inclinada corre **2.2 mm de radio por vuelta con 1.17 mm de
  altura de capa** —62° de voladizo— y el área de extrusión ahí es CONSTANTE.

O sea: la pieza de referencia se corre más de un cordón por vuelta y se imprime
igual. La regla "Δ radio por vuelta < ancho de cordón" que gobierna
`comun.marcha_vertical` es más estricta que lo que hace la pieza real, y es esa
regla la que desploma `dz` hasta 0.05.

**Esto NO está cerrado.** La comparación mezcla las pasadas concéntricas del
piso de `hongo` con las vueltas de pared, así que el lado de `hongo` de esa
tabla no está limpio. Antes de tocar `marcha_vertical` hay que rehacer la
medición separando piso de pared — con etiquetas al emitir, no por geometría.

## Herramientas nuevas, en el repo

- `verificar_pieza.py` — cuatro criterios (fabricabilidad con piso absoluto de
  0.10 mm, contacto, choque, puentes), por muestras a lo largo del cordón y
  separados por la etiqueta `;TIPO:` que deja el generador.
- `test_verificar.py` — doce casos con respuesta conocida. **Correr esto antes
  de creerle un veredicto al verificador.**
- `vista_gcode.py` — frontal y planta a PNG, sin dependencias.
- `gen_glitch6.py` — la forma de glitch2 con pasadas planas.

## Lo primero que haría la próxima sesión

0. Calibrar el criterio de contacto hasta que apruebe a Squeezy y al jarrón.
   Sin eso no se puede afirmar nada de ninguna pieza.
1. Variar el ancho de extrusión de la última pasada de relleno en
   `_radios_pasada`, para cerrar el 20.85 % de choque de `glitch6`.
2. Confirmar o descartar la hipótesis de los puentes en los cambios de bloque,
   etiquetando los cruces radiales al emitirlos.
3. Terminar la comparación con `Squeezy` con las etiquetas puestas, y si se
   confirma, aflojar `comun.marcha_vertical`.

---

# Sesión anterior (11-08, primera parte)

## Lo que funciona y está verificado

**La cabeza del hongo** (`output/hongo.gcode`) — silueta desde `gcodes/reference/hongis.dxf`,
piso anular con hueco de Ø33.30 compensado por el ancho de cordón, PETG 245/80,
ventilador apagado salvo los últimos 12 mm, velocidad rampada para mantener
~25 s por vuelta en toda la pieza. **0 vueltas sueltas**, solape mínimo 54 %.
Empaquetado en `hongo.gcode.3mf` con las temperaturas correctas.

**El esculpido en vivo** — se deforma el recorrido real a 60 fps, Ctrl+Z
instantáneo, y el campo de JS es idéntico al de Python (405 muestras, verificado).

**El importador de DXF** (`lamparas/perfil.py`) — lee el documento entero de
Fusion, elige la curva más larga que más altura recorre, evalúa las splines con
De Boor. Encuentra los círculos, de donde salen los huecos.

**La pantalla glitch** (`output/glitch2.gcode`) — cono clásico con una banda de
sectores duros corrida de lado. **0 vueltas sueltas de 577, solape mínimo 56 %**,
40 mm de excursión. Es la primera versión del glitch que se imprime, y lo que la
desbloqueó fue el arreglo de la marcha vertical (abajo).

**Las lenguas planas** de `recorrido.pasos_lampara_glitch2` — 34 alturas,
separación de 1.27 mm entre arcos concéntricos contra 1.2 de cordón, vuelan
33 mm. Se sostienen de costado.

## El arreglo que desbloqueó el glitch

`comun.marcha_vertical` medía la pendiente del **radio medio** de cada vuelta.
Una deformación angular —que saca la pared por un lado y la mete por el otro— no
mueve el radio medio: el generador creía que la pared seguía vertical, no frenaba,
y las vueltas quedaban separadas varios milímetros en radio mientras la Z subía
0.4. Entre ellas, huecos. Era el defecto que se veía en el render como escalones
"mega separados".

Ahora mide el **peor ángulo**: muestrea 32 direcciones y se queda con la que más
se corre. El paso se desploma a 0.050 mm justo en los escalones y las vueltas se
acuestan una contra otra.

    antes:  400 vueltas · Δz 0.400 constante · 16 sueltas
    ahora:  578 vueltas · Δz 0.050 .. 0.389  ·  0 sueltas · solape 56%

Cuesta 178 vueltas más, todas en la banda. Las piezas lisas no cambian: sin
variación angular, el peor ángulo y el medio dan lo mismo.

## Lo que está roto, y hay que borrar o arreglar

- `estructura.aletas` — tira `TypeError` en `estructura.py:676`. **No se usa.**
- `estructura.glitch` y `glitch2` — sumas de armónicos. Ver abajo por qué no
  sirven. Candidatas a borrar.
- `output/glitch.gcode` — 36–50 vueltas sin apoyo. **No imprimir.**
- La medición que separa "pared" de "lengua" filtra por radio y contamina el
  conteo: los primeros arcos de una lengua nacen pegados a la pared. Hay que
  **etiquetar los puntos al emitirlos**, no adivinarlos después por geometría.
  Hasta entonces, el número de vueltas sueltas de la pared no es confiable.

## El problema abierto: la lámpara glitch

Es lo que el usuario pidió desde el principio. Un dibujo a mano: pantalla cónica
clásica con una banda en el medio que se rompe, corrida hacia la derecha, con
cortes rectos y líneas que salen y entran.

**Seis intentos fallidos, y por qué:**

1. Todo lo que sea **suma de senos no puede hacer un corte** — es suave en todas
   partes por definición. Salían lámparas derretidas. Ese fue el error de
   `glitch`, `glitch2` y de todas las versiones con armónicos.
2. Un **corte duro entre dos vueltas** deja la vuelta nueva sin apoyo. Con
   bordes duros (`glitch3`) el techo medido es **6 mm de salto** con cordón de
   1.8, y ahí queda con 11 % de solape.
3. Estuve tratando de expresar una **topología de recorrido** cambiando la
   función del radio. Son cosas de distinto tipo. Por eso existe `recorrido.py`.

**Resuelto para la pantalla de sectores duros** con el arreglo de la marcha
vertical. Queda abierto para la versión con lenguas.

**La dirección correcta, que fue idea del usuario:** no elegir entre las dos
técnicas, **combinarlas en capas distintas**.

- La **pared** sigue siendo una espiral continua y suave: se ondula y se corre,
  pero poco, y es lo que sostiene la pieza.
- Las **lenguas** son lo violento: salen de la pared, corren a Z constante y
  vuelven. No piden apoyo vertical.

Eso está implementado en `recorrido.pasos_lampara_glitch2` y las lenguas ya
verifican. Falta confirmar la pared con una medición honesta.

## El límite físico que quedó identificado (y su salida)

Con `salto=38` no hay configuración buena, y el motivo no es geométrico sino
físico. Donde la pared se tumba, el paso adaptativo baja `dz` hasta 0.05 mm para
que las vueltas se toquen, y la extrusión lo sigue. Pero **un cordón de 1.8 mm de
ancho por 0.05 de alto no existe**: una boquilla de 0.8 no tiende una cinta así,
sale un hilo. Es lo que Orca pinta azul oscuro en la vista de ancho de línea.

Medido sobre `glitch2.gcode`, con el medidor por segmento:

    paso≥0.05 bloq=9   cordón 0.052 mm       —
    paso≥0.05 bloq=4   cordón 0.140 mm    1161 sin apoyo (0.42%)
    paso≥0.15 bloq=4   cordón 0.177 mm    5032 (2.25%)
    paso≥0.25 bloq=4   cordón 0.251 mm    5830 (3.08%)

Subir el paso mínimo engorda el cordón y **empeora** el apoyo: las dos curvas van
en la misma dirección, no hay punto medio.

**La salida, que fue idea del usuario:** hacer lo mismo que las aletas flotantes.
Ellas mantienen el grosor porque no dejan que el paso se desplome — se imprimen a
Z CONSTANTE con pasadas al lado, cada una con su altura de cordón completa. La
espiral hace lo contrario: comprime el paso hasta que el cordón deja de ser
realizable.

Aplicado a la banda: detectar las zonas casi horizontales y emitirlas como
pasadas planas (`recorrido.py` ya sabe hacerlo) en vez de como espiral apretada.
Ahí el cordón se mantiene en 0.4 mm y el apoyo es lateral, sin tocar el diseño.
Es la unión de las dos técnicas, ahora por el lado de la física y no solo de la
geometría.

## Medir el solape: usar el medidor por segmento

`/tmp/solape.py` (conviene moverlo al repo) recorre todos los segmentos y busca
en una grilla espacial el material más cercano que esté debajo. Es lo mismo que
hace el modo solape del preview.

**No usar el conteo por vueltas**: mide el radio en un solo ángulo (el rayo +X) y
por eso reportó "0 vueltas sueltas" en una pieza que tenía 1161 segmentos al
aire. Mismo error que el radio medio contra el peor ángulo, cometido en la
herramienta de medir.

## La lámpara glitch: diagnóstico final (11-08, cierre)

**Ninguna versión se imprime.** Con los tres criterios medidos juntos:

    glitch2.gcode   35.6% de los cordones son IRREALIZABLES
                    (1.8 mm de ancho por 0.05 de alto = 36:1 con boquilla 0.8)
                    + 2949 puentes de hasta 68 mm al aire, con 20 mm de
                      filamento cada uno: se descuelgan por su propio peso
    glitch3.gcode   81.5% de los cordones no tocan a ningún vecino
                    (paso fijo en 0.4 = exactamente la altura del cordón:
                     se rozan en el límite, no se montan)

**La causa, y es un error de diseño mío, no un límite físico.** Yo describí esto
como "la banda pide que la pared se acueste tanto que o el paso se comprime hasta
un cordón imposible, o las vueltas no se tocan". Eso es falso, y el usuario lo
corrigió: el problema es que **nunca combiné las dos metodologías**.

- En `glitch2` metí el glitch DENTRO de la pared. Eso la obliga a acostarse, el
  paso adaptativo se comprime, y el cordón deja de ser fabricable.
- En `glitch3` reemplacé la espiral entera por pasadas planas.

Las dos veces elegí una técnica. Lo correcto es:

- **La pared sigue siendo una espiral normal**: vertical, paso 0.4, cordón
  1.8×0.4 fabricable, cada vuelta apoyada en la anterior. No se deforma casi
  nada. Es la que sostiene la pieza y nunca entra en la zona imposible.
- **El glitch va ENCIMA**, como estructura aparte: lenguas y repisas planas que
  salen de la pared, corren a Z constante y vuelven. Se apoyan de costado, no
  debajo, así que no le piden nada al paso vertical.

`recorrido.pasos_lampara_glitch2` es el esqueleto de eso y sus lenguas ya
verificaban (1.27 mm entre arcos contra 1.2 de cordón, 33 mm de vuelo). Lo que
falta es no tocar la pared en absoluto y poner todo el efecto en las lenguas.

## Los TRES criterios, que hay que medir juntos

Cada veredicto equivocado de esta sesión salió de medir uno solo:

1. **Fabricabilidad**: el cordón que se le pide a la boquilla tiene que existir.
   Relación ancho/alto por encima de ~10:1 con boquilla 0.8 ya no sale.
2. **Contacto**: `(dh/ancho)^2 + (dv/alto)^2 <= 1`. Comparar la distancia cruda
   contra el ANCHO da por sobre-extruida la vecindad vertical normal del modo
   vaso —las vueltas van a 0.4 en Z, que es correcto— y de ahí salió un
   "89% sobre-extruido" que era falso y me llevó a romper lo que funcionaba.
3. **Puentes**: un tramo largo sin apoyo se descuelga aunque tenga material.
   Darle el cordón completo lo empeora: pasa de hilo a soga.

Referencia validada: `hongo.gcode` da 1.22% suelto, y todo en z0 (las líneas de
purga, que no tienen vecino por definición).

## Por qué no se hizo, y el plan acordado

El usuario propuso combinar las dos técnicas desde temprano y lo repitió varias
veces. No se hizo, y **no fue por dificultad de cálculo**. Se implementó —
`recorrido.pasos_lampara_glitch2`, pared lisa continua más lenguas planas — y las
lenguas verificaron bien (1.27 mm entre arcos contra 1.2 de cordón, 33 mm de
vuelo). Después medí la pared con un filtro que la separaba de las lenguas por
radio; los primeros arcos de cada lengua caían del lado equivocado, dio 36
vueltas sueltas, y concluí que el enfoque fallaba. Me fui a `glitch3`.

**Ese es el patrón a no repetir: cada vez que un número salía mal, cambié el
diseño en lugar de revisar la medición.** Varias de esas mediciones estaban mal
calibradas. Se abandonó el camino correcto porque un medidor roto dijo que no
funcionaba.

Que no es difícil lo dicen los números: la pared sin tocar es la misma espiral
del hongo, que mide 1.22% de cordones sueltos (todo líneas de purga, que no
tienen vecino por definición). Las lenguas ya verificaron. Combinarlas es dejar
la pared en paz —deformación casi nula— y poner toda la amplitud en las lenguas.

### Plan acordado para la próxima sesión

1. **Etiquetar cada punto como pared o lengua AL EMITIRLO.** Nada de deducirlo
   después por geometría: es lo que hizo abandonar el enfoque bueno. Con la
   etiqueta, cada parte se mide con su criterio y el primer número ya es fiable.
2. **Pared del cono limpia, sin tocar.** Espiral normal, paso 0.4, cordón
   1.8×0.4 fabricable. Es la que sostiene la pieza y nunca entra en la zona
   imposible.
3. **Lenguas COLOCADAS A MANO, no generadas al azar.** Una lista explícita —
   altura, ángulo, cuánto vuela, qué arco abarca— de ocho o diez, que el usuario
   ajusta. Dos ventajas concretas sobre la aleatoriedad: se verifica lengua por
   lengua en vez de en promedio, y el resultado se parece a los dibujos del
   usuario, que tienen las lenguas en lugares concretos. Veintiséis al azar nunca
   iban a dar eso.
4. Medir con los **tres** criterios juntos (fabricabilidad, contacto, puentes)
   antes de dar cualquier veredicto.

## Lo primero que haría la próxima sesión

1. Etiquetar los puntos como pared/lengua al emitirlos, y medir cada uno con su
   criterio. Sin eso no se puede afirmar nada sobre `glitch.gcode` — la pantalla
   de sectores duros (`glitch2.gcode`) ya no lo necesita, porque ahí no hay
   lenguas y la medición de vueltas es limpia.
2. Con eso, subir `vuelo` y `lenguas` hasta el límite real.
3. Meter `pasos_lampara_glitch2` en la CLI de `lamparas.bowls` para que sus
   parámetros aparezcan como sliders en el preview. Hoy están en un script suelto.
4. Borrar las estructuras de glitch fallidas.

## Nota de proceso

En esta sesión entregué dos g-codes rotos describiéndolos como buenos, e inventé
una pieza (la lámpara de aletas) que nadie había pedido, a partir de fotos que el
usuario mandó como ejemplo de qué se puede imprimir. Los avances reales de la
última parte —la topología del recorrido y la combinación de técnicas— fueron
correcciones suyas, no mías. Conviene preguntar antes de asumir el objetivo, y
medir antes de reportar.
