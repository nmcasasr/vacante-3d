"""
Pintar patrones sobre la superficie de una pieza en modo vaso.

La idea que pediste: una función que, dado un punto de la superficie, diga si
ahí va o no va el dibujo. En modo vaso cada punto del recorrido queda definido
por dos números —el ángulo alrededor del eje y la altura— así que una máscara
es exactamente eso:

    mascara(angulo_rad, t) -> 0.0 (fondo) .. 1.0 (dibujo)

donde `t` va de 0.0 en la base a 1.0 en el borde. Es el mismo par de argumentos
que ya reciben `funcion_radio` y `funcion_dz` en `comun.generar_pieza()`, así
que una máscara se enchufa directo en cualquier patrón sin tocar el generador.

## Cómo se dibuja la máscara sobre la pieza

Hay dos formas, y NO son intercambiables:

- **Como textura** (lo que hace `bowls/zigzag.py`): donde la máscara vale 1, el
  recorrido zigzaguea; donde vale 0, va liso. El dibujo se ve por relieve y por
  cómo pega la luz. Cuesta cero: es la misma cantidad de material, el mismo
  tiempo, y el cambio se decide punto por punto.

- **Como color**, cambiando de filamento al entrar y salir del dibujo. Se puede
  —`colores.cambio_ams()` está para eso— pero para un dibujo con detalle **no
  funciona**, por dos motivos independientes, los dos medidos:

  1. *Tiempo.* Cada cambio del AMS son ~56 s (29 s de descarga + 25 s de carga,
     números del propio perfil de Bambu). Una carita con ojos y boca, de 40 mm
     de alto, cruza unas 100 capas y necesita del orden de 10 cambios por capa:
     1000 cambios, casi 16 h **solo cambiando filamento**.

  2. *Sangrado*, que es peor y no se arregla con tiempo. A radio 40 una vuelta
     entera consume 33 mm de filamento, y un blanco→negro tarda ~70 mm en salir
     limpio: **2.1 vueltas**. Un ojo ocupa 15° de arco, o sea 0.04 vueltas. El
     color tardaría 50 veces más en limpiarse que lo que dura el detalle que
     querías pintar. Con purga se arregla el sangrado y se multiplica el tiempo.

  El color sí sirve para **bandas horizontales**: ahí el cambio dura una vuelta
  entera o más y el sangrado queda como un degradado de borde, que es
  justamente el efecto que busca `colores.py`.

O sea: **la forma se hace con textura, el color se hace por bandas.** Es lo que
combinan las piezas de referencia, y es lo que sale bien en una A1.

## Ver la máscara antes de imprimir

`rasterizar()` la dibuja en ASCII en la terminal. Iterar ahí cuesta
milisegundos; iterar generando gcode cuesta minutos.
"""

import functools
import inspect
import math
from typing import Callable, List

# (angulo_rad, t) -> 0.0 (fondo) .. 1.0 (dibujo)
Mascara = Callable[[float, float], float]

TAU = 2 * math.pi


def _envolver(delta: float) -> float:
    """Lleva una diferencia de ángulos al rango [-pi, pi]."""
    return (delta + math.pi) % TAU - math.pi


def constante(valor: float = 1.0) -> Mascara:
    """Máscara uniforme. Útil como fondo o para desactivar el dibujo."""
    return lambda angulo, t: valor


def banda(desde_t: float, hasta_t: float) -> Mascara:
    """Franja horizontal entre dos alturas relativas."""
    return lambda angulo, t: 1.0 if desde_t <= t <= hasta_t else 0.0


def sectores(cantidad: int = 5, desde: float = 0.0, hasta: float = 1.0) -> Mascara:
    """
    Escalera alrededor de la pieza: `cantidad` gajos, cada uno con su peso.

    Es la máscara de los CUPONES DE MATRIZ. Un patrón convierte el peso en
    amplitud —`fondo + (figura - fondo) x peso`— así que una escalera en el
    ángulo es una escalera de amplitudes alrededor del cilindro. Eso deja el
    eje vertical libre para barrer otra cosa (`barrido_puas`, `barrido`), y una
    sola pieza prueba las dos variables cruzadas en vez de dos piezas.

    El corte entre gajos es DURO a propósito, igual que en `_bandas`: la gracia
    de un cupón es poder decir "el tercer gajo sirve y el cuarto no", y con un
    degradé no hay gajos, hay un continuo del que no se lee un número.

    Ojo con el salto que eso mete: entre dos gajos el radio cambia de golpe
    dentro de la MISMA vuelta. No es el salto entre vueltas —que es el que
    gobierna el apoyo— sino un escalón lateral, y el cordón lo tiende como
    cualquier otro cambio de radio dentro de la vuelta.

    Args:
        cantidad: cuántos gajos.
        desde, hasta: el peso del primero y el del último. Con (0, 1) el primer
            gajo sale al nivel del fondo y el último a la amplitud entera.
    """
    n = max(1, int(cantidad))
    if n == 1:
        return lambda angulo, t: hasta
    paso = (hasta - desde) / (n - 1)

    def mascara(angulo: float, t: float) -> float:
        k = int((angulo % TAU) / TAU * n)
        return desde + paso * min(n - 1, k)

    return mascara


def carita(
    feliz: bool = True,
    angulo_centro: float = 0.0,
    ancho_grados: float = 140.0,
    centro_t: float = 0.5,
    alto_t: float = 0.55,
    grosor: float = 0.16,
) -> Mascara:
    """
    Una carita, feliz o triste, centrada en un ángulo.

    El truco para que no se deforme: se trabaja en coordenadas LOCALES de la
    cara, `(u, v)`, las dos normalizadas a -1..1 dentro del recuadro que ocupa
    el dibujo. Así el ancho se mide en grados y el alto en fracción de la
    pieza, y la cara se estira o encoge con la pieza en vez de quedar pegada a
    un tamaño en mm que después no entra.

    Args:
        feliz: True sonríe, False está triste (la boca se invierte).
        angulo_centro: dónde va la cara, en radianes.
        ancho_grados: cuánto arco ocupa. 140° deja lugar para dos caras
            opuestas sin que se toquen.
        centro_t: altura relativa del centro de la cara (0..1).
        alto_t: qué fracción de la altura ocupa.
        grosor: espesor del trazo, en unidades locales.

    Returns:
        Una `Mascara`.
    """
    medio_ancho = math.radians(ancho_grados) / 2
    medio_alto = alto_t / 2

    def mascara(angulo: float, t: float) -> float:
        u = _envolver(angulo - angulo_centro) / medio_ancho
        v = (t - centro_t) / medio_alto
        # fuera del recuadro de la cara no hay nada que dibujar
        if abs(u) > 1.2 or abs(v) > 1.2:
            return 0.0

        # --- ojos: dos discos ---
        for ou in (-0.36, 0.36):
            if (u - ou) ** 2 + (v - 0.34) ** 2 < 0.15 ** 2:
                return 1.0

        # --- boca: un arco de circunferencia ---
        # Sonrisa: la MITAD DE ABAJO de un círculo alto. Tristeza: la mitad de
        # ARRIBA de un círculo bajo. Es el mismo arco espejado, y por eso las
        # dos caras salen del mismo código con un solo signo de diferencia.
        cv, radio_boca = (0.34, 0.62) if feliz else (-0.92, 0.62)
        d = math.hypot(u, v - cv)
        if abs(d - radio_boca) < grosor / 2:
            en_arco = (v - cv) < -0.12 if feliz else (v - cv) > 0.12
            if en_arco:
                return 1.0
        return 0.0

    return mascara


