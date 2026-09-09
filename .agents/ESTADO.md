# Sesión del 25/26-08-2026 — la tuerca, el encastre y el caudal

## LO PRIMERO: qué imprimir

**`output/rosca/final/`** es la tanda vigente. Tiene su propio `LEEME.md`.
**`output/rosca/prueba/` entero quedó viejo**: esas piezas se generaron con la
pared un 32 % más gruesa de lo pedido (ver más abajo).

A LA ALTURA REAL: los machos miden **230 mm** (17 vueltas) y la tuerca los
28 mm de su STL. En `final/cupon_40mm/` están las mismas cinco a 40 mm, para
probar el encastre sin gastar 2.3 h.

    macho_clasico_v1823.gcode              el ajuste, el caso más justo
    macho_caritas_relieve_v1775.gcode      el dibujo original
    macho_caritas_intercalada_v1774.gcode  ojos de línea, feliz/triste alternadas
    macho_perlas_v1846.gcode               apoyo 14 %, el más flojo
    macho_interrumpida_v1824.gcode         hilo cortado en 6 sectores
    hembra_v1878.gcode                     la tuerca en modo vaso, 28 mm

Todas: pared **1.0 mm real** (medida, no declarada), **1440 segmentos** por
vuelta, PLA a **220 / cama 65 / ventilador 75 %**, tramo gordo clavado en
**12.0 mm3/s**. Cada macho son ~245 m de recorrido, 2.3 h y 52 MB. Los cinco
entran en esa hembra (+0.094 a +0.101 mm de holgura mínima medida sobre el
g-code).

**Lo que hay que traer de vuelta de la impresión:** si las caritas salen ahora
(ver más abajo por qué no salían), y si el par enrosca sin raspar.

## OJOS DE LÍNEA Y CARAS ALTERNADAS — `caritas_intercalada`

Dos cambios pedidos sobre `caritas_relieve`, los dos como PARÁMETROS: el patrón
viejo se regenera idéntico (comprobado, 0.0000 mm de diferencia en 144 000
muestras contra HEAD).

**Los ojos son líneas verticales** y eso sale gratis en los dos ejes:

- En ARCO no cuesta nada. Dos vueltas seguidas se llevan 0.30 mm de z al MISMO
  ángulo, así que el solape entre vueltas lo fija la pendiente en `d` y no la
  del ángulo. El ancho del ojo en arco NO mueve el salto radial — medido: 0.413
  mm con `alto_ojo` 0.7, 0.9, 1.3, 1.8 y hasta 2.4, el mismo número hasta la
  milésima. Lo que manda ahí es la boca.
- En `d` la campana se ESTIRA, o sea que la pendiente BAJA: `techo*pi/(2*ojo_v)`
  da 0.67 con `ojo_v=4.6` contra 0.92 con el ojo redondo.

    `alto_ojo` 1.8   3.6 mm de arco = 3.6 cordones de 1.0. Más angosto se lo
                     come la línea, que es una de las dos causas candidatas de
                     que los rasgos no salieran en la tanda anterior. Y
                     ENSANCHARLO ES GRATIS: el salto radial se queda en 0.413
                     mm hasta 4.8 mm de ojo, y el apoyo hasta mejora. El único
                     límite es que se siga leyendo como línea — a 3.6 x 9.2 la
                     proporción es 2.6 a 1.
    `ojo_v` 4.6      9.2 mm de alto contra 6.7 del ojo redondo, sin llegar a
                     PASO/2 = 6.75, que es donde invadiría la fila de al lado.

**Las caras alternan en damero.** `feliz` salía de la paridad de la fila, así
que un anillo entero salía feliz y el de arriba entero triste. Con `intercalar`
se le suma el índice de cara y alternan también alrededor.

**`n_por_vuelta` tiene que ser PAR**, y esto no es cosmético: con 9 las caras 8
y 0 son vecinas y tienen la misma paridad, o sea una costura por anillo donde la
cara se repite. Se usa 10, que además baja el hueco sin apoyo de 27.5 a 23.9 mm.

Medido contra la hembra `PLA_NUEVAS_hembra_v1844`, con `caritas_relieve` de
control — las tres cifras del encastre son las MISMAS:

    | | intercalada | relieve (control) |
    |---|---|---|
    | holgura radial | +0.101 mm ENTRA | +0.100 mm ENTRA |
    | juego axial | 3.03 mm (22 %) | 3.03 mm (22 %) |
    | apoyo | 9.8 % | 10.3 % |
    | peor salto radial | 0.413 mm, 59 % solape, FIJO | 0.411 mm, FIJO |

`verificar_pieza`: línea fina 0.00 %, contacto 0.00 %, sin puentes -> IMPRIMIBLE.

**Ojo con el apoyo medido sobre la FUNCIÓN**: `verificar_rosca` da 5.1 % contra
8.9 % del ojo redondo, y parece una caída grande. Es que mide una sola línea
—la fase de la cresta— y el ojo de línea es angosto justo ahí. Sobre el g-code
emitido contra la hembra real, que es lo que cuenta, la diferencia es 9.8 contra
10.3 %.

## EL GRUESO DE PARED: sale 32 % más gordo de lo que se pide

Lo notó el usuario a ojo comparando con `macho_tuerca_PLA_35m22s.gcode.3mf`, que
está impreso. Es la misma rosca (radio de trayectoria 49.4..51.5 en las dos), así
que la comparación es limpia.

Espesor real = sección depositada / SEPARACIÓN entre vueltas sobre la superficie.
Dividir por la subida es la trampa de las tres alturas de `MAPA.md` otra vez: en
el flanco del hilo la vuelta de arriba no se apoya encima sino AL LADO.

    referencia impresa (Orca)      0.88 mm de mediana, baja a 0.67 en los flancos
    nuestra clasico_v1778          1.32 mm                (pidiendo 1.0)
    nuestra caritas_intercalada    1.39 mm, hasta 1.64

Las dos yerran, para lados OPUESTOS:

- **Orca mantiene el caudal constante** —0.358 mm2/mm con 0 % de dispersión— así
  que donde la superficie se inclina la pared adelgaza. 0.67 en el flanco.
- **Nosotros escalamos con la separación, que es lo correcto, pero con UNA sola
  por vuelta: la del PEOR ÁNGULO** (`_pendiente` hace `max` sobre los 360). En
  una cúpula da igual porque toda la vuelta se tumba lo mismo. En una rosca sólo
  los flancos están a 43°; la cresta y el fondo son planos y reciben igual la
  sección del flanco. `sqrt(1+tan²43°)` = 1.37, y 0.301 x 1.37 = 0.412, que es
  justo la sección medida.

**Esto no es sólo material de más: corre la superficie.** `rosca(ancho_cordon=1.0)`
resta medio cordón para que la pared caiga donde el diseño la quiere. Con la pared
saliendo a 1.32 el medio cordón real es 0.66, o sea que la cara impresa queda
**0.16 mm por fuera** de donde se calculó — sobre una holgura de 0.20.

### `separacion_por_angulo`, opt-in en `generar_pieza`

`gen_rosca.py --separacion-por-angulo`. Calcula `hypot(subida, dr)` con `dr`
contra la vuelta de arriba EN EL MISMO ÁNGULO (`angulo + 2*pi`, que con el ángulo
acumulado es exactamente una vuelta) y emite el `ExtrusionGeometry` que cambia.

