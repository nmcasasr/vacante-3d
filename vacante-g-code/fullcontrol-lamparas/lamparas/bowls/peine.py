"""
Peine: la pared entera rayada con líneas verticales finas, y el dibujo hecho
con las líneas que SOBRESALEN más que las demás.

Es la técnica de la lámpara de referencia, y es la misma familia que
`zigzag.py` —una máscara decide qué pasa en cada punto de la superficie— pero
con una diferencia que cambia todo lo que se ve:

- `zigzag` **prende y apaga** la textura: donde la máscara vale 1 la pared
  zigzaguea, donde vale 0 va lisa. El dibujo es textura contra liso.
- `peine` tiene textura **en toda la pieza** y lo que cambia es CUÁNTO sale
  cada línea. Hay dos alturas de diente —`amplitud_fondo` y `amplitud`— y la
  máscara elige cuál le toca a cada línea. El dibujo es relieve contra relieve.

Que el fondo también esté rayado es lo que hace que la pieza se lea como una
piel y no como un sello estampado: sin líneas de fondo, el dibujo queda
flotando sobre una pared lisa y se ve el recuadro.

## Por qué las líneas son verticales y no una hélice

`funcion_radio` recibe el ángulo ACUMULADO de toda la espiral. Si el número de
dientes por vuelta es ENTERO, `angulo` y `angulo + 2pi` caen en la misma fase
del diente, así que el bulto de una vuelta queda exactamente encima del de la
vuelta anterior y las vueltas se apilan en una columna. Con un número no entero
—lo que hace la malla, con `n + 0.5`— la columna se corre un poco por vuelta y
sale una hélice. Acá se redondea a entero a propósito.

## Cuántas líneas entran, y por qué no lo decide una regla

El recorrido ondula, pero lo que queda impreso es el cordón. En modo vaso cada
capa es UNA pasada, así que no hay una pasada vecina que rellene el valle entre
dos dientes: lo rellena el propio cordón, y si el valle es más angosto que él,
el g-code tiene un peine y la pieza sale con una ondulación apenas insinuada.

La regla que parecía obvia —"el paso de la línea tiene que medir dos
cordones"— es falsa en las dos direcciones, y está medida en el encabezado de
`lamparas/cordon.py`: un peine de paso 1.26 mm (1.6 cordones) sale entero y uno
de paso 0.80 mm con MÁS valle sale borrado. No lo decide el paso solo: el disco
del cordón tiene que llegar al fondo del valle Y a la punta del diente, y eso
depende del paso y de `ancho_diente` a la vez.

Así que acá no hay regla: `lineas=0` —el valor por defecto— no es "sin líneas",
es **elegilas vos**, y `cordon.lineas_que_entran()` busca la mayor cantidad
cuyo relieve todavía sobrevive, corriendo el modelo del cordón sobre este
diente, este radio y esta boquilla. Cuesta milisegundos; generar el g-code para
descubrir que la pieza sale lisa cuesta minutos. Poner `lineas` a mano está
bien —es la perilla estética— y si la cuenta dice que a esa cantidad el cordón
se come el peine, `construir()` lo avisa antes de generar nada.

Después de imprimir el archivo hay que medirlo, que no es lo mismo que
predecirlo: `python3 verificar_lineas.py output/peine.gcode` corre el mismo
modelo sobre el g-code REAL, con la rejilla de muestreo y la máscara ya
aplicadas. Si los dos números no coinciden, lo que se emitió no es lo que el
patrón cree que emitió.

## Cómo sube y baja una línea (y por qué no salta de golpe)

La máscara se evalúa **en el centro de cada línea y una sola vez por vuelta**,
no punto por punto. O sea que la decisión se cuantiza a la rejilla del peine:
una línea sale entera o no sale, nunca a medias. Eso es lo que da el borde
escalonado, línea por línea, que se ve en las fotos — y de paso evita el
diente a media altura, que no se lee ni como fondo ni como dibujo.

En vertical no se puede hacer lo mismo. Si una línea pasara de `amplitud_fondo`
a `amplitud` entre una vuelta y la siguiente, el radio saltaría la diferencia
entera de golpe, y la regla que gobierna todas las piezas de este proyecto es

    Δ radio por vuelta < ancho de cordón

Así que el peso de cada línea se promedia en una ventana de `rampa` vueltas: el
salto por vuelta queda en `(amplitud - amplitud_fondo) / rampa` y la línea nace
en punta en vez de arrancar de un escalón. Con los valores por defecto son
0.14 mm por vuelta contra un cordón de 0.8: 83 % de solape.
"""

import math
from typing import Optional, Tuple

from ..cordon import lineas_que_entran, sobrevive
from ..superficie import Mascara, acepta, resolver
from .siluetas import Silueta

TAU = 2 * math.pi

# La pared es VERTICAL y todo el relieve es angular: la marcha adaptativa mide
# mal ese caso —trata el corrimiento radial como si fuera vertical— y devuelve
# una altura de capa que se bandea sin corresponder a ningún rasgo de la pieza.
# `bowls.pasos_bowl` lee esta constante. El razonamiento largo está en el
# bloque `paso_fijo` de `comun.generar_pieza`.
PASO_FIJO = True

