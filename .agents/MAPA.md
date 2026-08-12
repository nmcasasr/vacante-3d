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
| `vista_gcode.py` | frontal y planta a PNG | el ojo |
| `verificar_campo.py` | campo de deformación JS contra Python | uno contra otro |
| `verificar_ams.py` | bloque de cambio de filamento | un 3mf real de Bambu |

**La referencia es `Squeezy Fidget Toy.gcode`, no `hongo.gcode`.** El hongo fue
la referencia una sesión entera y no servía: tenía el 4.07 % del recorrido con
cordón por debajo de 0.10 mm contra el 0.26 % de Squeezy. Calibrar contra él
dejaba pasar el defecto que había que cazar.

Y Squeezy hay que medirlo **por sus cúpulas** (z 0..28 y z 70..97): el medio es
una celosía cuyos hilos cruzan en el aire por diseño, y el ángulo no avanza de
forma monótona, así que cualquier detección de vueltas sobre la pieza entera da
basura.

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
