"""
Bowl calado: celosía de verdad, con agujeros pasantes.

Cómo se arma: acá la pared es lisa y lo que ondula es la **Z**. Dentro de cada
vuelta la boquilla sube y baja `amplitud_z`, y la onda se invierte de una vuelta
a la otra (medio nodo de más por vuelta). Entonces dos vueltas consecutivas se
tocan solo en los cruces y entre cruce y cruce queda aire: el calado de la pieza
de `claywovenofficial` de las referencias.

OJO: entre nodo y nodo el material queda puenteando en el aire y descuelga un
poco. Ese descuelgue es parte del efecto, pero significa que esta pieza es
**decorativa**: no contiene líquidos ni aguanta como las otras tres. Si querés
la estética calada en un bowl utilizable, dejá `base_solida=True` (viene así) y
subí `capas_transicion` para que el arranque sea macizo.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    n_nodos: int = 60,
    amplitud_z: float = 0.7,
    solape: float = 0.15,
    ondulacion_radial: float = 0.0,
) -> Tuple[callable, Optional[callable], int, float]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (sin uso acá, va por uniformidad).
        n_nodos: cruces por vuelta. Más nodos = agujeros más chicos y tramos
            colgados más cortos, o sea más fácil de imprimir. Con 60 nodos y un
            radio de 55 mm, cada tramo al aire mide unos 5.8 mm.
        amplitud_z: cuánto sube y baja la boquilla dentro de la vuelta, en mm.
            Es lo que abre el calado.
        solape: cuánto se encaja cada vuelta en la de abajo, como fracción del
            paso teórico. 0 deja las vueltas apenas besándose en los nodos (la
            pieza se desarma); 0.15 les da un poco de mordida para que suelden.
        ondulacion_radial: onda radial opcional encima, en mm, para que además
            del calado la pared tenga relieve.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    El `paso_z` que devuelve es la clave de este diseño: la pieza sube
    2*amplitud_z por vuelta en vez de una altura de capa. Con el paso normal,
    la cresta de una vuelta queda por debajo del valle de la anterior y la
    boquilla vuelve a bajar sobre material ya impreso.
    """
    frecuencia = n_nodos + 0.5  # el medio nodo invierte la onda vuelta a vuelta
    paso_z = 2 * amplitud_z * (1 - solape)

    def radio(angulo: float, t: float) -> float:
        if ondulacion_radial:
            return silueta(t) + ondulacion_radial * math.sin(frecuencia * angulo)
        return silueta(t)

    def dz(angulo: float, t: float) -> float:
        return amplitud_z * math.sin(frecuencia * angulo)

    return radio, dz, max(240, int(n_nodos * 8)), paso_z