# Qué fracción del relieve tiene que sobrevivir al cordón. El automático de
# `lineas` busca la mayor cantidad que todavía llega a `RELIEVE_BUSCADO`; por
# debajo de `RELIEVE_MINIMO` se avisa, porque ahí la pieza sale con una
# ondulación insinuada en vez de un peine. Los dos salen de la tabla del
# encabezado de `lamparas/cordon.py`: el salto es abrupto —de 100 % a 49 %
# entre 160 y 200 líneas— así que cualquier corte entre medio da la misma
# cantidad de líneas.
RELIEVE_BUSCADO = 0.85
RELIEVE_MINIMO = 0.60


def _bulto(fase: float, ancho: float, meseta: float) -> float:
    """
    El perfil de un diente: 0 en el valle, 1 en la cresta.

    `fase` va de 0 a 1 dentro del paso de la línea y el diente está centrado en
    0.5. `ancho` es qué fracción del paso ocupa; el resto es valle plano, que
    es lo que separa una línea de la otra.

    La cresta es PLANA (`meseta`) y no un pico, y no es una decisión estética:
    el generador muestrea la vuelta en una rejilla pareja que no tiene por qué
    caer justo en el centro del diente —arranca en el ángulo donde terminó la
    espiral del piso, que es cualquier cosa—. Con un pico, la altura de cada
    línea dependería de dónde cayó la muestra más cercana; con una meseta más
    ancha que el paso de muestreo, siempre hay al menos una muestra en la
    cresta y todas las líneas salen iguales. `construir()` fuerza esa relación
    al elegir `muestras_diente`.
    """
    d = abs(fase - 0.5) / max(ancho / 2, 1e-9)
    if d >= 1.0:
        return 0.0
    if d <= meseta:
        return 1.0
    u = (d - meseta) / max(1.0 - meseta, 1e-9)
    return 0.5 * (1 + math.cos(math.pi * u))


