"""
Bowl con trenzado de cestería: tejas horizontales alternadas.

Cómo se arma: el radio ondula con `n_tiras` lóbulos alrededor de la vuelta,
pero la fase se invierte media vuelta de lóbulo entre una banda de capas y la
siguiente. Cada banda tiene además una envolvente seno, así la teja nace y
muere dentro de su banda en vez de cortarse de golpe. El resultado es el
aparejo de ladrillos entrelazados de la lámpara roja de referencia.

Bonus técnico: como la envolvente vale 0 justo en el borde de cada banda, el
cambio de fase cae donde la amplitud es nula y no deja marca.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    n_tiras: int = 16,
    amplitud: float = 3.0,
    alto_banda: float = 4.0,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (para medir las bandas).
        n_tiras: cuántas tejas hay alrededor de la circunferencia.
        amplitud: cuánto sobresale cada teja, en mm.
        alto_banda: alto de cada banda de tejas, en mm.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `paso_z` es None: este patrón usa la altura de capa normal.
    """

    def radio(angulo: float, t: float) -> float:
        posicion = t * altura / alto_banda
        banda = math.floor(posicion)
        dentro = posicion - banda
        fase = math.pi if banda % 2 else 0.0
        envolvente = math.sin(math.pi * dentro)
        return silueta(t) + amplitud * envolvente * math.sin(n_tiras * angulo + fase)

    return radio, None, max(200, n_tiras * 12), None
