# Tanda de prueba de impresión — la rosca

Una hembra y cuatro machos, todo g-code. Lo que se prueba no es cada pieza por
separado: es si **enroscan entre sí**. También podés enroscarlos en una caperuza
ya impresa, que es la referencia de verdad.

| archivo | qué es | qué prueba |
|---|---|---|
| `prueba_hembra_v2400.gcode` | la tuerca en modo vaso, 28 mm, un cordón | que el barreno salga a medida |
| `prueba_macho_clasico_v2400.gcode` | el hilo pelado | el ajuste, en el caso más justo |
| `prueba_macho_caritas_relieve_v2400.gcode` | los rasgos SON el hilo | el que menos apoya: 0.4 % |
| `prueba_macho_perlas_v2400.gcode` | hilo estrangulado 20 veces por vuelta | apoyo 3.9 % con el hilo entero |
| `prueba_macho_interrumpida_v2400.gcode` | hilo cortado en 6 sectores | el hilo que arranca y termina |

Todos miden bien sobre el archivo. Lo que ningún script puede decir es si el
plástico se comporta como la geometría — para eso son las piezas.

## La hembra

Sale de `mariposa_v3_hembra.stl` con `gen_tuerca.py`. No es una tuerca
inventada: el barreno se mide del STL y el g-code lo reproduce con **RMS
0.0079 mm** en toda la zona roscada.

    ./venv/bin/python gen_tuerca.py ../../gcodes/reference/tuerca/mariposa_v3_hembra.stl \
        --carpeta rosca/prueba --nombre prueba_hembra

**Modo vaso, un cordón de 1.20 mm, igual que los machos** — una sola espiral
continua: 2 movimientos sin extruir en todo el archivo, los mismos que tiene el
macho. Sin relleno, sin soportes, sin faldón, sin costura.

    barreno    R 50.217 .. 52.185      <- la rosca va por DENTRO
    exterior   R 53.4 aprox
    paso fijo 0.30 mm, peor salto radial 0.559 mm -> 53 % de solape

Con un solo cordón la cara de afuera copia la rosca, y eso no tiene arreglo: una
pared no puede dar dos superficies distintas.

**Chaflán de entrada de 3 mm**, y no es decoración. `generar_pieza` arranca la
espiral con una rampa, y en los primeros 2 mm la z impresa todavía no es la del
modelo: la fase va corrida y el radio sale hasta 0.55 mm fuera de sitio. En un
macho da igual —el pie queda gordo y no estorba— pero en una hembra eso AHOGA LA
BOCA justo por donde tiene que entrar el tornillo. El chaflán abre más de lo que
la rampa cierra, y como sólo quita material no puede interferir. Quedan 1.85
vueltas engranando.

Si hace falta la tuerca maciza —5 a 7 mm de pared y exterior cilíndrico de
verdad, como el STL— la misma orden con `--macizo`.

## Tres velocidades por pieza

Cada pieza está tres veces. La geometría es **idéntica byte a byte** en las
tres: sólo cambia la `F`, comprobado comparando las 47 521 líneas XYZ.

| sufijo | qué es | tiempo |
|---|---|---|
| `_v2400` | 2400 mm/min (40 mm/s) constante, lo que veníamos usando | x1 |
| `_lento_v2400` | 2400, bajando a 240 donde el cordón cuelga | x1.20 a x1.56 |
| `_v480` | **480 mm/min (8 mm/s) constante** | x5 |

De dónde salen esos números: medí `Squeezy Fidget Toy.gcode`, la referencia
impresa del repo. Su cuerpo tiene exactamente DOS velocidades, no un gradiente —
**480 normal y 240 en lo flotante**— y esa mitad sigue al voladizo y no a la
altura: de los segmentos a 240, el **70.4 % no tiene material debajo**, contra
el 12.3 % de los de 480.

**`_v480` es la que más se parece a Squeezy**: misma velocidad de pared, misma
física de cordón. Es la apuesta segura si lo que se quiere es reproducir lo que
ya se sabe que imprime bien.

**`_lento_v2400` es la traducción de su regla**, no de su número: frena donde
cuelga y corre donde apoya. Ojo con una cosa: 240 sobre 2400 es 0.10 de la
velocidad normal, mientras que en Squeezy 240 sobre 480 es 0.50. Y
`CIERRE-SUPERIOR.md` anota que el mínimo de Claywoven era 0.18 y que bajar
demasiado produce sobre-extrusión —su intento 2, el del bulto—. O sea que esta
versión frena MÁS de lo que nadie probó, no menos.

