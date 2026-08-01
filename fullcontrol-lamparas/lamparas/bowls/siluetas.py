"""
Siluetas de bowl: el radio medio en función de la altura relativa `t` (0..1).

El patrón (trenzado, malla, celosía) se suma *encima* de la silueta, así que
las dos cosas se combinan libremente: cualquier patrón sobre cualquier silueta.

El límite práctico no es estético sino de voladizo: en modo vaso cada vuelta se
apoya sobre la de abajo, y si el radio crece más rápido que el ancho de línea
por capa la pared se descuelga. `generar_pieza()` avisa por consola cuando se
pasa de 45°.
"""

import math
from typing import Callable

# Una silueta ya parametrizada: t (0..1) -> radio medio en mm
Silueta = Callable[[float], float]


def bol(radio_base: float = 35.0, radio_boca: float = 75.0) -> Silueta:
    """
    Bowl clásico: arranca vertical, se abre en el medio y vuelve a enderezarse
    en la boca. La curva es un smoothstep, que reparte la apertura y evita el
    voladizo brusco que daría un cono recto.
    """

    def silueta(t: float) -> float:
        s = t * t * (3 - 2 * t)
        return radio_base + (radio_boca - radio_base) * s

    return silueta


def copa(radio_base: float = 30.0, radio_boca: float = 70.0) -> Silueta:
    """Cónica pura: la apertura es constante en toda la altura."""

    def silueta(t: float) -> float:
        return radio_base + (radio_boca - radio_base) * t

    return silueta


def platillo(radio_base: float = 30.0, radio_max: float = 80.0, radio_boca: float = 45.0) -> Silueta:
    """
    Silueta tipo platillo: se abre hasta `radio_max` a media altura y vuelve a
    cerrar hacia la boca. Es la forma de la lámpara "platillo volante" de las
    referencias. La parte de arriba es reentrante, así que conviene revisar el
    aviso de voladizo antes de mandarla a imprimir.
    """

    def silueta(t: float) -> float:
        lineal = radio_base + (radio_boca - radio_base) * t
        panza = radio_max - max(radio_base, radio_boca)
        return lineal + panza * math.sin(math.pi * t)

    return silueta


def campana(radio_base: float = 28.0, radio_boca: float = 78.0) -> Silueta:
    """Campana: casi vertical abajo y apertura marcada arriba (cuarto de coseno)."""

    def silueta(t: float) -> float:
        return radio_base + (radio_boca - radio_base) * (1 - math.cos(t * math.pi / 2))

    return silueta


SILUETAS = {
    "bol": bol,
    "copa": copa,
    "platillo": platillo,
    "campana": campana,
}
