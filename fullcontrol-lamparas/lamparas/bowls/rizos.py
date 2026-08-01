"""
Pieza cubierta de rizos: bucles de material que sobresalen de la pared.

Es la técnica de los candeleros "Dream of Glow" de uauproject. La pared no es
una curva suave: el recorrido va tirando bucles hacia afuera, y como en modo
vaso cada vuelta cae encima de la anterior, los bucles se apilan y forman esas
columnas de rulos que parecen gotas o tentáculos.

## Cómo se hace un bucle

Un bucle no es una onda. Una onda entra y sale del radio pero el ángulo siempre
avanza; para que el trazo se cierre sobre sí mismo tiene que *retroceder* en
ángulo. La curva que hace eso es una trocoide: el punto orbita un circulito
mientras avanza alrededor de la pieza.

    radio  = R + a·cos(m·θ)
    ángulo = θ + (a/R)·sin(m·θ)

La derivada del ángulo respecto de θ es `1 + (a·m/R)·cos(m·θ)`. Se vuelve
negativa —o sea, el trazo retrocede y cierra el bucle— solo si:

    a > R / m

Con R = 35 mm y m = 28 rizos, hace falta a > 1.25 mm. Por debajo de eso no hay
rizo, hay una ondulación. El módulo avisa si los parámetros no dan bucle.

## Por qué la base y el cuello salen lisos

En las fotos de referencia la banda de abajo y el cuello son anillos limpios y
los rizos viven solo en el cuerpo. Eso lo hace `desde`/`hasta`: una ventana de
altura que enciende y apaga la amplitud de forma gradual.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def _ventana(t: float, desde: float, hasta: float, suavizado: float) -> float:
    """0 fuera de la banda [desde, hasta], 1 adentro, con rampas suaves."""
    if t <= desde or t >= hasta:
        return 0.0
    subida = min(1.0, (t - desde) / suavizado) if suavizado > 0 else 1.0
    bajada = min(1.0, (hasta - t) / suavizado) if suavizado > 0 else 1.0
    u = min(subida, bajada)
    return u * u * (3 - 2 * u)  # smoothstep, para que no haya un escalón


def construir(
    silueta: Silueta,
    altura: float,
    n_rizos: int = 28,
    amplitud: float = 3.5,
    desde: float = 0.12,
    hasta: float = 0.86,
    suavizado: float = 0.10,
    deriva: float = 0.6,
) -> Tuple[callable, Optional[callable], int, Optional[float], callable]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm.
        n_rizos: cuántos bucles por vuelta.
        amplitud: cuánto sobresale cada bucle, en mm. Tiene que superar
            `radio / n_rizos` o no se forma el bucle (ver el módulo).
        desde, hasta: en qué tramo de la altura (0..1) hay rizos. Fuera de esa
            banda la pared sale lisa.
        suavizado: cuánto tarda la ventana en abrir y cerrar, en unidades de t.
        deriva: vueltas que rota el patrón de rizos a lo largo de la altura.
            Con 0 los rizos se apilan en columnas verticales perfectas; con
            0.5-1 las columnas serpentean, que es lo que se ve en las fotos.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z, funcion_dangulo)
    """
    # aviso temprano: sin esta condición no hay bucle, hay ondulación
    radio_medio = (silueta(0.0) + silueta(0.5) + silueta(1.0)) / 3
    minima = radio_medio / n_rizos
    if amplitud <= minima:
        print(
            f"AVISO: con radio ~{radio_medio:.0f} mm y {n_rizos} rizos, la amplitud "
            f"tiene que superar {minima:.2f} mm para que el trazo cierre el bucle. "
            f"Con {amplitud} mm vas a tener una pared ondulada, no rizos."
        )

    def _fase(angulo: float, t: float) -> float:
        return n_rizos * angulo + deriva * 2 * math.pi * t

    def radio(angulo: float, t: float) -> float:
        env = _ventana(t, desde, hasta, suavizado)
        return silueta(t) + amplitud * env * math.cos(_fase(angulo, t))

    def dangulo(angulo: float, t: float) -> float:
        env = _ventana(t, desde, hasta, suavizado)
        r = max(silueta(t), 1e-6)
        return (amplitud * env / r) * math.sin(_fase(angulo, t))

    # cada bucle necesita bastantes puntos para cerrar limpio
    return radio, None, max(360, n_rizos * 16), None, dangulo
