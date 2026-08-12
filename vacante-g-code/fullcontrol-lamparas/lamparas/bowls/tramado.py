"""
Bowl con entramado en diagonal: dos familias de hélices que se cruzan.

Cómo se arma: dos ondas radiales con la misma cantidad de lóbulos pero que
derivan en sentidos opuestos con la altura. Cada una dibuja una familia de
hélices, y las dos familias se cruzan en diagonal.

La clave está en combinarlas con `max()` y no sumándolas. Sumadas se anulan y
queda una onda estacionaria sin diagonales. Con `max()`, en cada punto gana la
cresta más alta, así que una tira parece pasar *por encima* de la otra en cada
cruce: eso es lo que hace que se lea como trenzado y no como una grilla.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    n_tiras: int = 20,
    amplitud: float = 1.8,
    torsion: float = 8.0,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (sin uso acá, va por uniformidad).
        n_tiras: tiras por vuelta en cada una de las dos familias.
        amplitud: relieve de las tiras en mm.
        torsion: vueltas que deriva cada familia a lo largo de la altura. Sube
            la inclinación de las diagonales: 0 las deja verticales, 8 da unos
            45°, más las acuesta.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `paso_z` es None: este patrón usa la altura de capa normal.
    """

    def radio(angulo: float, t: float) -> float:
        deriva = torsion * 2 * math.pi * t
        una = math.sin(n_tiras * angulo + deriva)
        otra = math.sin(n_tiras * angulo - deriva)
        return silueta(t) + amplitud * max(una, otra)

    return radio, None, max(240, n_tiras * 14), None