Va APAGADO por defecto y el control lo confirma: **el hongo se regenera byte a
byte idéntico**, sólo cambian las 2 líneas del comentario con su propio nombre.

    intercalada por VUELTA   pared 1.393 (1.038 .. 1.640)
    intercalada por ÁNGULO   pared 1.009 (0.855 .. 1.018)   <- el 1.0 que se pide

Sigue ENTRANDO (+0.101 mm, juego axial 3.03 mm, apoyo 9.9 % — las tres cifras
idénticas a la versión por vuelta) y sigue IMPRIMIBLE. Y como la sección mediana
baja de 0.408 a 0.303, el freno de caudal deja subir de 1714 a 2142 mm/min: 25 %
menos de tiempo.

### PENDIENTE: el freno de caudal se aplica sobre la MEDIANA

`velocidad.area_emitida` devuelve `a[len(a)//2]`. Con la sección constante eso
está bien, pero en cuanto varía deja pasar los picos:

    | | sección | caudal mediano | pico | recorrido sobre 12 |
    |---|---|---|---|---|
    | referencia impresa | 0.358 plana | 12.0 | 12.2 | — |
    | intercalada por vuelta | 0.358..0.497 | 11.7 | **14.2** | 26 % |
    | intercalada por ángulo | 0.301..0.51 | 10.8 | **18.2** | 10 % |

Las lisas (clásico, perlas, interrumpida) no tienen el problema: 12.2 de pico.

El arreglo es capar por un PERCENTIL ALTO, y el percentil importa porque los
picos son raros — medido sobre la intercalada por ángulo, qué fracción del
RECORRIDO (no de los segmentos) pasa cada sección:

    >0.31  16.7 %     p50  0.303 -> 2374 mm/min
    >0.35   8.5 %     p90  0.337 -> 2135
    >0.40   2.7 %     p99  0.407 -> 1770
    >0.45   0.1 %     máx  0.511 -> 1409
    >0.50   0.0 %

O sea que capar por el MÁXIMO frenaría la pieza entera un 41 % por el 0.1 % del
recorrido: mal negocio. **p99 es el corte** — `velocidad.PERCENTIL_FRENO`.

HECHO. `area_emitida(pasos, q)` toma un percentil y pesa **por LARGO DE
RECORRIDO**, no por cantidad de marcas: `generar_pieza` sólo emite el
`ExtrusionGeometry` cuando la sección cambia más de 0.005, así que un tramo
largo y parejo deja UNA marca y un tramo que varía deja cientos. Contando
marcas, los tramos gordos pesan de más. `velocidad_para` frena por p99 y
`caudal_pico` lo informa; `caudal` sigue dando el típico.

    cupón final   1769 mm/min   8.9 mm3/s típico   12.0 en el tramo gordo

## LA PARED GORDA SE COME LA HOLGURA DEL MACHO

`rosca(ancho_cordon=1.0)` resta medio cordón para que la pared caiga donde el
diseño la quiere. Si el cordón real no mide 1.0, la cara impresa no cae ahí:

    macho clasico_v1778   pared real 1.32 mm -> medio cordón 0.66 -> +0.16 mm

Sobre una holgura de diseño de 0.20 quedan **0.04 mm**. No es interferencia,
pero es el margen entero.

**LA HEMBRA NO ENTRA EN ESTA CUENTA.** La que se imprime sale del STL laminado
en Orca, no de `gen_tuerca.py`, así que su pared es la de Orca y no la nuestra.
Y Orca yerra para el otro lado —mantiene el caudal constante, así que la pared
adelgaza (0.88 medido en el macho de referencia)—, con lo cual el barreno queda
si acaso un pelo MÁS ancho de lo dibujado. Suma a favor.

Nuestro `PLA_NUEVAS_hembra_v1844` sí sale con 1.75 mm de pared (peor que el
macho porque va en marcha ADAPTATIVA: sube 0.221 por vuelta en vez de 0.301 y
la sección le sigue llegando del peor ángulo; medido por dos caminos, 1.746 y
1.771). Importa el día que se imprima ESA hembra, no ahora.

Salvedad: el g-code dice cuánto material se deposita, no hacia qué lado crece el
cordón. Lo medido es la sección, no la cara impresa.

**Pendiente:** regenerar los otros cuatro machos con `--separacion-por-angulo`.
El de caritas intercaladas ya está.

## `pastillas` — discos con figura hundida

Pedido: como `perlas` pero más circulares, con incrustaciones como las del cupón
de estrellas y lo negro hundido. Salió `rosca.pastillas`, que es los dos
cruzados: de `perlas` el bulto suelto, de `sellos_relieve` la figura sacada de
un contorno. La diferencia con los dos es que el disco y la figura son COSAS
DISTINTAS — el disco sube, la figura baja sobre él.

    r = min(envolvente(d), núcleo + disco(u,v) - grabado(u,v))

32 por vuelta: 9.97 mm de paso para un disco de **Ø8.40**, o sea 1.6 mm de
hueco. Figuras en damero: corazón, estrella, carita y raya.

### El disco NO lo limita la meseta

Empecé con Ø6.65 creyendo que el tope era la meseta —donde el riel está a
tope—, y es otra cosa. Más allá de la meseta la envolvente baja DESPACIO (1.53
a 3.60 del centro, 1.11 a 4.00, 0.78 a 4.40) y el chaflán del disco ya bajó más
rápido que eso: no lo recorta. Lo único que tiene que caber en la meseta es la
CARA PLANA, o sea `radio - borde <= 3.325`.

Con chaflán 1.30 el tope es radio 4.625 → Ø9.25 contra Ø6.65. Y del lado de la
IMPRESIÓN sale gratis: el salto radial se queda en 0.455 con cualquier tamaño
—lo fija el chaflán, que no cambia— y el apoyo sube.

### Pero agrandar SÍ cuesta, y no donde lo buscaba

Un disco más ancho llena más el canal del hilo y se come el JUEGO AXIAL. Medido
contra `hembra_v1878`, con la misma holgura radial en los cuatro (+0.096..0.097):

    Ø6.65  n36   juego 2.69 mm (20 %)   apoyo 14.4 %
    Ø7.80  n34   juego 1.54 mm (11 %)   apoyo 19.6 %
    Ø8.40  n32   juego 0.94 mm ( 7 %)   apoyo 21.4 %   <- por defecto
    Ø9.25  n30   juego 0.16 mm ( 1 %)   apoyo 24.7 %

El par que el usuario ya imprimió y enrosca mide 4.08 mm (30 %) y "baila un
poco"; el máximo teórico —`perfil_envolvente`— da 0.28. O sea que **Ø9.25 queda
más apretado que el diente más gordo posible** y no deja nada para absorber la
variación del plástico. Ø8.40 es 26 % más de diámetro y 59 % más de área que el
original y conserva casi un milímetro. `gen_rosca.py pastillas_max` emite el de
Ø9.25 para el que lo quiera probar.

**La raya es la única que llega al FILO del disco**, y no es un capricho: los
tres cierres tienen borde de ARRIBA horizontal, y ahí la pendiente del grabado
se sumaría a la del chaflán en el mismo punto. La raya no tiene borde de arriba
—sus dos límites corren en `u`— así que cruza la pastilla entera sin costar una
centésima de solape: medido, el salto sigue en 0.455. Y se lee mejor, porque una
pastilla partida al medio es lo que hace una ranura de verdad.