def caritas(
    angulo_feliz: float = 0.0,
    ancho_grados: float = 140.0,
    centro_t: float = 0.5,
    alto_t: float = 0.55,
    grosor: float = 0.16,
) -> Mascara:
    """
    Feliz de un lado, triste del otro. Es `--p mascara=caritas`.

    La triste va a 180°, así que en la pieza terminada ves una cara por lado.

    Los parámetros están escritos uno por uno y no recogidos en un `**kwargs`
    a propósito: esta función REENVÍA a `carita`, que es más angosta que
    cualquier cosa. Con `**kwargs` la firma prometía aceptar todo, `acepta` le
    creía y le mandaba el bolso entero del CLI —`cantidad`, `semilla`,
    `rugosidad`, que son de las manchas— y reventaba adentro de `carita`. Un
    `**kwargs` que reenvía no es una promesa: es una firma que no se puede
    inspeccionar.
    """
    comun = dict(ancho_grados=ancho_grados, centro_t=centro_t,
                 alto_t=alto_t, grosor=grosor)
    a = carita(feliz=True, angulo_centro=angulo_feliz, **comun)
    b = carita(feliz=False, angulo_centro=angulo_feliz + math.pi, **comun)
    return unir(a, b)


def parches(
    cantidad: int = 6,
    semilla: int = 0,
    ancho_grados: float = 70.0,
    alto_t: float = 0.10,
    borde: float = 0.25,
) -> Mascara:
    """
    Manchas sueltas repartidas por la pieza, para pintar con dos colores.

    Pensado para lo contrario de un degradado: en vez de un color y después el
    otro, parches del segundo color salpicados sobre el primero. Y pensado para
    ser BARATO, que es lo que un dibujo con detalle no puede ser.

    ## Qué lo hace barato

    Un cambio de filamento se paga por cada vez que el recorrido ENTRA o SALE
    de la figura. Una carita cuesta ~10 cambios por capa, porque una capa a la
    altura de los ojos cruza cuatro bordes por cara. Un parche cuesta 2 por
    capa, y solo en las capas que lo atraviesan.

    O sea que el costo es `2 · cantidad · (alto_t · n_capas)` y no depende de
    lo ancho que sea el parche. **Pocos parches y altos** sale barato; muchos y
    bajitos sale igual de caro que la carita. `generar_pieza` imprime el total
    antes de generar.

    Y el sangrado acá no molesta: un parche de 10 capas dura varias vueltas, y
    que sus bordes salgan difuminados es lo que lo hace ver orgánico en vez de
    recortado.

    Args:
        cantidad: cuántos parches.
        semilla: cambiala para otra distribución.
        ancho_grados: qué arco ocupa cada uno. No afecta el costo.
        alto_t: qué fracción de la altura ocupa cada uno. **Este sí** afecta el
            costo, linealmente.
        borde: cuánto del parche es transición suave (0 = borde duro).

    Returns:
        Una `Mascara`.
    """
    from .estructura import _fases

    r = _fases(semilla, cantidad * 3)
    centros = []
    for _ in range(cantidad):
        centros.append((
            next(r) * TAU,
            0.08 + next(r) * 0.84,
            0.7 + next(r) * 0.6,           # tamaños distintos, si no parece estampado
        ))
    sigma_a = math.radians(ancho_grados) / 2
    sigma_t = alto_t / 2

    def mascara(angulo: float, t: float) -> float:
        for centro_a, centro_t, escala in centros:
            da = _envolver(angulo - centro_a) / (sigma_a * escala)
            dt = (t - centro_t) / (sigma_t * escala)
            d = math.hypot(da, dt)
            if d <= 1.0 - borde:
                return 1.0
            if d < 1.0:
                return (1.0 - d) / max(borde, 1e-6)
        return 0.0

    return mascara