def construir(
    silueta: Silueta,
    altura: float,
    mascara="organico",
    lineas: int = 0,
    amplitud: float = 0.90,
    amplitud_fondo: float = 0.35,
    ancho_diente: float = 0.55,
    meseta: float = 0.45,
    rampa: int = 4,
    invertir: int = 0,
    muestras_diente: int = 0,
    cantidad: int = 9,
    semilla: int = 5,
    ancho_grados: float = 85.0,
    alto_t: float = 0.20,
    rugosidad: float = 0.55,
    centro_t: float = 0.5,
    ancho_cordon: float = 0.8,
    altura_capa: float = 0.4,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura de la pared en mm. Se usa: de acá sale cuántas vueltas
            tiene la pieza, y con eso el largo de la rampa vertical.
        mascara: nombre de `superficie.MASCARAS` o una `Mascara` ya armada.
            'organico' son las manchas de la referencia; 'ninguna' deja todas
            las líneas a `amplitud` y sirve para ver el peine solo.
        lineas: cuántas líneas verticales hay alrededor. **0 = automático**: la
            mayor cantidad cuyo relieve todavía sobrevive al cordón, calculada
            con el modelo de `lamparas/cordon.py` sobre este diente, este radio
            y esta boquilla. Ponerla a mano está bien —es la perilla estética—;
            si el cordón se la come, sale un aviso antes de generar.
        amplitud: cuánto sale una línea DEL DIBUJO, en mm.
        amplitud_fondo: cuánto sale una línea del FONDO, en mm. No es 0 a
            propósito: el fondo rayado es lo que hace que el dibujo se lea como
            relieve sobre una piel y no como un sello sobre una pared lisa.
            Con 0 el patrón se parece al de `zigzag.py`.
        ancho_diente: qué fracción del paso ocupa el diente; el resto es valle.
            0.55 deja diente y valle casi iguales. Subirlo pega las líneas
            entre sí, bajarlo las adelgaza hasta que el cordón no las llena.
        meseta: qué fracción del diente es cresta plana. Ver `_bulto`.
        rampa: en cuántas vueltas una línea pasa de `amplitud_fondo` a
            `amplitud`. Es lo que reparte el salto radial: el radio se corre
            `(amplitud - amplitud_fondo) / rampa` por vuelta, y eso tiene que
            quedar cómodamente por debajo del ancho de cordón. Bajarlo a 1 hace
            el borde de la mancha más filoso y el salto entero de una vez.
        invertir: 1 intercambia dibujo y fondo — las manchas quedan lisas y el
            relieve va alrededor. Es la otra lectura de la misma máscara.
        muestras_diente: puntos por línea. 0 = el mínimo que garantiza una
            muestra en la meseta (ver `_bulto`), que es lo que hace que todas
            las líneas salgan de la misma altura.
        cantidad, semilla, ancho_grados, alto_t, rugosidad, centro_t: van a la
            máscara; cada máscara toma los que entiende. Ver
            `superficie.organico()`.
        ancho_cordon, altura_capa: los pone `bowls.pasos_bowl` desde el perfil
            de impresión. No se piden por `--p`: la boquilla no es un parámetro
            del dibujo, pero el dibujo no se puede calcular sin ella.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `funcion_dz` y `paso_z` son None: el peine no toca la Z. La pared queda
    estanca y cada vuelta apoya entera sobre la anterior, así que sirve igual
    para una lámpara que para un florero con agua.
    """
    fn: Mascara = mascara if callable(mascara) else resolver(
        mascara, **acepta(mascara, dict(
            cantidad=cantidad, semilla=semilla, ancho_grados=ancho_grados,
            alto_t=alto_t, rugosidad=rugosidad, centro_t=centro_t)))

    # El radio con el que se calcula el paso es el MEDIO de la pieza, no el de
    # la base ni el de la boca: la cantidad de líneas es una sola para toda la
    # altura —si no, no serían verticales— así que el paso es cómodo en el
    # medio y se aprieta donde la silueta se angosta. Con un cilindro da igual.
    r_medio = sum(silueta(k / 20) for k in range(21)) / 21
    circunferencia = TAU * max(r_medio, 1e-6)
    perfil_diente = lambda f: _bulto(f, ancho_diente, meseta)  # noqa: E731

    n = int(lineas) or lineas_que_entran(
        perfil_diente, r_medio, ancho_cordon, amplitud_fondo, RELIEVE_BUSCADO)
    n = max(4, n)
    paso_linea = circunferencia / n

    # El relieve se mide sobre `amplitud_fondo` y no sobre `amplitud`: el fondo
    # es el diente MÁS BAJO, o sea el primero que el cordón borra. Si el fondo
    # sobrevive, el dibujo sobrevive de sobra.
    crudo, impreso = sobrevive(perfil_diente, r_medio, ancho_cordon, n, amplitud_fondo)
    queda = impreso / crudo if crudo > 1e-9 else 0.0
    print(f"Peine: {n} lineas, paso {paso_linea:.2f} mm "
          f"({paso_linea / ancho_cordon:.1f} cordones de {ancho_cordon:g} mm) "
          f"a radio medio {r_medio:.1f}. Del relieve de fondo sobrevive el "
          f"{100 * queda:.0f} % al cordon.")
    if queda < RELIEVE_MINIMO:
        entran = lineas_que_entran(perfil_diente, r_medio, ancho_cordon,
                                   amplitud_fondo, RELIEVE_BUSCADO)
        print(f"AVISO: el cordon se come el {100 * (1 - queda):.0f} % del peine. Con esta "
              f"boquilla entran {entran} lineas, no {n}. Subir la amplitud NO lo arregla: "
              f"lo que falta es valle, no altura — bajá 'lineas', bajá 'ancho_diente' "
              f"o poné una boquilla mas fina.")

    # Una muestra en la meseta, como mínimo: la meseta mide `meseta * ancho`
    # del paso y las muestras van cada `1/m`. Ver `_bulto`.
    m = max(int(muestras_diente) or 0, math.ceil(1.0 / max(meseta * ancho_diente, 1e-9)), 6)

    # --- el peso de cada línea, cuantizado a la rejilla y suavizado en altura ---
    dt_capa = altura_capa / max(altura, 1e-9)
    n_capas = max(1, round(1.0 / dt_capa))
    ventana = max(1, int(rampa))
    salto = abs(amplitud - amplitud_fondo) / ventana
    print(f"  rampa de {ventana} vueltas -> {salto:.3f} mm de radio por vuelta, "
          f"{100 * max(0.0, ancho_cordon - salto) / ancho_cordon:.0f}% de solape "
          f"sobre el cordon. {n_capas} vueltas, {n * m} puntos por vuelta.")

    cache: dict = {}

    def peso(indice: int, capa: int) -> float:
        clave = (indice % n, capa)
        v = cache.get(clave)
        if v is None:
            # El centro de la línea, no el punto donde está la boquilla: es lo
            # que hace que la línea entera comparta una sola decisión.
            ang = (indice + 0.5) * TAU / n
            t0 = capa * dt_capa
            # Promedio en una ventana vertical de `ventana` vueltas. Un
            # promedio de caja y no un suavizado más fino a propósito: lo que
            # importa es el TECHO del salto por vuelta, y en una caja de N
            # muestras ese techo es exactamente 1/N.
            v = sum(fn(ang, t0 + (k - (ventana - 1) / 2) * dt_capa)
                    for k in range(ventana)) / ventana
            v = min(1.0, max(0.0, v))
            if invertir:
                v = 1.0 - v
            cache[clave] = v
        return v

    def radio(angulo: float, t: float) -> float:
        base = silueta(t)
        # `angulo` viene acumulado a lo largo de toda la espiral. Con `n`
        # entero, sumarle una vuelta suma `n` al índice y no mueve la fase: por
        # eso las líneas salen verticales y no en hélice.
        x = angulo * n / TAU
        indice = math.floor(x)
        amp = amplitud_fondo + (amplitud - amplitud_fondo) * peso(indice, int(t / dt_capa + 0.5))
        if amp == 0.0:
            return base
        return base + amp * _bulto(x - indice, ancho_diente, meseta)

    return radio, None, n * m, None