Mide **1.10 mm de ancho con 0.72 al fondo pleno**. El ancho no se elige a gusto:
por debajo de un cordón el surco no se dibuja —el cordón siguiente lo pisa— y
`borde_grabado` se come el resto. Bajarlo de 0.25 a 0.15 es lo que deja una raya
fina que igual llega al fondo, y no cuesta nada porque los bordes de la raya
corren en el eje libre.

    salto radial 0.455 -> 55 % de solape, paso FIJO
    contención +0.0000   apoyo 23.8 %   IMPRIMIBLE
    encastre +0.099 mm ENTRA, juego axial 2.69 mm (20 %)
    1329 mm/min (22 mm/s): el chaflán pide sección 0.545 y ahí manda el caudal

### Cuatro cosas que sólo se vieron RENDERIZANDO EL G-CODE

Ninguna aparece en los números. Todas salieron de mirar el PNG.

1. **El borde del disco tiene que ser RECTO, no campana.** Con coseno la
   pendiente es `alto*pi/(2*borde)` y para entrar en presupuesto hace falta
   borde 1.94, con lo que sobra 1.1 mm de cara y no hay dónde grabar. Recto la
   pendiente es `alto/borde`, constante, y con 1.30 quedan 2.03 mm de meseta.

2. **`prof` la fija el CANTO VIVO, no el borde suave.** En el valle de una
   estrella `e` deja de ser una distancia y el grabado sale con pared vertical:
   el salto vale `prof` entero. Con 0.55 la pieza se pasaba a adaptativa. 0.45
   es lo que deja 55 % de solape. El síntoma que lo delató: el peor salto daba
   0.550 clavado y NO se movía al tocar el chaflán.

3. **`|cos|` no hace estrellas, hace flores.** `_rho_estrella` es suave en los
   picos y grabada se lee como flor. Bajarle el valle de 0.45 a 0.30 no alcanzó
   —sigue siendo un coseno—. Hizo falta `_rho_estrella_recta`, de lados rectos,
   como tabla. Y la carita salía como una barra sobre un arco porque los ojos
   (v -0.08..1.30) y la boca (hasta 0.69) se pisaban.

4. **El salto de fila caía DENTRO del disco.** `caritas_relieve` saca la fila de
   `round((z - d + D_CRESTA)/PASO)`, que salta donde envuelve `d`. Con v0=0 eso
   cae en v=+4.75 y su rasgo llega a 3.36: nunca se tocan. Una pastilla va
   centrada en la MESETA (v0=+1.675) y ahí el mismo salto cae en **v=+3.075**
   con el disco llegando a **3.325**. Se veía como un escalón en diagonal
   cruzando cada pastilla. Se arregla rebasando `d` para que envuelva medio
   paso más allá del centro.

   **Y NO se arregla sacando la fila del ángulo ACUMULADO**: probado, y así la
   fila cambia una vez por VUELTA en vez de una por banda, con lo que la misma
   pastilla sale con una figura distinta en cada capa.

### El defecto que sólo apareció al AGRANDAR: la figura seguía al número de vuelta

Con Ø9.25 las pastillas salieron a RAYAS horizontales, franjas de 0.30 mm con
dos figuras alternadas. La función pura estaba limpia, así que era de la
emisión.

    dispersión de radio dentro de una misma celda del render:
        mediana 0.0000   p99 0.0000   MÁXIMO 0.4500   <- `prof` exacto

Dos figuras distintas en la misma celda. La causa: `celda = angulo / paso_ang`
con el ángulo ACUMULADO. Una vuelta recorre la banda entera en `d` —es una
hélice—, así que cada pastilla se construye a lo largo de ~30 vueltas, una
franja horizontal por vuelta; y con el ángulo acumulado `floor(celda)` avanza
`n_por_vuelta` por vuelta, con lo que la figura se corre `n_por_vuelta % 4` cada
una.

    n=36  ->  36 % 4 = 0   la figura no se movía. Estaba bien POR CASUALIDAD.
    n=30  ->  30 % 4 = 2   se corre dos figuras por vuelta -> rayas.

Se arregla sacando el índice del ángulo MÓDULO UNA VUELTA, que es lo que hace
que la figura sea función de la POSICIÓN y no del número de vuelta.

**Regla:** un índice de celda que se usa módulo k tiene que salir del ángulo
módulo una vuelta. Si sale del acumulado, funciona sólo cuando
`n_por_vuelta % k == 0`, y eso no se ve hasta que alguien cambia `n`.

### `ver_banda.py` — el render que hizo falta para ver todo esto

`ver_rosca.py` desenrolla por (ángulo, z) y ahí el recorrido llena UNA fila de
píxeles por pasada: para juzgar una figura de 4 mm no alcanza. `ver_banda.py`
pliega las vueltas en la grilla (ángulo, FASE DEL HILO), donde 45 vueltas llenan
la banda entera, y saca dos PNG: el sombreado y el de ALTURA.

**Hay que mirar el de altura.** En el sombreado la luz viene de un lado y el
lado oscuro parece vacío: con él di por descentradas figuras que estaban bien.

`--impreso` filtra en `u` con el diámetro de boquilla (0.8): el recorrido es una
línea sin espesor, pero la boquilla no dobla en menos que su propio diámetro, así
que todo lo que mida menos que eso sale redondeado. En `v` no filtra nada —ahí ya
hay una sola muestra por vuelta, que es la resolución real de la pieza—.

Dos trampas propias del render, las dos ya en el archivo: el centro se saca
DESPUÉS de descartar la purga (si no, el radio da 52..75 en vez de ~51), y la
resolución vertical no se elige —hay una muestra por vuelta, o sea una cada
0.30 mm— porque pedir más hace que el sombreado se coma las líneas de capa.

## CONTROLES DEL PREVIEW PARA LA ROSCA

La maquinaria ya existía y la usaban sólo los bowls: `guardar_receta` deja un
`<nombre>.params.json` con `args`, `cwd` y una lista de `controles`, y la
extensión arma un slider por cada uno y **vuelve a correr el generador** en vez
de editar el g-code. `gen_rosca.py` y `gen_tuerca.py` no la usaban. Ahora sí,
con `--receta`. Las piezas de ejemplo están en `output/rosca/control/`.

Tres cosas hubo que agregar, y las tres tienen su motivo:

1. **`guardar_receta` sólo sabía invocar paquetes.** Armaba `["-m", modulo]`, y
   `python -m gen_rosca` importaría el script en vez de correrlo. Ahora, si el
   módulo termina en `.py`, lo invoca como script.

2. **`--receta` implica NOMBRE ESTABLE**, sin el sufijo `_vNNNN`. La extensión
   relee siempre la misma ruta después de regenerar, y el freno de caudal cambia
   la velocidad sola en cuanto un slider mueve la sección —`--ancho` y
   `--pastillas-n` la mueven—, así que con el sufijo el archivo saldría con otro
   nombre y el preview se quedaría mirando el viejo. Por eso `--receta` exige
   una sola `--velocidad`.

3. **`_FLAGS_SUELTOS` ahora admite PASO.** Sin él el slider va en 200 tramos,
   que para un flotante está bien y para una cuenta entera no: `--pastillas-n`
   salía en 8.2 pastillas por vuelta y el `type=int` de argparse revienta.
   Flags nuevos: `--ancho` (0.8..1.6, el piso es el diámetro de boquilla),
   `--diente` (0..1) y `--pastillas-n` (8..48, paso 1).

