# Tanda FINAL — la rosca con la pared corregida

Todo lo de `output/rosca/prueba/` quedó viejo. Lo que cambia acá es **cuánto
plástico se deposita**, no la geometría: las trayectorias son las mismas.

A LA ALTURA REAL: los machos miden **230 mm** (17 vueltas de rosca) y la
tuerca los 28 mm que mide su STL.

    archivo                                  alto     recorrido   tiempo   peso
    macho_clasico_v1823.gcode               229.8 mm    242.9 m   2.22 h   52 MB
    macho_caritas_relieve_v1775.gcode       229.8       243.7     2.29     52
    macho_caritas_intercalada_v1774.gcode   229.8       246.4     2.32     52
    macho_perlas_v1846.gcode                229.8       247.3     2.23     52
    macho_interrumpida_v1824.gcode          229.8       247.2     2.26     52
    hembra_v1878.gcode                       28.3        43.3     0.38      2

    macho_clasico              el ajuste, el caso más justo
    macho_caritas_relieve      el dibujo original
    macho_caritas_intercalada  ojos de línea, feliz/triste alternadas
    macho_perlas               hilo estrangulado 20 veces por vuelta
    macho_interrumpida         hilo cortado en 6 sectores
    hembra                     la tuerca en modo vaso

En `cupon_40mm/` están las mismas cinco piezas cortadas a 40 mm (3 vueltas,
~20 min cada una), más las dos de `pastillas`: discos que sobresalen con
corazón, estrella, carita y raya HUNDIDOS, en damero. Sólo existen como cupón.

    macho_pastillas_v1326.gcode      Ø8.40, 32 por vuelta   juego axial 0.94 mm (7 %)
    macho_pastillas_max_v1329.gcode  Ø9.25, 30 por vuelta   juego axial 0.16 mm (1 %)

Las dos ENTRAN (+0.096 y +0.097 mm) y las dos son IMPRIMIBLES con paso fijo. Lo
que las separa es el JUEGO: un disco más ancho llena más el canal del hilo. El
par que ya enrosca mide 4.08 mm de juego y baila un poco; el máximo teórico del
diente más gordo posible da 0.28. O sea que la `max` queda MÁS APRETADA que ese
máximo y no deja nada para la variación del plástico — puede trabarse. Están las
dos justamente para que lo decida el plástico.

Al lado están sus renders: `_banda_altura` (gris = radio, el que no miente sobre
dónde está cada figura), `_banda` sombreado, e `_impreso`, que filtra con el
diámetro de boquilla para mostrar cómo va a salir de verdad. Misma geometría y mismos arreglos: sirven para probar el
encastre sin gastar 2.3 h.

Todas: pared **1.0 mm**, **1440 segmentos** por vuelta, PLA a 220 / cama 65 /
ventilador 75 %, tramo gordo clavado en 12.0 mm3/s.

## Los dos arreglos

### 1. La pared salía un 32 % más gruesa de lo pedido

`generar_pieza` escala la extrusión con la SEPARACIÓN entre vueltas sobre la
superficie —lo correcto, y lo que arregló la cabeza del hongo— pero usaba una
sola separación por vuelta: la del **peor ángulo**. En una cúpula da igual,
porque toda la vuelta se tumba lo mismo. En una rosca no: sólo los flancos del
hilo están a 43°, la cresta y el fondo son planos, y recibían igual la sección
del flanco.

`--separacion-por-angulo` la calcula en cada ángulo, contra la vuelta de arriba.

    pieza                    antes    ahora
    macho clásico            1.32     1.001
    macho caritas            1.39     1.007
    macho perlas                      1.005
    macho interrumpida                1.002
    hembra                   1.75     1.002    <- la peor: va en marcha adaptativa

Medido sobre las piezas de 230 mm en la ventana z 100..111, lejos de la base y
del remate.

Importa porque `rosca(ancho_cordon=1.0)` resta medio cordón para que la pared
caiga donde el diseño la quiere. Con la pared a 1.32 el medio cordón real era
0.66 y la cara impresa quedaba 0.16 mm por fuera, sobre una holgura de 0.20.

**Está APAGADO por defecto.** El hongo se regenera byte a byte idéntico.

### 2. El freno de caudal miraba la mediana y los picos se escapaban

Con la sección variable, capar por la mediana dejaba tramos a 14–18 mm3/s contra
el tope de 12 del PLA. Pedirle al extrusor más de lo que funde NO sale como
plástico de más: sale como línea fina, que es justo el defecto que se persigue.

Ahora se capa por el **p99 pesado por largo de recorrido**
(`velocidad.PERCENTIL_FRENO`). Por el máximo no: los picos son raros —el 0.1 %
del recorrido— y frenar por ellos costaba un 41 % de tiempo.

Todas las piezas de esta carpeta quedan con el tramo gordo clavado en 12.0.

## Qué medir cuando salgan

1. **Si las caritas se ven.** Es lo que decide entre las causas candidatas
   (resolución 1440, caudal, pared).
2. **Si enrosca sin raspar.** La holgura de diseño es 0.20 mm y ahora debería
   estar entera; antes quedaban 0.04.
3. La `intercalada` contra la `relieve`: misma boca, ojos distintos.

La hembra de esta carpeta es opcional — la que se venía imprimiendo sale del STL
laminado en Orca, y Orca yerra para el otro lado (deja la pared fina, así que el
barreno queda si acaso un pelo más ancho). Está acá por si se quiere el par
entero generado.
