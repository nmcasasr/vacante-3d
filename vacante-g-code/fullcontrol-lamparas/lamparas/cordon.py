"""
Qué le hace el CORDÓN a un relieve angular.

Un patrón que ondula el radio dentro de la vuelta —el peine de
`bowls/peine.py`, los dientes de `bowls/zigzag.py`— está en el g-code con la
amplitud que uno pidió. Lo que queda en la pieza es otra cosa: la boquilla no
deposita una línea sin espesor sino una cinta de `perfil.ancho` de ancho, y esa
cinta no entra en un valle más angosto que ella.

En modo vaso cada capa es UNA sola pasada, así que no hay una pasada vecina que
rellene el valle: lo único que lo rellena es el propio cordón de la pasada. La
superficie exterior de la pieza es entonces el borde de la unión de los discos
de radio `ancho/2` apoyados a lo largo del recorrido. Sobre un rayo que sale
del eje con ángulo `theta`, ese borde está en

    env(theta) = max_p [ r_p cos(d) + sqrt((w/2)^2 - (r_p sin(d))^2) ],  d = theta - theta_p

y sólo cuentan los puntos que el rayo llega a tocar (`r_p |sin d| < w/2`). Es la
intersección más lejana del rayo con cada disco: el contorno exacto de la unión,
no una aproximación.

## Lo que dice el modelo, medido

La intuición era "el paso de la línea tiene que medir dos cordones". Es falsa
en las dos direcciones, y el modelo lo muestra en una tabla. Con cordón de
0.8 mm, radio 32 y 0.55 mm de amplitud pico a valle:

    líneas  diente  paso mm  valle mm   sobrevive
       160    0.55     1.26      0.57       100 %
       200    0.55     1.01      0.45        49 %
       200    0.35     1.01      0.65       100 %
       250    0.35     0.80      0.52        36 %
       125    0.75     1.61      0.40        96 %

O sea que no lo decide el paso solo ni el valle solo: un peine de paso 1.26 mm
—1.6 cordones, muy por debajo de la regla de los dos— sale entero, y uno de
paso 0.80 mm con MÁS valle sale borrado. Las dos cosas que tienen que pasar son
que el disco llegue al fondo del valle y que llegue a la punta del diente, y
eso depende del paso y de `ancho_diente` a la vez.

Por eso acá no hay ninguna regla: hay una función que calcula el número. Vale
milisegundos correrla antes de generar, contra los minutos que cuesta generar
un g-code para descubrir que la pieza sale lisa.
"""

import math
from typing import Callable, Tuple

import numpy as np


def envolvente(r, th, ancho: float, rayos):
    """
    El contorno exterior que deja un cordón de `ancho` recorriendo `(r, th)`.

    `r` y `th` son el recorrido en polares, con `th` creciente (desenrollado), y
    `rayos` los ángulos ABSOLUTOS donde se quiere el contorno, en las mismas
    coordenadas que `th`. Absolutos y no relativos a `th[0]` a propósito: quien
    compara dos vueltas necesita que las dos caigan en los mismos ángulos, y
    anclar cada una a su primer punto las corre entre sí hasta un paso de
    muestreo — que en un peine de seis muestras por diente es media línea.

    **Los puntos tienen que estar juntos**, y si no lo están esto LEVANTA en vez
    de devolver un número. El modelo apoya un disco en cada punto: si entre dos
    puntos hay más de un diámetro, entre disco y disco queda un hueco que
    ningún rayo toca. Esos rayos daban `-inf`, el `-inf` se colaba en el pico a
    valle y la envolvente salía MÁS grande que el recorrido —el cordón
    ahondando el relieve, que es imposible— o directamente infinita. Un modelo
    mordido tiene que gritar, no devolver 1.10 con cara de dato. Con los puntos
    del g-code crudo (uno cada 0.3 mm) hay que densificar antes; ver
    `verificar_lineas._densificar`.
    """
    w = ancho / 2.0
    rayos = np.asarray(rayos, dtype=float)
    paso = float(np.median(np.diff(th))) or 1e-6
    radio_medio = float(np.median(r))
    # Cuántos puntos del recorrido caben en el arco que el disco alcanza, con
    # margen: el paso angular del recorrido no es exactamente constante.
    k = int(math.ceil(w / max(radio_medio * paso, 1e-9))) + 2
    centros = np.searchsorted(th, rayos)
    idx = np.clip(centros[:, None] + np.arange(-k, k + 1)[None, :], 0, len(r) - 1)
    rp = r[idx]
    d = rayos[:, None] - th[idx]
    perp = rp * np.sin(d)
    lejano = rp * np.cos(d) + np.sqrt(np.maximum(w * w - perp * perp, 0.0))
    env = np.max(np.where(np.abs(perp) < w, lejano, -np.inf), axis=1)
    sueltos = int(np.count_nonzero(~np.isfinite(env)))
    if sueltos:
        separacion = radio_medio * paso
        raise ValueError(
            f"el cordón de {ancho:g} mm no cubre {sueltos} de {len(env)} rayos: los puntos "
            f"del recorrido están a {separacion:.3f} mm y los discos miden {ancho:g} de "
            f"diámetro, así que entre uno y otro queda un hueco. Densificá el recorrido a "
            f"menos de {ancho / 4:.3f} mm entre puntos antes de medir.")
    return env