def flores(
    cantidad: int = 7,
    petalos: int = 6,
    tamano: float = 46.0,
    variacion: float = 0.45,
    corazon: float = 0.42,
    borde_mm: float = 3.0,
    semilla: int = 0,
    radio_mm: float = 35.0,
    altura_mm: float = 150.0,
) -> Mascara:
    """
    Flores repartidas por la pieza, para dibujar POR TEXTURA (no por color).

    Es la máscara de la lámpara de referencia: un tubo cubierto de púas, y las
    flores aparecen porque ahí las púas se apagan y la pared queda lisa. O sea
    que lo que se ve no es un contorno pintado sino un cambio de piel, y por eso
    la figura se lee sola con la luz rasante y no cuesta ni un cambio de
    filamento. Ver el docstring del módulo.

    ## Por qué se mide en MILÍMETROS y no en grados

    `carita()` trabaja en un recuadro normalizado —ancho en grados, alto en
    fracción de la pieza— y le sirve, porque una cara admite estirarse con la
    pieza. Una flor no: si el ancho va en grados y el alto en fracción de
    altura, la misma flor sale redonda en un tubo de Ø70 y chatísima en uno de
    Ø140. Acá la superficie se desenrolla a mm de verdad
    —`radio_mm · Δángulo` a lo ancho, `altura_mm · Δt` a lo alto— así que
    `tamano` es un diámetro que se puede medir con una regla sobre la pieza
    impresa, y las flores siguen siendo redondas en cualquier silueta.

    ## El BORDE no es un detalle estético: decide si la pieza se imprime

    En modo vaso cada vuelta se apoya sobre la de abajo, y `marcha_vertical`
    aplasta el paso vertical hasta que la separación real vuelva a valer un
    cordón. El borde de la flor es donde la púa pasa de estar afuera a no
    estar: con un borde DURO, dos vueltas vecinas se llevan la amplitud entera
    de diferencia en ese ángulo, `marcha_vertical` lo ve como una pared
    acostada y desploma el paso de toda la pieza al mínimo. No es un defecto
    local — el paso es uno solo por vuelta, así que un borde duro en una flor
    cuesta la pieza entera.

    Con el borde en mm, el salto por vuelta es `amplitud · altura_capa / borde_mm`,
    y `bowls/puas.py` lo calcula y avisa antes de generar nada. Y como eso solo
    no alcanza —el contorno entre dos pétalos corre casi horizontal, así que se
    mueve mucho más rápido de lo que dice esa cuenta— `puas.py` además promedia
    la máscara en vertical. Ver el comentario de `peso()` allá.

    Args:
        cantidad: cuántas flores. Se reparten al azar pero reproducible.
        petalos: lóbulos de cada flor.
        tamano: diámetro medio en mm, medido sobre la superficie.
        variacion: cuánto varían de tamaño entre sí (0 = todas iguales).
        corazon: qué fracción del radio ocupa el disco central. 1 = un círculo
            sin pétalos; 0.2 = pétalos largos y flacos.
        borde_mm: ancho del desvanecido, en MILÍMETROS de superficie. Lleva la
            unidad en el nombre porque `parches()` ya tiene un `borde` que es
            una fracción, y los dos aparecen como slider: sin distinguirlos, el
            control heredaba el rango 0..1 del otro y no dejaba pasar de 1 mm.
        semilla: cambiala para otra distribución.
        radio_mm, altura_mm: el tamaño de la pieza. Los inyecta el patrón, no
            hace falta escribirlos a mano.

    Returns:
        Una `Mascara`. Vale 1 DENTRO de la flor.
    """
    from .estructura import _fases

    # Repartidas, no sorteadas. `parches()` sortea las dos coordenadas y le
    # alcanza porque son pocas manchas y da igual dónde caigan; acá las flores
    # SON el dibujo, y con azar puro nueve de ellas se apelotonaban en media
    # vuelta y dejaban la otra media lisa. Así que la altura va estratificada
    # —una por franja— y el ángulo avanza el ángulo áureo, que es la forma
    # clásica de repartir puntos en un círculo sin que se alineen nunca. El azar
    # queda para lo que sí conviene que sea azar: el desorden alrededor de esa
    # posición, el tamaño y la rotación de los pétalos.
    AUREO = 0.6180339887498949
    r = _fases(semilla, cantidad * 3 + 1)
    fase0 = next(r)
    centros = []
    for i in range(cantidad):
        franja = (i + 0.5) / cantidad
        centros.append((
            (fase0 + i * AUREO + (next(r) - 0.5) * 0.12) * TAU,   # alrededor del eje
            0.04 + 0.92 * min(1.0, max(0.0,
                  franja + (next(r) - 0.5) * 0.8 / cantidad)),    # a qué altura
            1.0 + (next(r) * 2 - 1) * variacion,                  # su tamaño
            i * AUREO * TAU,                                      # giro de los pétalos
        ))

    def _dentro(du: float, dv: float, radio: float, giro: float) -> float:
        """Cuánto vale la flor a `(du, dv)` mm de su centro."""
        d = math.hypot(du, dv)
        # Fuera del círculo que la contiene, ni se calcula el pétalo.
        if d > radio + borde_mm:
            return 0.0
        if d < radio * corazon:
            return 1.0
        fi = math.atan2(dv, du) - giro
        # |cos(n·fi/2)| tiene n lóbulos en una vuelta entera, y cada lóbulo
        # llega a 1: el contorno va de `corazon·radio` (entre pétalos) a
        # `radio` (en la punta del pétalo).
        borde_r = radio * (corazon + (1 - corazon) * abs(math.cos(petalos * fi / 2)))
        if d <= borde_r:
            return 1.0
        if borde_mm <= 0 or d >= borde_r + borde_mm:
            return 0.0
        u = 1.0 - (d - borde_r) / borde_mm
        return u * u * (3 - 2 * u)      # smoothstep, sin escalón

    def mascara(angulo: float, t: float) -> float:
        peso = 0.0
        for centro_a, centro_t, escala, giro in centros:
            du = _envolver(angulo - centro_a) * radio_mm
            dv = (t - centro_t) * altura_mm
            peso = max(peso, _dentro(du, dv, tamano / 2 * escala, giro))
            if peso >= 1.0:
                return 1.0
        return peso

    return mascara


# --- el isotipo de Kadzi -------------------------------------------------
#
# Leído del SVG de la marca (`Isotipo.svg`, viewBox 425.19 x 425.23, con la `y`
# hacia ABAJO como manda SVG). Son cuatro piezas: un triángulo grande apuntando
# a la izquierda, dos chicos apuntando a la derecha y un rombo. Juntas se leen
# como una K.
#
# Se guardan en las coordenadas del SVG y no normalizadas para que se pueda
# volver al archivo y comparar número por número si el dibujo cambia.
_ISO_LADO = 425.19
_ISO_SD = 135.29 * math.sqrt(2) / 2      # semidiagonal del rombo (un cuadrado a 45°)
_ISO_PARTES = (
    [(212.59, 0.04), (314.64, 102.08), (212.59, 204.13)],          # triángulo de arriba
    [(212.59, 221.14), (314.64, 323.18), (212.59, 425.23)],        # el de abajo
    [(329.5, 212.6 - _ISO_SD), (329.5 + _ISO_SD, 212.6),
     (329.5, 212.6 + _ISO_SD), (329.5 - _ISO_SD, 212.6)],          # el rombo
    [(191.33, 0.0), (191.33, 425.19), (0.0, 212.59)],              # el triángulo grande
)


def _en_poligono(x: float, y: float, poly) -> bool:
    """Punto dentro de un polígono, por cruces de rayo."""
    n = len(poly)
    dentro = False
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


