"""
Bowl con malla fina de rombos.

Cómo se arma: una onda radial de frecuencia alta, con **medio lóbulo de más por
vuelta** (`n_lobulos + 0.5`). Ese medio lóbulo hace que las crestas de una capa
caigan exactamente en los valles de la de abajo. Apiladas, las crestas dibujan
diagonales cruzadas y la pared se lee como un tejido de rombos: es el bowl
amarillo y el morado de las referencias.

El truco del medio lóbulo solo funciona porque `generar_pieza()` pasa el ángulo
acumulado de toda la espiral y no uno que se reinicia en cada vuelta: la
inversión sale sola y sin salto en la costura.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    n_lobulos: int = 60,
    amplitud: float = 0.9,
    deriva: float = 0.0,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (sin uso acá, va por uniformidad).
        n_lobulos: lóbulos por vuelta. Más = malla más fina y gcode más pesado.
        amplitud: profundidad del relieve en mm. Cerca de la altura de capa
            (0.4) queda sutil; 1.5 o más queda muy marcado.
        deriva: vueltas completas que la malla rota a lo largo de la altura.
            Con 0 las diagonales son simétricas; con 2 o 3 el tejido se
            arremolina como en el bowl amarillo.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `paso_z` es None: este patrón usa la altura de capa normal.
    """
    frecuencia = n_lobulos + 0.5  # el medio lóbulo es lo que teje la malla

    def radio(angulo: float, t: float) -> float:
        giro = deriva * 2 * math.pi * t
        return silueta(t) + amplitud * math.sin(frecuencia * angulo + giro)

    return radio, None, max(240, int(n_lobulos * 6)), None
