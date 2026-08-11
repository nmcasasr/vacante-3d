"""
Ondas horizontales que recorren la pared, tipo cerámica torneada.

El patrón: el radio ondula con la ALTURA en vez de con el ángulo. Eso da
cordones que sobresalen formando anillos, uno cada `paso` milímetros. Y como la
fase corre también con el ángulo, los anillos no quedan perfectamente
horizontales: suben y bajan mientras dan la vuelta, que es lo que los hace
parecer torneados a mano y no maquinados.

    radio = silueta(t) + amplitud * sin( 2π·altura/paso + giro·ángulo )

Los tres parámetros hacen tres cosas distintas y conviene no confundirlas:

- `paso` es cada cuántos mm aparece un anillo. Es lo que se ve de lejos.
- `giro` es cuántas veces sube y baja el anillo al dar la vuelta entera. Con 0
  quedan anillos perfectamente horizontales, que es el aspecto maquinado. Con 2
  o 3 quedan las ondas suaves de la referencia.
- `amplitud` es cuánto sobresale. Va contra el ancho del cordón: si dos vueltas
  vecinas se corren radialmente más que el ancho del cordón, dejan de tocarse y
  la pared se abre. Con boquilla de 0.8 el techo práctico es ~0.6 mm.

`n_lados` deforma la sección de círculo a polígono redondeado — la boca
cuadrada de la referencia sale con `n_lados=4`.

Y encima de todo eso se le puede sumar el diente de sierra de `zigzag.py`, que
opera en el otro eje: los anillos ondulan con la ALTURA, los dientes con el
ÁNGULO. Como no compiten por el mismo eje, se ven los dos a la vez — anillos
gruesos recorridos por un rayado fino. Con `alternar=1` los dientes van una
vuelta sí y otra no, que es lo que los hace leer como textura.

Las dos amplitudes se suman, y la suma es la que tiene que respetar el ancho
del cordón: `amplitud + amp_dientes <= ~0.6` con boquilla de 0.8. El módulo
avisa si se pasa.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    paso: float = 3.0,
    amplitud: float = 0.55,
    giro: float = 3.0,
    n_lados: int = 0,
    redondez: float = 2.5,
    dientes: int = 0,
    amp_dientes: float = 0.0,
    alternar: int = 1,
    ancho_cordon: float = 0.8,
    altura_capa: float = 0.4,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm. Hace falta de verdad: `paso`
            está en milímetros y `t` es adimensional, así que sin la altura no
            se puede convertir uno en el otro y los anillos saldrían más juntos
            en una pieza baja que en una alta.
        paso: cada cuántos mm de altura aparece un anillo.
        amplitud: cuánto sobresale el anillo, en mm.
        giro: cuántas subidas y bajadas da el anillo en una vuelta completa.
            0 = anillos horizontales perfectos.
        n_lados: 0 para sección circular; 4 para una boca cuadrada redondeada.
        redondez: cuánto sobresalen los lados del polígono, en mm.
        dientes: cuántos dientes de sierra entran en una vuelta. 0 los apaga.
            Es el patrón de `zigzag.py`, sumado encima de los anillos.
        amp_dientes: cuánto sobresale cada diente, en mm.
        alternar: 1 = dientes una vuelta sí y otra no (textura); 0 = en todas.
        ancho_cordon: para avisar si las dos ondas juntas despegan la pared.
        altura_capa: hace falta para ese aviso — cuánto avanza el anillo entre
            una vuelta y la siguiente depende de la altura de capa.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `funcion_dz` y `paso_z` son None: el patrón no toca la Z, solo el radio, así
    que las vueltas apoyan enteras y la pared queda estanca.
    """
    if paso <= 0:
        raise ValueError("`paso` tiene que ser mayor que 0")

    # ¿Se despega la pared? Lo que importa no es la amplitud sino cuánto se
    # corre el radio ENTRE DOS VUELTAS VECINAS, y las dos ondas contribuyen
    # distinto:
    #
    # - Los anillos varían con la ALTURA, con período `paso` mm. Entre una
    #   vuelta y la siguiente solo avanzan una altura de capa, así que su salto
    #   es amplitud·2π·capa/paso — con paso 3 y capa 0.4, un 84 % MENOS que la
    #   amplitud. Contarla entera es lo que hace que un aviso cante lobo.
    # - Los dientes con `alternar` sí saltan entero: una vuelta los tiene y la
    #   siguiente no.
    salto = amplitud * 2 * math.pi * altura_capa / paso
    salto += amp_dientes if (dientes and alternar) else 0.0
    if salto > ancho_cordon:
        print(
            f"AVISO: entre dos vueltas vecinas el radio se corre hasta {salto:.2f} mm, "
            f"más que el ancho del cordón ({ancho_cordon} mm): dejan de tocarse y la "
            f"pared puede quedar abierta. Bajá `amplitud`, `amp_dientes`, o subí `paso`."
        )

    def _triangulo(x: float) -> float:
        """Onda triangular de -1 a 1 — el mismo diente de sierra de zigzag.py."""
        return 2 / math.pi * math.asin(math.sin(x))

    def radio(angulo: float, t: float) -> float:
        base = silueta(t)
        if n_lados:
            base += redondez * math.cos(n_lados * angulo)
        r = base + amplitud * math.sin(2 * math.pi * t * altura / paso + giro * angulo)
        # Los dientes van en el otro eje: los anillos ondulan con la altura y
        # estos con el ángulo, así que se ven los dos a la vez.
        if dientes and amp_dientes:
            if not (alternar and int(angulo / (2 * math.pi)) % 2):
                r += amp_dientes * _triangulo(angulo * dientes)
        return r

    # Resolución: hay que muestrear bien la onda ANGULAR (la de `giro`) y los
    # lados del polígono. La onda vertical no pide resolución angular ninguna.
    por_vuelta = max(200, int(abs(giro) * 24), n_lados * 40, dientes * 8)
    return radio, None, por_vuelta, None