def _encoger(poly, k: float):
    """El polígono encogido hacia su centro un factor `k` (1.0 = igual)."""
    cx = sum(x for x, _ in poly) / len(poly)
    cy = sum(y for _, y in poly) / len(poly)
    return [(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in poly]


def _en_isotipo(du: float, dv: float, lado: float, giro: float,
                separacion: float = 0.0) -> bool:
    """
    El isotipo inscrito en un cuadrado de `lado` mm, girado `giro` grados.

    `du` va a la derecha y `dv` hacia ARRIBA, los dos en mm desde el centro del
    dibujo. Con `giro=90` el triángulo grande —que en el archivo apunta a la
    izquierda— queda apuntando hacia ARRIBA, que es como va en la pieza.

    El giro se deshace sobre la CONSULTA en vez de rotar los polígonos: así los
    puntos quedan escritos igual que en el SVG y el giro es una perilla.
    """
    if lado <= 0 or abs(du) > lado or abs(dv) > lado:
        return False
    g = math.radians(-giro)
    px, py = du, -dv                      # a `y` hacia abajo, como el SVG
    qx = px * math.cos(g) - py * math.sin(g)
    qy = px * math.sin(g) + py * math.cos(g)
    # `lado` es la SEMI-caja, así que la escala es media viewBox por semi-caja.
    # Con `_ISO_LADO` entero el dibujo salía a la mitad de lo pedido.
    x = qx / lado * (_ISO_LADO / 2) + _ISO_LADO / 2
    y = qy / lado * (_ISO_LADO / 2) + _ISO_LADO / 2
    if not (0.0 <= x <= _ISO_LADO and 0.0 <= y <= 425.23):
        return False
    # `separacion` ENCOGE cada pieza para ensanchar los huecos entre ellas.
    #
    # Es lo que hace que el dibujo se LEA. Los triángulos y el rombo se
    # distinguen por los huecos que los separan, y esos huecos miden ~1.5 mm en
    # un isotipo de 16, mientras que una púa mide 2.62: la rejilla se los come y
    # el logo sale como una mancha alta y pareja. Medido, el relieve cruzando el
    # logo daba 3.6 4.0 4.0 4.2 4.0 — sin un solo valle.
    #
    # Ensanchando el hueco hasta que quepa una púa entera, ahí SÍ falta una púa
    # y el hueco se ve. Va en mm de superficie, que es como se piensa: "quiero
    # 3 mm de aire entre los triángulos".
    if separacion <= 0.0:
        return any(_en_poligono(x, y, P) for P in _ISO_PARTES)
    k = max(0.05, 1.0 - separacion / lado)
    return any(_en_poligono(x, y, _encoger(P, k)) for P in _ISO_PARTES)


def hoja(
    columnas: int = 4,
    filas: int = 1,
    largo_mm: float = 60.0,
    ancho_mm: float = 28.0,
    punta: float = 1.0,
    panza: float = 0.12,
    tallo_mm: float = 8.0,
    tallo_ancho_mm: float = 3.0,
    tallo_afina: float = 0.45,
    vena_mm: float = 3.2,
    degradado: float = 0.0,
    k: int = 1,
    brazo: float = 0.62,
    borde_mm: float = 1.5,
    iso_mm: float = 0.0,
    iso_giro: float = 90.0,
    iso_giro2: float = -90.0,
    iso_separacion: float = 0.0,
    iso_t: float = 0.5,
    iso_t2: float = 0.0,
    patron: str = "",
    patron_puas: int = 60,
    patron_fila_mm: float = 3.6,
    patron_fila0: int = 2,
    patron_corrimiento: int = 0,
    patron_alineado: bool = False,
    giro_celdas: float = 0.0,
    patron_z0: float = 0.8,
    patron_copias: int = 4,
    radio_mm: float = 25.0,
    altura_mm: float = 75.0,
) -> Mascara:
    """
    La hoja de Kadzi: una hoja con tallo y la K del logo inscrita.

    El truco del dibujo es que **la nervadura central de la hoja ES el asta de
    la K**. En el logo, la K son un rombo alto partido por una hendidura
    vertical y dos brazos que salen del medio hacia la derecha; en una hoja esa
    hendidura ya existe y se llama nervadura. Así que la marca no se estampa
    encima de la hoja: se lee en sus nervios. Por eso `k` no dibuja asta propia
    — dibuja sólo los dos brazos.

    El tallo no es decorativo: sin él la hoja se lee como una almendra o un ojo,
    porque una lente simétrica no tiene arriba ni abajo. El tallo y la panza
    —el ensanchamiento por debajo del medio— son las dos cosas que le dan
    orientación.

    Trabaja en MILÍMETROS de superficie y no en grados, como `flores` y a
    diferencia de `carita()`: una hoja tiene que salir con la misma proporción
    en un tubo de Ø50 que en uno de Ø68. `radio_mm` y `altura_mm` los inyecta
    el patrón (ver `GEOMETRIA`).

    Devuelve 1 en la carne de la hoja y 0 en el fondo Y EN LAS VENAS, o sea que
    las venas salen hundidas al nivel del fondo. En `bowls/puas` eso es un
    turupe corto donde va la vena y uno largo en la carne, que es lo que las
    hace visibles: si la vena valiera 0.5 no se leería ni como una cosa ni como
    la otra.

    ## Los tamaños se eligen contra la rejilla, no a ojo

    `bowls/puas` dibuja con un "punto" de `2·pi·radio / puas` de ancho por
    `(lisas + con_patron) · altura_capa` de alto — en un Ø50 típico, 2.24 x
    2.40 mm. **Un rasgo más fino que eso no se dibuja.** Los valores por defecto
    de acá salen de esa cuenta y no del croquis:

        media hoja (donde va la K)   14 mm  ->  6.3 puntos
        vena                        3.2 mm  ->  1.4 puntos
        tallo                       3.0 mm  ->  1.3 puntos

    El primer intento usó las medidas del croquis a mano —hoja de 13 x 30, vena
    de 2— y no se leyó nada: media hoja daba 2.9 puntos y la vena 0.9, menos de
    uno. `construir()` de `puas` imprime el tamaño del punto en cada corrida.

    Args:
        columnas: hojas alrededor de la pieza.
        filas: hileras a lo alto. Con más de una, las impares van corridas
            media columna para que queden en tresbolillo y no en cuadrícula.
            Ojo: dos hileras obligan a hojas de la mitad de alto, y ahí la K
            deja de entrar.
        largo_mm, ancho_mm: el alto y el ancho de la hoja, sin contar el tallo.
        punta: cuán afilada es la punta. 1.0 la deja en punta franca; por
            debajo se redondea hacia una elipse y por encima se afila.
        panza: cuánto se corre hacia abajo el punto más ancho, en fracción del
            largo. 0 deja la hoja simétrica —un ojo—; 0.12 la baja lo justo
            para que se lea como hoja.
        tallo_mm: largo del tallo por debajo de la hoja. 0 lo saca.
        tallo_ancho_mm: ancho del tallo DONDE NACE de la hoja. Tiene que valer
            al menos un punto de la rejilla o no se dibuja.
        tallo_afina: qué fracción de ese ancho le queda a la punta de abajo.
            1.0 deja el tallo recto —un palito pegado—; 0.45 lo afina lo justo
            para que se lea como parte de la hoja. **Ojo con la rejilla**: la
            punta mide `tallo_ancho_mm x tallo_afina` y si eso baja de un punto,
            la punta del tallo no se dibuja y el afinado se corta de golpe.
        vena_mm: ancho de la nervadura y de los brazos de la K.
        degradado: cuánto BAJA el relieve hacia el centro de la hoja. 0 (por
            defecto) deja la hoja pareja, que es como una meseta de canto vivo y
            se lee cuadrada. Con 0.2, el borde de la hoja sale entero y el
            centro apenas por encima del fondo, así que la hoja se ve abombada
            hacia adentro en vez de estampada.

            Es el peso en el CENTRO, en fracción: el patrón lo convierte en
            `amplitud_fondo + (amplitud - amplitud_fondo) x degradado`. Con 0.2
            sobre un fondo de 1.25 y una figura de 7, el centro sale a 2.4 mm.

            **NEGATIVO da vuelta la hoja**: con -0.2 el relieve baja hacia el
            CONTORNO y sube hacia el eje, o sea abombada hacia afuera. El tallo
            NO se da vuelta, porque ya nace alto en el medio.

            **El TALLO va al revés**: alto en el medio y fino en los cantos,
            que es como es un tallo. Con la regla de la hoja saldría como una
            canaleta, hundido justo en el eje.

            Ojo con la rejilla: el degradado es una rampa suave y el patrón la
            cuantiza a puntos de un par de milímetros. Si la hoja mide pocos
            puntos de ancho, la rampa sale en dos o tres escalones.
        k: 1 dibuja los dos brazos; 0 deja la hoja con la nervadura sola.
        brazo: la pendiente de los brazos, en fracción de `largo/ancho`. 0.62
            los saca a media altura del borde, que es la proporción del logo.
        iso_mm: tamaño del ISOTIPO de Kadzi, en mm de lado, dibujado en el hueco
            entre dos hojas. 0 (por defecto) no lo dibuja y la máscara queda
            como estaba. Ojo con la rejilla: el isotipo tiene rasgos finos —el
            rombo y los triángulos chicos— y por debajo de unos 14 mm se
            empastan en el punto del patrón.
        iso_giro: grados del isotipo de ARRIBA. 90 (por defecto) deja el
            TRIÁNGULO GRANDE apuntando hacia arriba; en el archivo de la marca
            apunta a la izquierda.
        iso_giro2: grados del de ABAJO. -90 lo deja espejado respecto del de
            arriba, o sea con el triángulo grande hacia abajo.
        patron: el dibujo YA RESUELTO sobre la rejilla, un carácter por púa y
            una línea por fila (una fila = un ciclo `lisas + con_patron`). `0`
            o `#` ponen púa. Las líneas se separan con `/` o salto de línea.
            Es lo que hay que usar cuando el dibujo tiene rasgos del tamaño de
            una púa: un polígono muestreado se come los huecos y sale una
            mancha pareja; la rejilla imprime exactamente lo escrito.
        patron_puas: cuántas púas tiene la vuelta, para mapear ángulo a columna.
        patron_fila_mm: alto de una fila en mm, o sea
            `(lisas + con_patron) x altura_capa`.
        patron_fila0: en qué BANDA de la cadencia arranca la fila de abajo del
            dibujo. Se cuenta en bandas y no en mm a propósito: cada `0` es una
            columna de púas durante una banda entera, así que las filas tienen
            que caer sobre las bandas o cada punto queda partido entre dos.
        patron_z0: z donde arranca la primera banda, o sea el espesor del piso.
        patron_copias: cuántas veces se repite alrededor de la pieza.
        iso_separacion: cuánto se ENCOGE cada pieza del isotipo, en mm, para
            ensanchar los huecos entre ellas. 0 deja el dibujo tal cual. Hace
            falta porque los huecos originales son más finos que una púa y el
            patrón se los come: el logo sale como una mancha alta y pareja. Con
            el hueco de una púa o más, ahí FALTA una púa y el dibujo se lee.
        iso_t: altura relativa del isotipo de ARRIBA.
        iso_t2: altura del de ABAJO, en el mismo hueco. 0 lo apaga y queda uno
            solo.
        borde_mm: en cuántos mm se desvanece el CONTORNO. Las venas no se
            desvanecen: son las que tienen que leerse filosas.
        radio_mm, altura_mm: el tamaño real de la pieza. Los inyecta el patrón.
    """
    columnas = max(1, int(columnas))
    filas = max(1, int(filas))
    semi_l = max(largo_mm / 2, 1e-6)
    semi_a = max(ancho_mm / 2, 1e-6)
    # el conjunto hoja+tallo se centra en su franja: el centro de la HOJA queda
    # medio tallo por encima del centro del conjunto
    subida = tallo_mm / 2

    # PARIDAD: cuántas celdas de púa puede cubrir la hoja sin salir torcida.
    #
    # La celda de la púa `k` es la fase [k, k+1). Con la hoja centrada en un
    # BORDE de celda —que es donde cae sola, en `c/columnas * TAU`— ninguna
    # celda es su propio espejo: la celda 0 se refleja en la -1, la 1 en la -2.
    # La hoja cubre entonces un número PAR de celdas y al hueco le quedan PAR.
    # Y el logo mide 9 columnas, impar: nunca encaja centrado.
    #
    # Corriendo la hoja MEDIA CELDA el eje pasa por el centro de una celda, esa
    # celda es su propio espejo y los dos números pasan a impares. De regalo,
    # el centro del hueco cae exacto en el centro de la celda `kc`, que es
    # donde va la columna del medio del logo, así que el dibujo no se mueve.
    #
    # `giro_celdas` se mide en celdas de púa, no en grados, porque lo que hay
    # que alinear es la rejilla y no la geometría.
    giro = giro_celdas / max(1, patron_puas) * TAU

    centros = []
    for f in range(filas):
        t_c = (f + 0.5) / filas
        corrimiento = 0.5 * (f % 2)
        for c in range(columnas):
            centros.append(((c + corrimiento) / columnas * TAU + giro, t_c))

    # Los dos isotipos van APILADOS EN EL MISMO HUECO —uno arriba (`iso_t`) y
    # otro abajo (`iso_t2`)—, entre dos hojas. Eso pide hojas ANCHAS DE POCAS:
    # con dos hojas en una vuelta de 157 mm el hueco mide 60 y pico, y ahí el
    # logo entra grande. Con cuatro hojas el hueco baja a 15.3 mm y no entra
    # nada legible.
    _iso_huecos = [(c + 0.5) / columnas * TAU + giro for c in range(columnas)]

    # --- el dibujo como REJILLA -------------------------------------------
    #
    # `patron` es el dibujo ya resuelto sobre la rejilla del patrón: un
    # carácter por PÚA y una línea por FILA (una fila = un ciclo
    # `lisas + con_patron`). `0` o `#` ponen púa, cualquier otra cosa la deja.
    #
    # Existe porque un polígono muestreado NO es lo mismo que la rejilla. El
    # isotipo dibujado como polígono y muestreado por el patrón sale con los
    # huecos comidos —miden menos que una púa— y el logo queda como una mancha
    # alta y pareja. Con la rejilla, lo que se escribe es exactamente lo que se
    # imprime, púa por púa, y no hay nada que interpretar.
    _rej = [f for f in patron.replace("\n", "/").split("/") if f.strip()]
    _rej_nf = len(_rej)
    _rej_nc = max((len(f) for f in _rej), default=0)
    # Cada anillo lleva su propio giro: en el croquis los dos isotipos están
    # ESPEJADOS —el de arriba con el triángulo grande arriba, el de abajo con
    # el grande abajo— y así la pareja se lee como una composición y no como el
    # mismo sello repetido.
    iso_anillos = []
    if iso_mm > 0:
        iso_anillos.append((iso_t, iso_giro))
        if iso_t2 > 0:
            iso_anillos.append((iso_t2, iso_giro2))

    def _media_anchura(dv: float) -> float:
        """Media anchura de la hoja a esa altura, 0 fuera."""
        if abs(dv) >= semi_l:
            return 0.0
        # `panza` corre el punto más ancho hacia abajo estirando la mitad de
        # arriba y encogiendo la de abajo, así que la punta de arriba queda más
        # larga que la de abajo: eso es lo que distingue una hoja de un ojo.
        v = dv / semi_l
        v = (v + panza) / (1.0 + panza) if v >= -panza else (v + panza) / (1.0 - panza)
        if abs(v) >= 1.0:
            return 0.0
        return semi_a * (1.0 - v * v) ** punta

    def _en_hoja(du: float, dv: float) -> float:
        """1 en la carne (hoja o tallo), 0 fuera, contorno desvanecido."""
        media = _media_anchura(dv)
        if tallo_mm > 0 and -semi_l - tallo_mm <= dv <= -semi_l + tallo_mm:
            # El tallo AFINA hacia abajo: grueso donde nace de la hoja y
            # delgado en la punta. Recto se lee como un palito pegado; el
            # afinado es lo que lo hace parecer parte de la hoja.
            #
            # Se toma el MÁXIMO contra la hoja, no un `else`. Con un `else`, en
            # la fila donde la hoja ya se cerró en punta pero `dv` todavía no
            # pasó su base, la anchura era la de la hoja —o sea cero— y quedaba
            # una FILA VACÍA entre la hoja y el tallo: el tallo salía suelto,
            # despegado. Con el máximo, el tallo entra por dentro de la punta de
            # la hoja y el nacimiento queda grueso, que es como se ve en una
            # hoja de verdad.
            u = (-semi_l - dv) / tallo_mm          # <0 dentro de la hoja, 1 en la punta
            if u <= 1.0:
                media = max(media, tallo_ancho_mm / 2
                            * (1.0 - (1.0 - tallo_afina) * max(0.0, u)))
        if media <= 0.0:
            return 0.0
        d = abs(du)
        if d <= media:
            return 1.0
        if borde_mm <= 0 or d >= media + borde_mm:
            return 0.0
        u = 1.0 - (d - media) / borde_mm
        return u * u * (3 - 2 * u)

    def _en_vena(du: float, dv: float) -> bool:
        """La nervadura central, más los dos brazos de la K si están pedidos."""
        # El tallo queda ENTERO: la nervadura es de la hoja. Dejándola correr
        # también por el tallo lo parte en dos hilos —el tallo mide dos puntos
        # de ancho y la vena se lleva el del medio— y deja de leerse como
        # tallo.
        if dv < -semi_l:
            return False
        if abs(du) <= vena_mm / 2:
            return True
        if not k or du <= 0:
            return False
        # Los brazos salen del centro hacia la DERECHA, como en el logo, uno
        # para arriba y otro para abajo. La distancia de un punto a la recta
        # dv = ±m·du es |dv ∓ m·du| / sqrt(1 + m^2).
        m = brazo * semi_l / semi_a
        norma = math.hypot(1.0, m)
        return (abs(dv - m * du) / norma <= vena_mm / 2
                or abs(dv + m * du) / norma <= vena_mm / 2)

    def mascara(angulo: float, t: float) -> float:
        if _rej_nf:
            # La fila se cuenta sobre la MISMA rejilla de bandas que usa la
            # cadencia, no sobre una altura libre. Cada `0` es una columna de
            # púas durante una banda entera; si las filas no caen sobre las
            # bandas, cada punto queda partido entre dos y el dibujo se borra.
            # Las bandas se cuentan desde el ARRANQUE DE LA PARED, que es
            # donde empieza la cadencia: `t=0`. Restarle el piso corría todo
            # media banda y las filas salían de a pares.
            banda = int(t * altura_mm / patron_fila_mm + 1e-9)
            j = (_rej_nf - 1) - (banda - patron_fila0)   # fila 0 = la de arriba
            if 0 <= j < _rej_nf:
                fila = _rej[j]
                # Sin `+ 0.5`: la celda `k` es la fase [k, k+1), que es
                # justo lo que ocupa la púa `k` —su pulso arranca en `k`—, y
                # su centro `k+0.5` es el punto de lectura de `peso_por_pua`.
                #
                # Con `+ 0.5` la celda iba de `k-0.5` a `k+0.5` y pasaban dos
                # cosas malas: la frontera de la rejilla caía en mitad del
                # pico (medido: 20 de 56 púas a z=10 leían dos celdas), y el
                # punto de lectura caía EXACTO sobre la frontera de redondeo,
                # así que el error de coma flotante decidía la columna púa por
                # púa (medido: el logo baja de 320/324 a 275/324 y las cuatro
                # copias dejan de coincidir entre sí).
                k = (int((angulo % TAU) / TAU * patron_puas
                         + (0.0 if patron_alineado else 0.5)) % patron_puas)
                # Las copias van en los HUECOS entre hojas: con el mismo
                # origen que las hojas, el dibujo cae encima de ellas.
                #
                # El centro se REDONDEA A PÚA ENTERA. Con 60 púas y 4 copias el
                # hueco cae en 7.5, o sea ENTRE dos púas, y entonces la 7 y la 8
                # daban las dos `round(±0.5) = 0`: las dos caían en la misma
                # columna del dibujo y cada punto salía de a dos púas.
                for r in range(max(1, patron_copias)):
                    kc = round((r + 0.5) * patron_puas / max(1, patron_copias))
                    i = (k - kc) + _rej_nc // 2 + patron_corrimiento
                    if 0 <= i < len(fila) and fila[i] in "0#":
                        return 1.0
        # El isotipo se consulta PRIMERO y manda: cae donde no hay hoja, así que
        # no compite con ella, y devolver 1 de una evita recorrer las hojas.
        for t_iso, g_iso in iso_anillos:
            dv_iso = (t - t_iso) * altura_mm
            if abs(dv_iso) > iso_mm / 2:
                continue
            for a_iso in _iso_huecos:
                if _en_isotipo(_envolver(angulo - a_iso) * radio_mm,
                               dv_iso, iso_mm / 2, g_iso, iso_separacion):
                    return 1.0
        mejor = 0.0
        for centro_a, centro_t in centros:
            du = _envolver(angulo - centro_a) * radio_mm
            dv = (t - centro_t) * altura_mm - subida
            carne = _en_hoja(du, dv)
            if carne <= 0.0:
                continue
            if _en_vena(du, dv):
                return 0.0      # la vena manda sobre la carne
            if degradado != 0.0:
                if dv < -semi_l and tallo_mm > 0:
                    # EL TALLO VA AL REVÉS QUE LA HOJA: alto en el medio y fino
                    # en los cantos, o sea redondeado como un tallo de verdad.
                    # Con la regla de la hoja —alta en el borde— el tallo salía
                    # como una canaleta, hundido justo en el eje, que es donde
                    # un tallo tiene que ser más grueso.
                    u = (-semi_l - dv) / tallo_mm
                    med = tallo_ancho_mm / 2 * (1.0 - (1.0 - tallo_afina)
                                                * max(0.0, min(1.0, u)))
                    e = 1.0 - min(1.0, abs(du) / max(med, 1e-9))
                else:
                    # Cuán CERCA DEL CONTORNO está el punto: 0 en el centro, 1
                    # en el borde. Se toma el máximo de las dos distancias
                    # normalizadas —la de costado contra la media anchura de esa
                    # altura, y la de alto contra el semilargo— porque la punta
                    # de la hoja también es borde. Sólo con la de costado, las
                    # puntas quedaban al nivel del centro y la hoja seguía
                    # leyéndose plana en el eje largo.
                    media = _media_anchura(dv)
                    lado = abs(du) / media if media > 1e-9 else 1.0
                    e = min(1.0, max(abs(dv) / semi_l, lado))
                    # Con `degradado` NEGATIVO la hoja va al revés: baja hacia
                    # el CONTORNO y sube hacia el eje, o sea abombada hacia
                    # afuera en vez de hacia adentro. Sólo se da vuelta acá: el
                    # tallo (la rama de arriba) ya nace alto en el medio, que es
                    # como es un tallo, y darlo vuelta lo volvería una canaleta.
                    if degradado < 0.0:
                        e = 1.0 - e
                d = abs(degradado)
                carne *= d + (1.0 - d) * max(0.0, e)
            mejor = max(mejor, carne)
            if mejor >= 1.0:
                return 1.0
        return mejor

    return mascara


def organico(
    cantidad: int = 9,
    semilla: int = 5,
    ancho_grados: float = 85.0,
    alto_t: float = 0.20,
    rugosidad: float = 0.55,
    armonicos: int = 4,
    borde: float = 0.0,
) -> Mascara:
    """
    Manchas orgánicas que se pisan entre sí, tipo camuflaje.

    Es la máscara de la lámpara de líneas: formas grandes, de borde irregular,
    que se solapan hasta formar continentes en vez de leerse como una fila de
    lunares. `parches` no sirve para eso — sus manchas son elipses y la elipse
    se delata en cuanto hay más de dos.

    Cada mancha es una elipse cuyo RADIO depende del ángulo polar local:

        r(phi) = 1 + rugosidad * sum_j  c_j * cos(j*phi + fase_j)

    con `c_j` proporcional a 1/j y normalizados para que la suma de los módulos
    valga 1. O sea que `rugosidad` es literalmente cuánto se aparta del óvalo,
    en fracción de su propio radio: 0 son elipses, 0.55 son manchas, 1.0 son
    estrellas de mar. Los armónicos bajos dan los lóbulos grandes y los altos
    el picoteo del borde; por eso pesan 1/j y no todos igual.

    El borde sale DURO a propósito (`borde=0`). En la lámpara de líneas la
    máscara se cuantiza a la rejilla de líneas antes de usarse, así que el
    contorno queda escalonado línea por línea —el dentado que se ve en las
    fotos— y suavizarlo acá no lo suaviza: sólo mete líneas a media altura.

    Args:
        cantidad: cuántas manchas. Pocas y grandes se pisan y forman
            continentes; muchas y chicas quedan como un estampado.
        semilla: cambiala para otra distribución. Misma semilla, misma pieza.
        ancho_grados: cuánto arco ocupa una mancha de escala 1.
        alto_t: qué fracción de la altura ocupa una mancha de escala 1.
        rugosidad: cuánto se aparta del óvalo (0 = elipse, 1 = estrella).
        armonicos: cuántos lóbulos distintos tiene el borde. 2 son manchas
            arriñonadas, 5-6 son manchas de vaca.
        borde: fracción del radio que es transición suave. 0 = borde duro.

    Returns:
        Una `Mascara`.
    """
    from .estructura import _fases

    r = _fases(semilla, cantidad * (3 + 2 * max(1, armonicos)))
    manchas = []
    for _ in range(cantidad):
        centro_a = next(r) * TAU
        # Se dejan salir por arriba y por abajo: una mancha cortada por el
        # borde de la pieza se lee como que el patrón sigue, y es lo que hacen
        # las de la referencia. Acotarlas al centro deja un marco liso que
        # delata que el dibujo es un estampado y no una piel.
        centro_t = -0.15 + next(r) * 1.30
        escala = 0.65 + next(r) * 0.80
        arm = []
        for j in range(1, max(1, armonicos) + 1):
            arm.append((j, next(r) * 2 - 1, next(r) * TAU))
        peso = sum(abs(c) / j for j, c, _ in arm) or 1.0
        arm = [(j, c / j / peso, f) for j, c, f in arm]
        manchas.append((centro_a, centro_t, escala, arm))

    sigma_a = math.radians(ancho_grados) / 2
    sigma_t = alto_t / 2

    def mascara(angulo: float, t: float) -> float:
        mejor = 0.0
        for centro_a, centro_t, escala, arm in manchas:
            u = _envolver(angulo - centro_a) / (sigma_a * escala)
            v = (t - centro_t) / (sigma_t * escala)
            d = math.hypot(u, v)
            if d > 1 + rugosidad:
                continue
            phi = math.atan2(v, u)
            radio = 1.0 + rugosidad * sum(c * math.cos(j * phi + f) for j, c, f in arm)
            if radio <= 0:
                continue
            if d <= radio * (1 - borde):
                return 1.0
            if d < radio:
                mejor = max(mejor, (radio - d) / max(radio * borde, 1e-9))
        return mejor

    return mascara


def unir(*mascaras: Mascara) -> Mascara:
    """Une varias máscaras: el dibujo es la suma de todas."""
    return lambda angulo, t: max(m(angulo, t) for m in mascaras)


def invertir(mascara: Mascara) -> Mascara:
    """Intercambia dibujo y fondo."""
    return lambda angulo, t: 1.0 - mascara(angulo, t)


MASCARAS = {
    "caritas": caritas,
    "flores": flores,
    "parches": parches,
    "organico": organico,
    "hoja": hoja,
    "sectores": sectores,
    # `partial` y no un lambda con `**kw`: así la entrada conserva la firma de
    # `carita` y `acepta` puede leerla. Ver la nota en `caritas`.
    "feliz": functools.partial(carita, feliz=True),
    "triste": functools.partial(carita, feliz=False),
    "ninguna": lambda **kw: constante(1.0),
}

# Claves que inyecta el PATRÓN, no el usuario: el tamaño real de la pieza, que
# `flores` necesita para trabajar en milímetros y las demás máscaras ni miran.
# Se descartan en silencio si la máscara no las pide — a diferencia de un
# `--p` mal escrito, que tiene que seguir reventando.
GEOMETRIA = ("radio_mm", "altura_mm")


def _firma(nombre):
    """Los parámetros que declara la fábrica de esa máscara, o None si no la hay."""
    if callable(nombre) or nombre not in MASCARAS:
        return None
    return inspect.signature(MASCARAS[nombre]).parameters


def acepta(nombre, kwargs: dict) -> dict:
    """
    De `kwargs`, los que esa máscara sabe recibir. El resto se DESCARTA.

    Es para quien tiene un bolso FIJO de parámetros y no sabe a qué máscara va
    a parar: el CLI, que declara `--cantidad` y `--centro-t` con valor por
    defecto y por lo tanto los manda siempre, o un patrón como `peine`, que
    ofrece la misma lista de perillas para todas las máscaras. Ahí un parámetro
    de más no es un error de uso —es el sobrante de otra máscara— así que se
    tira callado.

    NO es lo que hay que usar con parámetros que tipeó una persona: para eso
    está `resolver`, que los deja reventar. Ver la nota de `GEOMETRIA`.
    """
    firma = _firma(nombre)
    if firma is None:
        return {}
    # Un `**kwargs` en la firma NO cuenta como "acepta cualquier cosa": las
    # máscaras que lo tienen reenvían a otra más angosta, así que darle el
    # bolso entero revienta adentro. Sólo los parámetros con nombre.
    return {k: v for k, v in kwargs.items() if k in firma}


def resolver(nombre, **kwargs) -> Mascara:
    """
    Convierte el nombre que llega por `--p mascara=...` en una `Mascara`.

    A diferencia de `acepta`, acá lo que sobra NO se descarta: los `--p` los
    tipeó alguien y un nombre mal escrito tiene que reventar en vez de que la
    máscara salga con el valor por defecto y el dibujo no se parezca a lo
    pedido. La única excepción son las claves de `GEOMETRIA`, que las inyecta
    el patrón y no el usuario.

    Si ya viene una máscara (uso como librería) la deja pasar tal cual.
    """
    if callable(nombre):
        return nombre
    if nombre not in MASCARAS:
        raise ValueError(
            f"máscara desconocida: {nombre!r}. Opciones: {', '.join(sorted(MASCARAS))}"
        )
    firma = _firma(nombre)
    kwargs = {k: v for k, v in kwargs.items()
              if k not in GEOMETRIA or k in firma}
    return MASCARAS[nombre](**kwargs)


def rasterizar(mascara: Mascara, ancho: int = 100, alto: int = 30,
               relleno: str = "#", vacio: str = "·") -> str:
    """
    Dibuja la máscara en ASCII: el ángulo en horizontal, la altura en vertical.

    Es el desenrollado de la superficie, o sea la pieza abierta y aplanada. La
    fila de arriba es el borde (t=1) y la de abajo la base (t=0).

    Sirve para ajustar una cara en milisegundos en vez de generar un gcode de
    35 000 líneas para descubrir que la boca quedó fuera del recuadro.
    """
    filas: List[str] = []
    for f in range(alto):
        t = 1.0 - f / (alto - 1)
        fila = "".join(
            relleno if mascara(c / ancho * TAU, t) > 0.5 else vacio
            for c in range(ancho)
        )
        filas.append(fila)
    return "\n".join(filas)


def _cli() -> None:
    """
    Ver una máscara en la terminal:

        python -m lamparas.superficie caritas
        python -m lamparas.superficie feliz --ancho-grados 100 --alto-t 0.7
        python -m lamparas.superficie flores --p cantidad=9 --p petalos=6
        python -m lamparas.superficie flores --p radio_mm=34 --p altura_mm=200

    Iterar acá cuesta milisegundos; iterar generando gcode cuesta minutos.
    """
    import argparse

    def _kv(texto: str):
        if "=" not in texto:
            raise argparse.ArgumentTypeError(f"se esperaba clave=valor, llegó {texto!r}")
        clave, valor = texto.split("=", 1)
        for conversor in (int, float):
            try:
                return clave.strip(), conversor(valor)
            except ValueError:
                continue
        return clave.strip(), valor

    p = argparse.ArgumentParser(prog="lamparas.superficie", description=_cli.__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mascara", nargs="?", default="caritas", choices=sorted(MASCARAS))
    p.add_argument("--ancho-grados", type=float, default=140.0)
    p.add_argument("--centro-t", type=float, default=0.5)
    p.add_argument("--alto-t", type=float, default=0.55)
    p.add_argument("--p", dest="parametros", action="append", type=_kv, default=[],
                   metavar="CLAVE=VALOR",
                   help="parámetro de la máscara, repetible. Son los mismos que "
                        "acepta su función acá abajo: para 'flores', cantidad, "
                        "petalos, tamano, corazon, borde_mm, semilla, radio_mm, altura_mm.")
    p.add_argument("--cantidad", type=int, default=7, help="manchas (solo 'organico'/'parches')")
    p.add_argument("--semilla", type=int, default=3, help="semilla de las manchas")
    p.add_argument("--rugosidad", type=float, default=0.55,
                   help="cuanto se aparta del ovalo cada mancha (solo 'organico')")
    p.add_argument("--cols", type=int, default=96, help="ancho del dibujo en caracteres")
    p.add_argument("--filas", type=int, default=32, help="alto del dibujo en caracteres")
    p.add_argument("--centrar", action="store_true",
                   help="rotar media vuelta, para que un dibujo que cae en 0° no quede "
                        "partido entre los dos bordes del desenrollado")
    args = p.parse_args()

    # Los flags con nombre tienen valor por defecto, así que llegan SIEMPRE
    # aunque nadie los escriba: pasárselos a una máscara que no los acepta la
    # haría reventar por algo que el usuario no pidió, y por eso van por
    # `acepta`, que tira lo que sobra. Los de `--p`, en cambio, los tipeó
    # alguien: esos van tal cual y si están mal, que reviente.
    fijos = {"ancho_grados": args.ancho_grados, "centro_t": args.centro_t,
             "alto_t": args.alto_t, "cantidad": args.cantidad,
             "semilla": args.semilla, "rugosidad": args.rugosidad}
    kwargs = acepta(args.mascara, fijos)
    kwargs.update(dict(args.parametros))

    m = resolver(args.mascara, **kwargs)
    if args.centrar:
        base = m
        m = lambda a, t: base((a + math.pi) % TAU, t)  # noqa: E731
    print(f"máscara '{args.mascara}' — la pieza desenrollada, 0°..360° de izquierda a derecha")
    print(rasterizar(m, ancho=args.cols, alto=args.filas))


if __name__ == "__main__":
    _cli()