**LA TRAMPA: un control sólo aparece si el flag está en el `argv`.** No es un
bug — `guardar_receta` los arma recorriendo el comando con el que se generó la
pieza. Sin `--diente` en la línea no hay slider de diente aunque el generador lo
acepte. Comprobado: `clasico ... --receta` da tres controles y
`clasico ... --diente 0 --receta` da cuatro. Conviene pasar explícitamente, con
su valor por defecto, todo lo que se quiera poder tocar después.

Ida y vuelta comprobado como lo hace la extensión: moviendo `--pastillas-n` de
24 a 16 la velocidad pasó sola de 1325 a 1331 y el archivo siguió llamándose
igual.

**El `borrador` de la receta NO lo usa la extensión, y yo supuse que sí.** Los
tres `pedirRegen` de `media/main.js` pasan `borrador = false`; lo sacaron porque
salía un borrador por cada pausa del arrastre y la pieza parpadeaba. Los sliders
regeneran siempre a resolución completa.

Pero yo lo invoqué a mano para probarlo y **dejé el borrador pegado en el
disco**, así que el usuario abrió el preview y vio la pieza lisa:

    120 segmentos por vuelta -> 2.60 mm por segmento
    una pastilla mide 8.4 mm -> le tocan TRES puntos

Es la misma trampa que dejó las caritas sin dibujo con `SEGMENTOS = 360`.
Diagnóstico rápido cuando el preview muestre una pieza lisa:

    grep -c ' E' archivo.gcode     # 191534 completo, ~16000 borrador

### ARREGLADO en `ext-gcode`: el visor no abría archivos de más de 50 MB

`gcodePreview.open` exigía `vscode.window.activeTextEditor`, y VS Code NO abre en
el editor archivos de más de ~50 MB: la pestaña se ve pero el editor no existe,
así que el comando respondía "Open a .gcode file first" con el archivo delante.

Apareció con `pastillas_240.gcode` (66 MB); `pastillas_control` a 240 mm pesa 54
y ya estaba al borde. Es irónico: el visor existe para piezas grandes y se
rompía justamente con ellas.

Ahora busca en tres pasos: editor activo -> **URI de la pestaña activa**, que sí
se conoce aunque el editor no haya podido cargar -> selector de archivo.

### ARREGLADO en `ext-gcode`: cambiar de pestaña no releía la receta

`src/extension.ts`, el handler de `onDidChangeActiveTextEditor`:

    trackedUri = editor.document.uri;
    sendDoc();                 // la geometría sí
                               // la receta NO

Cambiaba de archivo sin releer el `.params.json`. Síntoma: viniendo de una pieza
sin receta y clicando en una que sí tiene, el panel seguía diciendo SIN RECETA y
no aparecía ningún slider. Es lo que le pasó al usuario, y me costó dos vueltas
porque en su primera captura los sliders SÍ estaban —ahí había abierto el
preview directamente sobre el archivo, que es el otro camino y ese sí llama a
`sendRecipe()`.

**Y al revés era peor:** el objeto `receta` que quedaba en memoria es el que usa
`regenerate()` para saber qué comando relanzar. Pasando de una pieza CON receta
a otra, los sliders seguían siendo los de la primera y moverlos regeneraba y
PISABA ESE OTRO ARCHIVO.

Una línea: `sendRecipe()` antes de `sendDoc()`.

**Regla:** `trackedUri` y `receta` son un par. Todo sitio que mueva uno tiene que
mover el otro — los otros tres sitios que asignan `trackedUri` ya lo hacían, y
este se había quedado afuera.

## PASTILLAS v2 — lo que dijo la pieza IMPRESA

El usuario imprimió `pastillas_control` (n=16, disco Ø8.40) y trajo tres cosas:
las figuras no se leen del todo, no están bien centradas, y **los círculos salen
deslizados hacia la derecha**. Las tres eran reales y ninguna se veía en los
números que veníamos mirando.

### 1. El deslizamiento es el ÁNGULO DE LA HÉLICE

`v` es la fase, o sea la altura medida DESDE LA CINTA — y la cinta sube. En el
arco que ocupa una pastilla (8.4 mm) el hilo gana `8.4 * PASO/ARCO_VUELTA` =
0.355 mm. Un círculo en (u, v) es un círculo sobre la cinta, pero sobre la PIEZA
sale corrido. Medido sobre el g-code impreso: **+2.81°**, contra 2.42° teóricos.

La altura sobre la pieza es `z - z0 = v + u*PASO/ARCO_VUELTA`, así que SUMANDO
ese término el disco sale redondo. Medido después: **+0.05°**, o sea 0.007 mm de
corrimiento contra 0.412.

**Lo probé primero RESTANDO y el deslizamiento se DUPLICÓ** (2.81° -> 4.35°).
Un signo mal puesto acá no rompe nada: empeora justo lo que venía a arreglar, y
sin medir las dos versiones no se distingue de "no funcionó".

No cuesta nada: entre dos vueltas al mismo ángulo `u` no cambia, así que el
salto radial queda igual.

### 2. `_encuadre` normaliza a la CAJA, y las puntas se recortaban

Las figuras polares se metían en su caja envolvente, y la caja de una estrella
sobresale del círculo: medido, las puntas llegan a **1.17 veces** el radio. Como
el grabado se recorta contra la cara plana, esas puntas salían CORTADAS — y
salían cortadas en la pieza impresa, donde el alcance real era 2.92 mm contra
una cara de 2.90. Por eso la estrella se leía redondeada por más que la afilara
con `_rho_estrella_recta`: el problema no era la forma, era el recorte.

Ahora `_marca_polar` divide por el alcance máximo, así que `rel_figura` significa
lo que parece: 0.95 es 5 % de margen para cualquier forma.

### 3. EL HUECO entre rasgos es tan trazo como el rasgo

La carita usaba **1.46 de 2.00** del círculo —el 73 %— y corrida 0.06. Corazón,
estrella y círculo usan 1.94-1.99. Impresa se veía más chica que las otras sin
que nada lo dijera; hay que medir la caja de cada marca, no mirarla.

Al agrandarla, el primer intento juntó los ojos a 0.78 mm de separación: **menos
de un cordón**. Impreso eso no es un hueco, es una BARRA — los dos ojos se
funden en una. La cuenta va al revés de lo que parece: primero se reparte el
hueco y con lo que sobra se dibuja.

    medida             impreso   ahora
    ojo: ancho          0.77      1.38     <- era 0.8 cordones
    ojo: alto           1.30      1.18
    hueco entre ojos      --      1.38
    boca: grosor        1.32      1.46
    hueco ojo-boca        --      1.01
    raya                1.19      1.82

### Lo que NO se pudo: el grabado no puede ser más hondo

`prof` está en 0.45 y ahí se queda. Teoricé dos veces cómo subirlo y las dos me
equivoqué:

1. "Con una rampa más ancha el salto baja." Falso: el desvanecido era un COSENO,
   cuya pendiente máxima es pi/2 veces la media. Lo pasé a RECTA, que es lo
   correcto y quedó, pero no alcanzó.
2. "Ahora sí, recta, el salto es `0.30*prof/borde_grabado`." También falso:
   medido, seguía saturando en `prof`.

