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