Por qué la modulación va dentro de la vuelta y no por altura: en una cúpula el
voladizo depende de z y alcanza una rampa. En una rosca el hilo sube y baja el
radio una vez por vuelta, así que a la MISMA altura hay ángulos apoyados y
ángulos al aire. Se mide punto contra punto, comparando con el que está una
vuelta más abajo en el mismo ángulo.

| pieza | peor voladizo | puntos frenados | tiempo |
|---|---|---|---|
| clásico | 27 % del cordón | 34 % | x1.56 |
| caritas_relieve | 78 % | 12 % | x1.20 |
| perlas | 80 % | 24 % | x1.22 |
| interrumpida | 165 % | 22 % | x1.41 |
| hembra | 40 % | 25 % | x1.33 |

El 165 % de `interrumpida` son los bordes de sector, donde el hilo arranca y
termina. La escala se toma del percentil 99 y no del máximo, justamente para que
esos 123 puntos no se coman toda la modulación del resto de la pieza.

## En qué orden

1. **La hembra y el clásico.** Son el par mínimo. Si estos dos no enroscan, los
   otros tres machos no aportan nada: todos salen del mismo perfil, sólo le
   quitan material.
2. **`caritas_relieve`**, que es el que te interesa y el que más riesgo tiene.
3. Perlas e interrumpida, si los dos primeros dan bien.

## Los números, y qué mirar en cada uno

Contra la hembra de esta tanda:

|  | holgura radial | solape | apoyo |
|---|---|---|---|
| clásico | +0.201 mm | 77 % | **10.4 %** |
| caritas_relieve | +0.208 mm | 66 % | **0.4 %** |
| perlas | +0.202 mm | 77 % | **4.0 %** |
| interrumpida | +0.202 mm | 77 % en el 99.73 % del recorrido | **6.7 %** |

**Que entren.** La holgura radial es ~0.20 mm en los cuatro. Es poco: del orden
de lo que engorda un cordón mal calibrado. Si raspa o no entra, no está mal la
geometría — está gorda la impresión.

**Cuánto cabecea, y esto es lo que hay que traer de vuelta.** Medido da **3.77 mm
de juego axial**, el 27 % del paso. Pero `envolvente_hembra.py` dice que el macho
actual tiene 0.45 mm, y los dos no pueden ser ciertos. Enroscá a fondo y fijate
cuánto sube y baja sin desenroscar: eso decide cuál vale, y es el único número de
toda la tanda que ningún script puede dar.

**Si `caritas_relieve` agarra.** Apoyo 0.4 % contra 10.4 % del clásico. Los
rasgos de las caras son el hilo, así que sólo tocan el riel en las puntas. Entra
igual y con más holgura que el clásico (+0.200), o sea que si falla no va a ser
por raspar: va a ser porque resbala bajo carga. Enroscá y tirá.

**Si perlas afloja.** Mismo ajuste y mismo solape que el clásico, pero apoyo
3.9 %: las perlas estrangulan el hilo justo en el lomo, que es lo que carga.

**Si `interrumpida` se sostiene.** En los bordes de sector el hilo empieza y
termina de golpe: hay 123 pares de vueltas (el 0.27 % del recorrido) donde el
radio pega un salto de 1.98 mm. En el otro 99.73 % se corre 0.276 mm, igual que
el clásico. La pregunta es si esos cantos salen limpios o se caen.

## Ojo con los nombres

`output/rosca/caritas_v2400.gcode` **NO** es el patrón `caritas`: es
`caritas_relieve` guardado con otro nombre en una sesión anterior. Se distinguen
por cuánto recorrido queda en el núcleo — 82 % el relieve, 43 % el grabado.
El de esta tanda es el relieve, el mismo que ese archivo.

## Cómo se verificó

    ./venv/bin/python verificar_encastre.py \
        --hembra output/rosca/prueba/prueba_hembra_v2400.gcode \
        'output/rosca/prueba/prueba_macho_*.gcode'

Mide el g-code contra `rosca.perfil_hembra`, la tabla sacada del barreno real de
la caperuza en `tuerca.stl` — comprobada con `medir_hembra.py`, RMS 0.02 mm.

También se puede medir contra una tuerca concreta, g-code o STL:

    ./venv/bin/python verificar_encastre.py \
        --hembra ../../gcodes/reference/tuerca/mariposa_v3.stl \
        'output/rosca/prueba/prueba_macho_*.gcode'

Contra la mariposa los cuatro entran con **+0.211/+0.217 mm** en vez de +0.191:
su barreno mide 0.023 mm más ancho que el nominal. El juego axial ahí da
**3.77 mm**, sobre una pieza real — más razón para medirlo a mano.