Midiendo dónde ocurre: `g` pasa de +0.603 a -0.040 en una sola vuelta. La causa
es que `_marca_polar` devuelve una diferencia de RADIOS, no una distancia real,
y donde el contorno gira rápido eso cambia mucho más rápido que 1:1. Así que el
techo lo pone el contorno, no la rampa.

### El chaflán 1.30 es el mínimo, y hay que probarlo contra TODOS los `n`

Bajarlo a 1.25 daba más cara plana, y con n=16, 24, 28 y 32 el salto quedaba en
0.455 — pero con **n=20 saltaba a 0.502** y la pieza se pasaba sola a marcha
adaptativa. El exceso no lo produce el chaflán solo: cerca del borde el `min`
contra la envolvente cambia de rama, y ahí el escalón puede superar lo que cae
cada término por separado.

**Regla:** un parámetro que roza un umbral se prueba contra todos los valores del
mando que lo acompaña, no contra uno.

### La raya volvió a engordar sola: un rasgo en FRACCIÓN, no en mm

`SEMI_RAYA` estaba en fracción del radio de la figura, así que cada vez que se
agrandaba el dibujo la raya crecía con él. El usuario había pedido explícitamente
que fuera más fina y quedó en 1.19 mm; al quitar el recorte de las puntas, subir
`rel_figura` y agregar el disco máximo, volvió sola a 1.79 y 2.05 — o sea a los
1.89 que le molestaban, y peor.

Ahora es `ancho_raya`, en MILÍMETROS, y da 1.20 en cualquier disco.

**Regla:** un rasgo cuyo ancho es lo único que se ve va en la unidad en la que se
lo juzga —el cordón—, no en fracción de otra cosa que después se toca. Si no,
un cambio de tamaño deshace en silencio un pedido explícito.

### El `rm` que no borró nada: zsh aborta con un glob sin coincidencias

Corrí `rm -f carpeta/*.gcode carpeta/*.png` para limpiar antes de regenerar, y
NO BORRÓ NADA: en zsh, un patrón sin coincidencias —no había ningún `.png`—
aborta la línea entera antes de ejecutarla. El `-f` no ayuda, porque `rm` nunca
llega a correr.

El resultado fue peor que no limpiar: quedaron las dos tandas mezcladas, con
nombres distintos porque el freno de caudal les había dado otra velocidad, y no
hay forma de saber cuál es cuál mirando el nombre. Traté de separarlas midiendo
el deslizamiento del disco y tampoco sirvió —la medición depende de qué figura
toque muestrear y da entre -1.18° y +0.97° en archivos de la MISMA tanda—. Lo
que las separó fue la hora de modificación al segundo.

**Regla:** después de un `rm` de limpieza, listar la carpeta y comprobar. Y
mejor un glob por comando.

### Y el tamaño: el techo es la MESETA, no el disco

La cara plana es `2*(radio - borde)`, y `borde` no puede bajar de 1.30. Con el
disco por defecto (4.2) eso da Ø5.80. `pastillas_max` —disco Ø9.25, el máximo
que admite la envolvente— da **Ø6.65 de cara plana y figura 15 % mayor**, sigue
en paso fijo, y cuesta el juego axial (0.16 mm contra 0.94).

## ENROSCABA DURO: era el JUEGO AXIAL, no la holgura radial

El usuario imprimió los 240 mm enteros y **enrosca duro**. Medido sobre el
g-code con `verificar_encastre --ancho 1.0`, contra los machos que ya enroscaba
sin quejarse:

    macho_clasico_v1823                3.74 mm de juego axial (28 % del paso)
    macho_perlas_v1846                 3.74 mm (28 %)
    macho_caritas_intercalada_v1774    3.20 mm (24 %)
    pastillas Ø9.25, lo impreso        0.28 mm ( 2 %)          <- DURO

La holgura RADIAL da +0.195..+0.200 en las cuatro: por ahí no es. Lo que cambió
es cuánto llena el disco el canal del hilo. Ø9.25 tiene **diez veces menos
margen** que todo lo que funcionó, y menos que la variación del propio plástico.

Estaba escrito en el código antes de imprimirlo —`radio=None` avisa que Ø9.25
"queda MÁS APRETADO que el diente más gordo posible"— y se eligió el máximo
igual, porque las figuras se leían mejor. La tabla no era una advertencia
teórica.

**Que el cupón pasara y la pieza entera no, no es contradicción.** El cupón de
40 mm cruza 48 pastillas; los 240 mm cruzan 284. Con 0.28 mm de margen basta
una para que agarre, así que el cupón es un mal test de ajuste: mide el dibujo,
no la tolerancia.

### La salida: achatar, no achicar

Lo que aprieta es el eje AXIAL: el canal del hilo sólo tiene ancho ahí. En el
ángulo el disco no le pide nada a nadie, porque la vuelta de arriba está al
mismo ángulo. Bajar el radio paga en las dos direcciones y sólo cobra en una.

`--pastillas-achatado` (nuevo) achica el disco sólo en axial. Medido, n16,
capa 0.25:

    radio 4.625, achatado 1.00   juego 0.28 mm   disco 9.25 x 9.25   figura r 3.16
    radio 4.40,  achatado 1.00        0.67              8.80 x 8.80          2.95
    radio 4.20,  achatado 1.00        1.06              8.40 x 8.40          2.76
    radio 4.625, achatado 0.88        1.01              9.25 x 8.14          3.16

Las dos últimas dan el mismo milímetro de juego; la de achatado no pierde nada
de ancho de figura, que es donde se había ganado la legibilidad vía
`fig_ancho_rel`.

**Pero 0.88 SE VE ovalado**, y el usuario lo preguntó apenas lo leyó. El juego
no lo fija el radio ni el achatado por separado sino el SEMIEJE AXIAL
(`radio * achatado`), así que hay toda una familia de combinaciones con el mismo
ajuste y distinta forma. Medidas, todas con n16 y capa 0.25:

    radio  achat  disco (ancho x alto)  ovalidad  figura  juego
    4.625  0.88     9.25 x 8.14          12 %     r 3.16  1.01 mm
    4.50   0.92     9.00 x 8.28           8 %     r 3.04  0.97
    4.45   0.94     8.90 x 8.37           6 %     r 2.99  0.94   <- elegida
    4.40   0.95     8.80 x 8.36           5 %     r 2.95  0.97
    4.35   0.97     8.70 x 8.44           3 %     r 2.89  0.94
    4.30   1.00     8.60 x 8.60           0 %     r 2.85  0.86

El ALTO de la figura casi no cambia en toda la tabla (5.56 a 5.70 mm): lo único
que se compra con la ovalidad es ANCHO de figura, 6.32 contra 5.70. O sea que
pasar de 0.88 a 4.45/0.94 cuesta 5 % de ancho de dibujo y parte la ovalidad al
medio. Ésa es la elegida. Y no cuesta solape: el peor salto radial se queda en 0.450
(55 %) hasta achatado 0.85, porque ese salto lo pone la rampa del GRABADO
(prof/borde_grabado = 2.5 por mm), no el chaflán del disco (alto/borde = 1.52).
Desde 0.80 sí cobra (0.473, 53 %).

El barrido completo quedó en `output/rosca/prueba/holgura/`.

## LA PIEZA VIGENTE

    output/rosca/control/pastillas_240.gcode      240 mm, con receta (7 sliders)
    output/rosca/final/pastillas/macho_pastillas_n16_redonda_v1330.gcode
                                                  el cupón de 40 mm