def pico_a_valle(perfil, n: int) -> float:
    """
    Mediana del pico a valle DENTRO de cada línea, no el rango del anillo.

    El rango del anillo entero mezcla el relieve del peine con la diferencia
    entre las líneas de fondo y las del dibujo: una pieza con el peine borrado
    pero las manchas marcadas daría un número alto igual. Por línea, no.
    """
    perfil = np.asarray(perfil)
    if n <= 0:
        return float(perfil.max() - perfil.min())
    m = len(perfil) // n * n
    if m == 0:
        return 0.0
    trozos = perfil[:m].reshape(n, -1)
    return float(np.median(trozos.max(axis=1) - trozos.min(axis=1)))


def sobrevive(diente: Callable[[float], float], radio: float, ancho: float,
              n: int, amplitud: float = 1.0, muestras: int = 24) -> Tuple[float, float]:
    """
    Qué fracción del relieve de un peine ideal queda en la superficie.

    `diente(fase) -> 0..1` es el perfil de UNA línea, con `fase` de 0 a 1. Se
    repite `n` veces alrededor de un círculo de `radio` y se le pasa el cordón
    por encima.

    Returns:
        (relieve del recorrido, relieve de la superficie), en mm.
    """
    # El paso entre puntos tiene que ser bastante menor que el cordón o la
    # unión de discos queda con huecos y `envolvente` levanta. Un cuarto del
    # ancho da tres discos pisándose en cada punto.
    m = max(2000, n * muestras, int(math.ceil(2 * math.pi * radio / max(ancho / 4, 1e-6))))
    th = np.linspace(0, 2 * math.pi, m, endpoint=False)
    x = th * n / (2 * math.pi)
    fase = x - np.floor(x)
    r = radio + amplitud * np.array([diente(f) for f in fase])
    rayos = th[0] + np.linspace(0, 2 * math.pi, n * 16, endpoint=False)
    return (pico_a_valle(np.interp(rayos, th, r), n),
            pico_a_valle(envolvente(r, th, ancho, rayos), n))


def lineas_que_entran(diente: Callable[[float], float], radio: float, ancho: float,
                      amplitud: float, minimo: float = 0.85,
                      tope: int = 600) -> int:
    """
    La mayor cantidad de líneas cuyo relieve todavía sobrevive al cordón.

    `minimo` es qué fracción del relieve tiene que quedar. Se busca por
    bisección **suponiendo que sobrevivir baja con la cantidad de líneas**, que
    es lo que muestra la tabla del encabezado: más líneas es menos paso y menos
    valle, y las dos empujan para el mismo lado. La suposición se comprueba en
    `test_cordon.py`, que barre el rango entero y verifica que no haya un
    repunte — si algún día un perfil de diente raro lo rompe, ahí salta.
    """
    def pasa(n: int) -> bool:
        a, b = sobrevive(diente, radio, ancho, n, amplitud)
        return a > 1e-9 and b / a >= minimo

    lo, hi = 8, max(9, int(tope))
    if not pasa(lo):
        return lo
    if pasa(hi):
        return hi
    while hi - lo > 1:
        medio = (lo + hi) // 2
        if pasa(medio):
            lo = medio
        else:
            hi = medio
    return lo
