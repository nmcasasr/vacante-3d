# Mapa: quién manda sobre qué

Existe porque los errores caros de este proyecto no fueron de cálculo. Fueron de
**territorio**: dos partes escribiendo la misma cosa, o una parte usando el
número de la otra. Cada trampa de acá abajo ya rompió algo, y dice qué síntoma
produjo, para reconocerlo la próxima vez.

## El camino de una pieza

    DXF / parámetros
        └─> lamparas/            genera la GEOMETRÍA y la EXTRUSIÓN
                └─> output/*.gcode          el cuerpo, sin plantilla
                        └─> ext-gcode/      INJERTA el cuerpo en una plantilla
                                            de Orca (bambu.ts)
                                └─> *.3mf   esto es lo que se abre en Orca
                                            y lo que se imprime

Los verificadores cuelgan del cuerpo, no del injerto.

## La frontera que más se rompió

| Cosa | La emite | El otro lado NO la toca |
|---|---|---|
| Puntos, radios, alturas | `lamparas/comun.py`, `lamparas/recorrido.py` | — |
| Sección de extrusión (`ExtrusionGeometry`) | `lamparas/comun.py` | — |
| `; CHANGE_LAYER`, `; Z_HEIGHT:`, `; LAYER_HEIGHT:` | **`ext-gcode/.../bambu.ts`** | **el cuerpo NUNCA** |
| `M73`, `; FEATURE:`, miniaturas | `bambu.ts` | el cuerpo nunca |
| `;WIDTH:`, `;HEIGHT:` (anotación pura) | `lamparas/comun.py` | — |
| Start/end gcode de máquina | la plantilla, vía `bambu.ts` | — |

**`; CHANGE_LAYER` es territorio exclusivo del injerto**, y no es una convención:
`bambu.ts` usa la PRIMERA línea `; CHANGE_LAYER` como `HEAD_END`, la marca que
le dice dónde termina el start-gcode de la plantilla. El cuerpo emitió 425 y
Orca mostró la pieza **cortada por la mitad**.

`;WIDTH:` y `;HEIGHT:` sí puede emitirlos el cuerpo porque son anotaciones: no
arman capas y no pueden mover ninguna frontera. `bambu.ts` lee `;WIDTH:` y le
gana al ancho nominal de la plantilla.

## Las tres alturas que NO son la misma

Confundirlas fue la causa de la mitad de los defectos de la pieza.

| Nombre | Qué es | Quién la usa |
|---|---|---|
| `altura_capa` | el paso nominal del perfil | punto de partida |
| `subida` | cuánto sube la vuelta **en Z** | apilar capas en el visor |
| `separación` | distancia entre vueltas **sobre la superficie** | **la extrusión** |

En una pared vertical las tres coinciden. En una cúpula no: donde la pared se
tumba, `separación` vale 0.400 mientras `subida` vale 0.050.

- Escalar la extrusión con `subida` dejó la cabeza del hongo con **0.157 mm de
  pared** arriba y el 4.07 % del recorrido con cordón imposible. La extrusión va
  con `separación`, que es la que `marcha_vertical` mantiene constante.
- Declarar `separación` como altura de capa al visor hizo que 425 capas sumaran
  ~170 mm para una pieza de 117: **cortada por la mitad** otra vez.

## Los dos mecanismos de apoyo

`SKILL.md` ya lo dice y aun así se olvidó dos veces:

- **Vertical**: la vuelta se apoya sobre la de abajo. Manda el paso.
- **Lateral**: una superficie casi horizontal se apoya AL LADO, como el piso de
  un bol. Manda la separación entre pasadas, **no** el apoyo vertical.

Un medidor que solo mire hacia abajo pinta de rojo toda repisa plana, que es
justo el mecanismo que hace imprimibles las aletas y las lenguas. El modo solape
del preview mide lo vertical: en una repisa plana, rojo es lo esperado.

## Qué mide cada verificador, y contra qué

**Regla: correr `test_verificar.py` antes de creerle un número al verificador.**
Cuatro bugs suyos dieron veredictos enteros equivocados, y ninguno se veía en una
pieza de 180 000 segmentos.

| Archivo | Mide | Referencia |
|---|---|---|
| `test_verificar.py` | 12 casos de g-code con respuesta conocida | él mismo |
| `verificar_pieza.py` | línea fina, contacto, choque, puentes | `Squeezy Fidget Toy.gcode` |
| `verificar_capas.py` | coherencia de las marcas de capa | suma declarada vs altura real |
| `verificar_piso.py` | Ø del disco de apoyo y del hueco | el disco plano del g-code |
| `vista_gcode.py` | frontal y planta a PNG | el ojo |
| `vista_relieve.py` | la pieza DESENROLLADA a PNG, y el período de la textura | el ojo, y el conteo contra una pieza sin figura |
| `verificar_campo.py` | campo de deformación JS contra Python | uno contra otro |
| `verificar_ams.py` | bloque de cambio de filamento | un 3mf real de Bambu |

`vista_gcode.py` no sirve para una pieza texturada: de frente, un tubo cubierto
de púas es un rectángulo gris y en planta las 500 vueltas se pisan. Ahí va
`vista_relieve.py`, que dibuja lo que en esas piezas hay que mirar —cuánto
sobresale la superficie en cada (ángulo, altura)— y se compara a ojo con lo que
dibuja `lamparas.superficie`. Ojo: `ver_rosca.py`, que vino con la rama de la
rosca, hace casi lo mismo. Ver el punto 2 de "lo que queda abierto" en
`ESTADO.md`.

**La referencia es `Squeezy Fidget Toy.gcode`, no `hongo.gcode`.** El hongo fue
la referencia una sesión entera y no servía: tenía el 4.07 % del recorrido con
cordón por debajo de 0.10 mm contra el 0.26 % de Squeezy. Calibrar contra él
dejaba pasar el defecto que había que cazar.

Y Squeezy hay que medirlo **por sus cúpulas** (z 0..28 y z 70..97): el medio es
una celosía cuyos hilos cruzan en el aire por diseño, y el ángulo no avanza de
forma monótona, así que cualquier detección de vueltas sobre la pieza entera da
basura.

## `cambios` es un dict POR ALTURA, y dos cosas en la misma z se pisan

El ventilador, los cambios de color, `--velocidad-en`, `--ventilador-en` y los
~50 escalones de `--segundos-vuelta` escriben todos en el mismo `cambios{z: bloque}`.
El que pisa es el último, porque cae en una grilla de 2 mm y son muchos:

    --ventilador-desde 0.08 sobre 150 mm  ->  aire a z12.00, que es de la grilla
    el escalón de velocidad de z12.00 le gana  ->  la pieza sale SIN VENTILADOR

Y no avisa nada: el CLI imprime "ventilador 100% desde z12.0" igual, porque lo
imprime cuando lo escribe, no cuando sobrevive. **El hongo zafó de casualidad**
—su `0.89 x 182.1` da 162.07, que no es múltiplo de 2— así que el defecto
esperó a la primera pieza cuya altura por la fracción cayera redonda.

Se arregla corriendo el escalón de velocidad una centésima; a la escala de una
vuelta no cambia nada. Pero la lección general es: **antes de creerle al log del
generador, buscar el `M106` en el g-code emitido.** Lo que vale es el archivo.

## Las rayas oscuras entre cordones del visor NO son huecos

Se ven en Orca en cuanto la pared se acuesta, y asustan: parece que las vueltas
no se tocan. Orca dibuja cada cordón con el ancho de `; LINE_WIDTH:` y el alto de
`; LAYER_HEIGHT:`, y `; LAYER_HEIGHT:` lleva la SUBIDA de la vuelta. Pero el
cordón real está ROTADO con la pared, y su extensión vertical es
`separacion·cos(θ) + ancho·sin(θ)`, que en un flanco a 55° vale 1.19 mm contra
una subida de 0.48. **El visor lo pinta a la mitad de lo que mide.**

Medido, en el gusanito y en el hongo, la subida entre vueltas y el
`; LAYER_HEIGHT:` declarado coinciden hasta la milésima: los cordones dibujados
quedan exactamente tangentes, 0.000 mm de hueco. Lo que se ve es el surco entre
dos cilindros tangentes pintados más flacos de lo que son.

**El hongo, que está impreso y sale bien, da lo mismo** (dibujado 0.19..0.80
contra 0.85..1.44 reales). Antes de perseguir un hueco del visor, medir la
separación sobre la superficie contra el ancho del cordón: eso es lo que decide,
y `verificar_pieza` ya lo hace.

Y a Squeezy esta medición no se le puede hacer: no tiene marcas de capa, y su
tramo del medio rompe cualquier detección de vueltas (ver más arriba).

## La extrusión se derivaba con una ventana más ancha que el detalle

La sección depositada se escala con la SEPARACIÓN, y la separación salía de
`subida * sqrt(1 + tan²)` con la pendiente de `_pendiente`, que deriva con una
**ventana fija de ±0.005 en `t`** — sobre una pieza de 150 mm, ±0.75 mm de z.

Donde el perfil tiene un detalle más angosto que esa ventana, la resta agarra
las dos caras y da casi cero: la cuenta declara vertical una pared que está a
55°. En el cuello del gusanito eso dejó **una vuelta con 0.449 mm² contra 0.731
de sus vecinas —el 61 % del material— y la de abajo con 0.793, gorda**. Se ve en
el laminador como una banda hundida y una saliente; no lo cazó ningún
verificador, lo cazó el usuario mirando la pieza.

`radio_de` ya avisaba de la misma trampa del otro lado ("la derivada de una
escalera es ruido") y por eso suaviza la tabla del DXF. Pero una silueta
analítica no pasa por ahí.

**El arreglo es no derivar.** `marcha_vertical` ya elige el paso con
`_delta_radio` —el radio evaluado en los dos extremos del tramo, sin ventana— y
la extrusión ahora usa la misma cuenta:

    separacion = hypot(subida, _delta_radio(t, t + subida/altura))

Las dos caras de la frontera hacen la misma cuenta, que es lo que este archivo
viene pidiendo desde arriba. Medido:

| | antes | después | Squeezy |
|---|---|---|---|
| gusanito, cuello | 0.449..0.793 mm² | **0.720 clavado** | — |
| hongo, área p10..p90 | 0.892..1.018 | **0.960..0.960** | 0.968..0.969 |
| hongo, caudal tope | 19.97 mm³/s | **15.36** | 10.44 |

**El hongo cambia**, y hay que saberlo: el RECORRIDO es idéntico —86 346
movimientos, 0 con X/Y/Z distinto— y lo único que cambia es cuánto material sale.
Le desaparece un pico de caudal del 30 % y queda con la sección constante, que
es lo que hace la referencia. Sigue dando IMPRIMIBLE y su choque baja de 4.25 a
3.99 %.

## Dos superficies solo empalman bien donde comparten la tangente

`espejar()` lo dice para la base del hongo: el eje del reflejo es la panza
porque "es el único punto donde las dos mitades empalman con la misma tangente;
cualquier otra altura deja un pico o un escalón". Vale igual para el gusanito,
que es el MÁXIMO de varios elipsoides: donde dos lóbulos se cruzan las tangentes
valen ±55° y queda un pico. Impreso se lee como un corte.

Por eso `gusanito` combina los lóbulos con un máximo SUAVE y no con `max()`. El
filete es local —fuera de su ventana devuelve el máximo duro, así que no toca ni
el ecuador ni el ápice— y ensancha el cuello exactamente `redondeo/4`.

Lo que NO hay que hacer es compensar ese ensanche descontándoselo a la V antes
de resolver la geometría: con la altura fija, una V más profunda obliga a un
paso más largo y **achata todos los lóbulos**. Medido, corría el perfil hasta
2.6 mm a media altura — un filete de 4 mm reformando la pieza entera. Se compensa
por afuera, bajando `cintura`.

## Un verificador tiene que mirar las vueltas QUE SE IMPRIMEN

`generar_pieza` medía el voladizo sobre `silueta(capa/n_capas)`: la silueta
repartida pareja en `t`. Pero `marcha_vertical` acorta el paso donde la pared se
tumba, así que las vueltas se AMONTONAN en `t` justo ahí — que es donde el
voladizo decide. Los puntos que se medían no los visitaba ninguna vuelta.

Sobre el gusanito daba **0.86 mm de salto radial y 28 % de solape** ("no esperes
que salga") contra los **0.64 mm y 46 %** que emite el recorrido de verdad. Se
arregla muestreando en los `t` que devuelve `marcha_vertical`, que ya están ahí
mismo en la función. Es el mismo error que `marcha_vertical` documenta al final
de su docstring, del otro lado de la frontera: dos copias de la misma cuenta
describiendo recorridos distintos.

El aviso es solo un `print`: comprobado regenerando el jarrón antes y después,
0 líneas de máquina distintas.

## Al ápice de una cúpula el "choque" le da siempre alto, y no significa nada

`verificar_pieza` marca "pisado" cuando dos ejes quedan a menos del 70 % de la
separación de fusión. En el ápice la pared está acostada y las vueltas apoyan AL
LADO, no encima: la separación sobre la superficie es el paso, y contra un
cordón de 1.2 eso cae debajo del umbral en cuanto el paso baja de ~0.73.

O sea que la MISMA pieza pasa de 1.5 % a 8.6 % de choque bajando la capa de 0.8
a 0.6 sin que cambie nada físico — la razón `área ÷ avance` es idéntica. El
hongo, impreso y bueno, da 4.25 %. Antes de creerle a ese número hay que
preguntarle DÓNDE: si está todo en la banda del ápice, es el cierre de la
cúpula, no un defecto.

## Cómo derivar el cordón de un g-code ajeno

Sin suponer nada, y la circularidad acá ya costó una calibración entera:

1. `h` = distancia vertical al material que está **justo debajo** (dh < 0.2 mm).
2. `w` = área por milímetro ÷ `h`.

Sobre `hongo_fix`, cuyo ancho nominal se conoce (1.2), el método devuelve 1.25.
Squeezy da 1.22 y el jarrón 1.20.

## Las etiquetas que lee Orca, con sus nombres exactos

Sacadas de un g-code **exportado por el propio Orca** (`gcodes/Cubo_PLA_multi_color_orca_template...`),
que es la única fuente que vale:

    ; CHANGE_LAYER
    ; Z_HEIGHT: 0.2          el TECHO de la capa, no el piso
    ; LAYER_HEIGHT: 0.2      cuánto ocupa el cordón en vertical
    ; LINE_WIDTH: 0.42       el ancho
    ; FEATURE: Outer wall

**El ancho se llama `; LINE_WIDTH:`.** No es `;WIDTH:` (eso es PrusaSlicer) ni
`; WIDTH:`. Con el nombre equivocado Orca lo ignora y deduce el ancho como
`área ÷ altura`, y ahí no hay forma de ganar: la altura que hace que apile bien
los cordones —la subida real, que varía de 0.400 a 0.050— es la misma que le
hace deducir un ancho de 9.6 mm. Eran una variable haciendo dos trabajos.

Con el nombre correcto son independientes:

| etiqueta | qué lleva | por qué |
|---|---|---|
| `; Z_HEIGHT:` | el techo de la capa | declarando el piso, el 86 % de los movimientos caía fuera de su capa |
| `; LAYER_HEIGHT:` | la subida REAL de la vuelta | una constante produce un aro visible en la cúpula |
| `; LINE_WIDTH:` | el ancho nominal, constante | el cordón es constante, el color tiene que serlo |

Y las tres son comentarios: **no cambian ni una instrucción de la máquina**.
Comprobado comparando los 110 102 movimientos del g-code contra los del 3mf
injertado: 0 distintos, 0 sobrantes.

## La regla que sale de todo esto

**Cuando haga falta saber qué formato espera una herramienta, abrir un archivo
que ESA herramienta haya producido.** Antes de proponer ninguna hipótesis.

Se perdieron horas probando ortografías de etiquetas y culpando a la velocidad,
la geometría, la extrusión y la pendiente —todas descartadas con medición, todas
inocentes— teniendo los g-code de Orca en el repo desde el principio
(`ext-gcode/gcode/orca_slicer_PETG_transparent.gcode.3mf.3mf`). La respuesta
estaba en un archivo del proyecto.

Corolario del mismo tipo: **el usuario repitió cuatro veces que era cuestión de
etiquetas y tenía razón.** Cuando alguien insiste en una hipótesis que uno ya
descartó, conviene volver a mirarla en vez de seguir con la propia.

## El color en Orca, y por qué engaña

Orca dibuja el ancho como `área ÷ altura_de_capa`, y esa altura la saca de los
comentarios del archivo — **no de la Z de los movimientos**. Consecuencias:

- Sin comentarios usa un valor por defecto y pinta un ancho que la pieza no
  tiene. Con área 0.480 y un defecto de ~1.0 pintaba 0.48 donde el cordón es 1.20.
- En un archivo injertado leía la altura de **la plantilla**.
- El mapa de **velocidad** tiene escala absoluta pensada para 100-300 mm/s.
  Nosotros imprimimos a 6-20 mm/s, igual que las referencias (Squeezy 4-8, el
  jarrón 12-15): todo cae en el escalón más bajo y se ve plano. No es un error.
- La vista **"Resumen"** pinta todo de un color liso. No mide nada.

## El g-code no se edita: se regenera

De `SKILL.md`, y sigue siendo la regla que ordena todo. Un g-code editado ya no
tiene parámetros. Todo —sliders, toques, esculpido— es un DATO que vuelve a
entrar al generador.

## Antes de decir que algo funciona

1. Medirlo sobre el g-code generado, no sobre el cálculo.
2. Si el número contradice lo esperado, **sospechar primero de la medición**.
   Cuatro de cuatro veces en la última sesión, el roto era el medidor.
3. Medir los criterios **juntos**: una pieza puede tener contacto perfecto y
   cordones imposibles.
4. Al cambiar algo del paso vertical, **comparar el perfil radio-contra-altura**
   antes y después. Altura y radio máximo iguales NO alcanzan: un piso en el
   paso dejó la silueta estirada con los dos números intactos.