Disco **Ø8.60 REDONDO** (radio 4.30, achatado 1.0 — el usuario la quiso redonda
de verdad), 16 por vuelta, capa 0.25, cordón 1.0, grabado 0.45, 1440 segmentos.
Juego axial **0.86 mm** (3x lo que enroscaba duro), holgura radial +0.200,
solape 55 %. 240 mm son 1.54 M movimientos, 66 MB y ~4 h.

`macho_pastillas_n16_MAX_capa025_v1330.gcode` sigue en la carpeta: es el que
imprimió bien pero enrosca duro. Sirve como referencia de calidad de impresión,
no para enroscar.

**1440 segmentos se queda.** El tramo mide 0.22 mm y la regla práctica es un
tercio del cordón (0.30 con cordón 1.0), así que 1080 alcanzaría; la diferencia
no se ve en el plástico, sólo en el peso. Por debajo sí se ve: a 720 el corazón
pierde la hendidura de arriba y a 360 es una mancha — es lo que dejó las caritas
sin dibujo cuando el generador tenía 360 fijos.

Y la densidad no le exige nada raro a la impresora: **96 movimientos por
segundo**, igual que el cupón que salió bien, porque el segmento y la velocidad
son los mismos. La nítida que falló iba a ~130 mov/s por correr a 30 mm/s —
cuarto sospechoso de aquellos errores, del mismo origen que los otros tres: la
velocidad que subió sola al bajar la capa.

## EL CENTRADO DE LAS FIGURAS: `_encuadre` deformaba y descentraba

El usuario dijo "creo que se puede mejorar el centrado de las figuras" y tenía
razón, con dos causas distintas dentro de `_marca_polar`.

**1. Centrar la CAJA no centra la figura.** La caja de una estrella con una
punta arriba llega a +1.00 y a -0.809, así que centrarla baja la estrella 0.096
de radio. Medido sobre el g-code, el centroide del grabado contra el centro del
disco daba:

    corazón   +0.598 mm      estrella  -0.256 mm
    carita    -0.406 mm      raya      -0.002 mm

Cada figura a una altura distinta. Con 284 pastillas en retícula eso es
exactamente lo que se lee como "mal centradas". Ahora las polares se centran en
el **centro de ÁREA**, que en una figura con simetría de giro —estrella,
círculo— cae en su centro de simetría.

**2. Escalar por `hx` y `hy` por separado ESTIRA la figura.** El mapa llevaba el
círculo de radio `radio` sobre la CAJA, así que cada forma se deformaba hasta
llenar un cuadrado: medido, la estrella salía 5.1 % más alta de lo que es y el
corazón 4.0 % más baja. Ahora el factor es uno solo. El estirado que sí se
quiere —`fig_ancho_rel`, para que las puntas pasen el cordón— sigue aparte, y en
el eje que es gratis.

**La carita necesitó tope.** No es polar, así que se centra midiendo su tinta
(`_centrar_ink`). Centrarla a secas la sube 0.62 mm y le deja los ojos a 0.11 mm
de la cara plana: la boca es un arco grueso y los ojos dos barras finas, así que
la tinta pesa abajo y pagar la corrección entera cuesta el borde. El
corrimiento se topa en 0.97 del radio de la figura —el mismo presupuesto que
gastan las polares— y sube 0.46 de los 0.62.

Después de las tres cosas, los cuatro centroides caen dentro de ±0.03 mm del
centro del disco, y los cuatro dibujos llegan como mucho a 2.76 de una cara
plana de 3.00.

## NITIDEZ DEL DIBUJO: manda el PASO DE CAPA, no el cordón

El usuario pidió figuras más nítidas y propuso más profundidad. Medido, el orden
de lo que rinde es otro:

    paso 0.30, cordón 1.0, prof 0.45   <- lo que venía
    paso 0.20, cordón 1.0, prof 0.45   el salto grande: los bordes curvos dejan
                                       de escalonarse
    paso 0.20, cordón 1.0, prof 0.65   más sombra, la figura se despega
    paso 0.20, cordón 0.8, prof 0.65   casi indistinguible de la anterior

**El borde de un grabado se cuantiza al PASO DE CAPA**, así que las curvas —la
sonrisa, los lóbulos del corazón— se dibujaban con escalones de 0.30 mm. El
cordón sólo limita el trazo más fino, y el más fino (la raya, 1.20 mm) ya son
1.2 cordones con 1.0: se dibuja igual. Bajar a 0.8 costaba pared para casi nada.

### IMPRESA: la de capa 0.20 salió CON ERRORES; la de 0.25 quedó mejor

Vigente: `macho_pastillas_n16_MAX_capa025_v1330` — capa 0.25, todo lo demás como
la que ya enroscaba. Confirmada por el usuario.

La de 0.20 falló por TRES causas que introduje juntas y ninguna avisé:

1. **0.20 sobre boquilla de 0.8 es el 25 %**, y nada acá se imprimió nunca por
   debajo de 0.30 (la referencia de Orca usa 0.40, o sea 50 %). Un cordón de
   1.0 x 0.20 es un aplastado de 5:1.
2. **La velocidad subió SOLA por el costado del freno de caudal.** El freno
   mantiene los mm3/s; al bajar la capa baja la sección por milímetro y deja
   correr más rápido: 22 -> 30 mm/s, y el movimiento RADIAL sobre las figuras
   de 19.8 a 28.4 mm/s.
3. **Forcé `--paso-fijo si`** para el grabado de 0.65, con 0.2 % del recorrido
   al 35 % de solape.

**Regla:** bajar la capa no es gratis aunque los verificadores digan IMPRIMIBLE.
Sube la velocidad por un camino indirecto, y hay un piso de capa/boquilla que
ningún script de este repo comprueba. Y cambiar tres cosas a la vez impide saber
cuál rompió: la de 0.25 cambia UNA.

### El techo de profundidad que había dado por cerrado estaba mal medido

Dije que `prof` no podía pasar de 0.45 porque el salto satura ahí. Cierto, pero
lo que importa no es el peor salto sino CUÁNTO RECORRIDO lo sufre:

    prof   peor salto   % del recorrido con menos de 50 % de solape
    0.45     0.454              0.000 %
    0.60     0.600              0.715 %
    0.75     0.750              0.969 %

Es un filo alrededor de cada figura, del mismo tipo que los valles de la
estrella o los bordes de sector de `interrumpida`, que ya damos por buenos. Hay
que forzar `--paso-fijo si` porque el criterio automático usa el máximo.

**Es la MISMA lección que el freno de caudal** (mediana -> p99): un criterio de
peor caso sobre una geometría con cantos vivos rechaza piezas sanas.

## MI ERROR: `verificar_encastre --ancho` vale 1.2 y nunca se lo pasé

Toda la sesión corrí `verificar_encastre` sin `--ancho` en piezas de cordón 1.0,
así que usó su defecto de 1.2. Los números que reporté estaban corridos:

    | | reporté | es |
    |---|---|---|
    | holgura radial | +0.096 | +0.196 |
    | juego axial | 0.16 mm | 0.29 mm |
    | apoyo | 16.3 % | 0.2 % |

La señal estaba en su PRIMERA LÍNEA y la pasé por alto quince veces:
`núcleo del recorrido R49.500 + medio cordón = R50.100 contra R50.00 la
compensación no cierra`. Con `--ancho 1.0` da R50.000 exacto. La herramienta
avisaba; yo miraba las líneas de abajo.

Y el dato que importa: **las pastillas casi no apoyan en el flanco** —0.2 %
contra 10.4 % del hilo clásico—. El disco toca el techo del riel pero su chaflán
no alcanza los flancos: centra, no hace tope axial.

**Regla:** cuando una herramienta imprime una línea de coherencia ("OK" / "no
cierra"), esa línea se lee ANTES que el resultado.

## LA REGLA QUE MÁS COSTÓ ESTA SESIÓN

**Cuando una medición contradice algo que ya se sabe, el roto es la medición.**
Pasó SEIS veces, y cada una costó una vuelta entera:

| lo que parecía | lo que era |
|---|---|
| 4 patrones de lienzo NO ENTRAN por 0.2–0.7 mm | el centro salía de la caja envolvente, y un patrón angular la corre justo eso |
| el apoyo da 0 % en todas las piezas | se medía en el δ de máxima holgura; una rosca apoya en el BORDE del juego axial |
| `interrumpida` tiene −65 % de solape | son 123 pares de 44 824, los bordes de sector, por diseño |
| la mariposa NO ENTRA, RMS 1.46 | rellenaba las fases sin medir con la TABLA, que tiene otro origen de fase |
| los 4 barrenos de `tuerca.stl` dan RMS 18–30 | saqué un prefiltro de radio creyéndolo optimización; sin él el rayo pega en el faldón |
| las versiones moduladas cambian la geometría | mi `grep "^G1 X"` no matchea `G1 F240 X...` |

Y una variante distinta, que conviene tener aparte: **cuando dos poblaciones
difieren en más de una cosa, cruzarlas por una sola atribuye el efecto a la
variable equivocada.** Medí que en Squeezy "el 70 % de los segmentos lentos
están al aire" y concluí que la velocidad seguía al voladizo. Era correlación de
ZONA: la celosía es a la vez la parte lenta y la parte al aire.

## LA HEMBRA: medida, y generada en modo vaso

`envolvente_hembra.py` traía la tabla `ENVOLVENTE` con la nota "medida sobre
tuerca.stl" y el script que la midió NO estaba en el repo. Ahora está:

- **`medir_hembra.py`** traza rayos desde el eje contra la malla y contrasta
  contra `rosca.perfil_hembra` = `ENVOLVENTE + 0.20`. Busca el (signo, origen de
  fase) que minimiza el error: si el modelo fuera falso, ningún origen daría
  residuo chico.
- Los **cuatro barrenos** de `tuerca.stl` dan RMS 0.019–0.029 mm. `mariposa_v3`
  y `mariposa_v3_hembra` dan 0.027. Cinco piezas independientes, misma tabla.
- De ahí sale **`rosca.perfil_hembra(d)`**, que antes no existía: sólo estaba la
  envolvente del MACHO, y sin la pared de la hembra no se puede dibujar tuerca.

**`gen_tuerca.py STL`** emite la tuerca. Tres intentos, los dos primeros míos y
malos:

1. STL del anillo a rebanar en Orca — deja la pieza a merced del laminador.
2. G-code de capas planas con las 4 paredes como offsets del mismo barreno. El
   exterior copiaba la rosca y ondulaba 1.9 mm: correcta por dentro, tornillo
   por fuera. *"La hembra no es hembra."*
3. **Modo vaso**, que es lo que el usuario dijo desde el principio.

**Con un cordón de pared la tuerca es topológicamente idéntica al macho**: un
tubo cuyo radio depende de la fase. Sólo cambia la función de radio — el macho
toma `perfil_clasico` y RESTA medio cordón; la hembra toma el barreno medido y
SUMA medio cordón, porque su pared queda afuera. Entra tal cual en
`generar_pieza`: 2 movimientos sin extruir en todo el archivo, sin costura, y
hereda paso fijo, primera vuelta apoyada y verificación de voladizo.

**Regla:** antes de escribir un recorrido nuevo, preguntarse si la pieza no es
la que ya se sabe hacer con otra función de radio. Escribí dos recorridos para
algo que era `generar_pieza` con `perfil_hembra + ancho/2`.

`--macizo` sigue estando para la versión de 5–7 mm de pared con exterior
cilíndrico, que es la única que sí necesita capas planas.

### El chaflán de entrada no es decoración

`generar_pieza` arranca la espiral con una RAMPA: los primeros 2 mm la z impresa
todavía no es la del modelo, la fase va corrida y el radio sale hasta **0.55 mm**
fuera de sitio (con `capas_base=0` es peor, 0.69: es la rampa, no el anillo). En
un macho da igual —el pie queda gordo y no estorba— pero en una hembra **ahoga
la boca** justo por donde entra el tornillo: sin arreglar, los cuatro machos
daban NO ENTRA por −0.031 mm.

Lo tapa un chaflán, que sólo QUITA material y no puede interferir. Y la
**pendiente importa tanto como la altura**: a 45° suma 0.30 al salto radial por
vuelta y la pieza se pasa sola a marcha adaptativa; a 0.40 (unos 22° desde la
vertical) repartido en 3 mm abre 0.8 mm en la boca y el paso fijo aguanta.

## EL ENCASTRE: `verificar_encastre.py`

Mide el **g-code emitido** contra la hembra, que es lo que `verificar_rosca.py`
—que valida la `FuncionRadio`— no hace. Entre la función y el plástico se meten
el medio cordón de compensación, el redondeo del paso fijo y los anillos de base.

`--hembra ARCHIVO` acepta **g-code o STL**: mide contra la tuerca concreta en vez
de contra la tabla. `--ancho-hembra` para cuando los cordones difieren — con
macho 1.0 contra hembra 1.2, leer las dos con el mismo ancho corre el riel medio
cordón y da +0.308 en vez de +0.208.

**El juego axial es el resultado, no un parámetro.** Enroscar es elegir una fase,
así que se barre el corrimiento axial δ y se busca el que deja más holgura; el
ANCHO del intervalo de δ que sigue entrando es cuánto cabecea la unión. Y el
apoyo se mide en el BORDE de ese intervalo, no en el centro: una rosca no carga
sobre la cresta sino sobre los flancos.

## EL PAR IMPRESO QUE FUNCIONA — la calibración que faltaba

El usuario trajo dos `.gcode.3mf` que imprimió y encajan, "aunque bailan un
poco". Extraídos y medidos:

    proceso        modo vaso (spiral_mode=1), capa 0.4, línea 0.82, PLA
    holgura radial +0.371 mm
    juego axial    4.08 mm = 30 % del paso   <-- esto es "bailan un poco"

**Eso cierra la duda que venía abierta.** Los 3.75 mm que mis scripts predicen
para nuestras piezas son REALES y son la magnitud que el usuario ya tiene en la
mano y tolera. Los **0.45 mm que dice `envolvente_hembra.py` son el número
muerto** del riel Ø11 de `fusion/tuerca/contrato.py`.

Y nuestras piezas son MÁS APRETADAS que lo que ya se sabe que entra: +0.20
contra sus +0.371.

### La causa del baile, y el arreglo (SIN PROBAR)

No es la holgura radial: es que el diente es mucho más angosto que el canal.

    perfil_clasico (el macho actual)   holgura +0.191   juego axial 3.75 mm (28 %)
    perfil_envolvente (el máximo)      holgura +0.200   juego axial 0.28 mm ( 2 %)

    ancho del diente a R51.0:  clásico 4.92 mm  ·  envolvente 8.23 mm  (de 13.5 del paso)

`rosca.perfil_mezcla(f)` gradúa entre los dos, y `gen_rosca --diente F` lo
expone. Con `--diente 1.0` el cupón mide 0.29 mm de juego, 65 % de solape e
IMPRIMIBLE. **El usuario pidió no iterar en esto todavía.**

Lo que cuesta: con el canal lleno, un flanco impreso gordo topa antes. Por eso
es un mando graduable y no un interruptor.

## EL CAUDAL: por ahí veníamos mal, no por la velocidad

Comparado contra los archivos impresos:

| | velocidad | área | caudal |
|---|---|---|---|
| su macho impreso (PLA) | 33.5 mm/s | 0.358 | **12.0 mm3/s** |
| su hembra impresa (PLA) | 43.5 mm/s | 0.151 | 6.6 |
| Squeezy | 8.0 mm/s | 0.960 | 7.7 |
| nuestro caritas v2400 | 40.0 mm/s | 0.490 | **19.7** |
| nuestra hembra v2400 | 40.0 mm/s | 0.639 | **25.6** |

Sus archivos declaran `filament_max_volumetric_speed = 12` (PLA) y `16` (PETG),
y su macho corre **exactamente a 12.0**: Orca le bajó la velocidad de 120 mm/s a
33.5 para no pasarse. Nosotros no teníamos ese freno y estábamos 64 % por encima
en el caritas y **113 % en la hembra**. Eso no sale como sobre-extrusión: sale
como **sub-extrusión**, línea flaca e irregular.

**En velocidad de cabezal estábamos bien** —sus piezas van a 33–43 mm/s contra
nuestros 40— así que el problema nunca fue ir rápido.

Y había un bug de reporte que lo escondía: **el generador anunciaba 14.7 mm3/s
mientras emitía 19.7.** Calculaba `ancho x 0.306`, o sea con la SUBIDA, cuando
la sección va con la SEPARACIÓN sobre la superficie, un 34 % mayor por el flanco
a 43°. Es la trampa de "las tres alturas" de `MAPA.md`, otra vez. Ahora
`velocidad.area_emitida` lo lee de los propios `ExtrusionGeometry`.

## LAS CARITAS NO SALÍAN PORQUE NO ESTABAN DIBUJADAS

`gen_rosca.py` tenía `SEGMENTOS = 360` fijo. A Ø103 son **0.86 mm por punto**, y
un ojo mide **3.4 mm de arco**: le tocaban **CUATRO puntos**, y a algunos rasgos
uno solo. Con `--segmentos 1440` pasan a 14. El archivo crece de 2.1 a 8.5 MB
pero el recorrido mide lo mismo — es resolución, no tiempo.

Sumado al caudal, son las dos causas candidatas. **Pendiente de confirmar con la
pieza impresa.**

## SQUEEZY, MEDIDO BIEN (corrige lo que decía `CIERRE-SUPERIOR.md`)

    zona                     sección     velocidad      caudal
    cúpulas (z<28, z>70)     0.961 mm2   480 siempre    7.7 mm3/s
    celosía (z 30..70)       0.501 mm2   480, y 240     4.0 mm3/s
                             (la mitad)  donde flota

- La **sección** cambia por ZONA, no por voladizo, y con tres decimales de
  constancia: es un valor declarado.
- La **velocidad** baja a la mitad donde flota, pero **sólo dentro de la
  celosía**: ahí los 240 están al aire el 71.5 % contra el 37.7 % de los 480.
- **En las cúpulas no modula nada.** Sus 653 segmentos al aire van a 480 y
  caudal pleno.
- Ventilador 0 hasta z 27.6, después 100 %. Sin `M204`.

**Una pared maciza —nuestras roscas, sus cúpulas— Squeezy la imprime a velocidad
y caudal constantes.** `lamparas/velocidad.py` traduce lo que hace en la celosía,
que es otra cosa; usarlo en pared maciza va MÁS ALLÁ de lo que la referencia
respalda. Y 240 sobre 2400 es 0.10 de la normal, cuando en Squeezy es 0.50 y
Claywoven pone el mínimo sano en 0.18.

## HERRAMIENTAS Y MANDOS NUEVOS

    medir_hembra.py            barrenos roscados de un STL contra la tabla
    verificar_encastre.py      g-code del macho contra hembra (tabla, g-code o STL)
    gen_tuerca.py STL          la tuerca en modo vaso (o --macizo)
    lamparas/velocidad.py      caudal real, tope por material, freno en voladizos
    rosca.perfil_hembra        la pared del barreno
    rosca.perfil_mezcla(f)     gradúa el ancho del diente

    gen_rosca.py  --ancho --segmentos --material --caudal-max --diente
                  --velocidad-voladizo --carpeta
    gen_tuerca.py --ancho --material --caudal-max --macizo --entrada --carpeta

`MATERIALES` y `CAUDAL_MAX` en `velocidad.py` salen de los `.3mf` impresos:
PLA 220/65/75 % y 12 mm3/s; PETG 245/80/50 % y 16.

**El eje de un STL no es el origen del archivo.** `mariposa_v3_hembra.stl` vive
en (0, 340) y en z 200..228. Se saca POR CUERPO de su caja envolvente en XY, y
el recorte por radio va DESPUÉS de centrar. La búsqueda vive en un solo sitio,
`medir_hembra.barrenos()`, que usan los tres scripts.

## OJO CON LOS NOMBRES

`output/rosca/caritas_v2400.gcode` **NO** es el patrón `caritas`: es
`caritas_relieve` guardado con otro nombre en una sesión anterior. La huella que
los separa es cuánto recorrido queda en el núcleo — 82 % el relieve, 43 % el
grabado. Y se descarta `p_caritas` sin medir nada: su mínimo es `r_grabado` =
51.30 y nunca llega al núcleo.

**Un g-code guardado con `--nombre` distinto del patrón pierde de qué patrón
salió.** Si se guarda con nombre propio, que el nombre lleve el patrón adentro.

## LO QUE SIGUE

1. **Imprimir `PLA_NUEVAS_*`** y ver si las caritas salen. Es lo único que decide
   entre las dos causas (resolución y caudal) o si son las dos.
2. **El baile**, con `--diente`. Está medido y sin probar; el usuario lo dejó
   para después.
3. **El ventilador**: los nuestros van al 75 % constante; Squeezy va a 0 % abajo
   de z 27.6, o sea casi todo un cupón de 40 mm. Sin decidir.
4. La hembra con pared 1.0 se pasó a **marcha ADAPTATIVA** (solape 44 %, bajo el
   umbral de 50). Es la decisión correcta del generador, pero deja de tener
   altura de capa constante. Verlo en el preview antes de imprimir.
5. `test_verificar.py` sigue con **1 de 13 fallando** —"el piso de altura de
   cordón se mide sobre el recorrido"— y viene de antes. Los veredictos de
   `verificar_pieza.py` cargan esa duda.
6. `fusion/tuerca/contrato.py` sigue con los números muertos del riel Ø11
   (`A_MAESTRO`, `R_BARRENO`). Reescribirlo contra `perfil_hembra`.

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
