"""
Textura de zigzag que dibuja una máscara sobre la pared.

El patrón: mientras la boquilla avanza por la vuelta, el radio va y viene en
diente de sierra; la vuelta siguiente va lisa. Alternar es lo que hace que se
lea como textura y no como una pared ondulada — el cordón liso de arriba marca
el borde de los dientes de abajo, igual que en las piezas de referencia.

Lo interesante es que el zigzag **solo se aplica donde la máscara vale 1**. O
sea que el dibujo aparece por relieve: donde hay dibujo la pared tiene textura,
donde no, está lisa. Ver `lamparas/superficie.py` para las máscaras y para por
qué el dibujo se hace con textura en vez de con color.

## Por qué el zigzag es RADIAL y no vertical

La primera intuición es hacer ondular la Z dentro de la vuelta, como
`celosia.py`. No sirve acá: con paso de capa 0.4 mm y una onda de ±0.15, el
hueco entre una vuelta y la siguiente pasa a valer entre 0.25 y 0.55 mm, y
donde vale 0.55 las capas no se tocan. En una lámpara eso es el calado que
buscás; en una matera es una filtración.

Moviendo el RADIO, la Z queda intacta: todas las vueltas se apoyan enteras
sobre la anterior, la pared sigue siendo estanca, y la textura se ve igual
porque un diente de 0.6 mm sobre una boquilla de 0.8 se nota perfectamente.
"""

import math
from typing import Optional, Tuple

from ..superficie import Mascara, resolver
from .siluetas import Silueta

TAU = 2 * math.pi


def _triangulo(x: float) -> float:
    """Onda triangular de -1 a 1. El diente de sierra que da el zigzag."""
    return 2 / math.pi * math.asin(math.sin(x))


def construir(
    silueta: Silueta,
    altura: float,
    mascara="caritas",
    dientes: int = 60,
    amplitud: float = 0.6,
    alternar: int = 1,
    ancho_grados: float = 140.0,
    centro_t: float = 0.5,
    alto_t: float = 0.55,
    hasta_t: float = 1.0,
    desvanecer: float = 0.06,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (no se usa; va por el contrato).
        mascara: nombre de `superficie.MASCARAS` ('caritas', 'feliz', 'triste',
            'ninguna') o una `Mascara` ya armada. 'ninguna' texturiza la pieza
            entera, que sirve para ver la textura sola.
        dientes: cuántos dientes de sierra entran en una vuelta completa. Más
            dientes = textura más fina. El límite es la boquilla: con 0.8 mm y
            radio 45, más de ~180 dientes ya no se distinguen.
        amplitud: cuánto sobresale el diente, en mm. 0.6 con boquilla de 0.8 se
            ve y se toca sin comprometer la pared.
        alternar: 1 = una vuelta con zigzag y la siguiente lisa (lo que da la
            textura); 0 = todas las vueltas con zigzag (queda una pared
            ondulada pareja, sin lectura de dibujo).
        ancho_grados, centro_t, alto_t: tamaño y posición del dibujo, se le
            pasan a la máscara. Ver `superficie.carita()`.
        hasta_t: por encima de esta altura relativa los dientes se apagan.
            Sirve para no meterlos donde la pieza ya está en voladizo: con
            `alternar=1` una vuelta tiene dientes y la siguiente no, así que el
            radio salta la amplitud entera entre vueltas vecinas, y eso se SUMA
            a lo que ya se corre una silueta que se abre. En un ala con 39 % de
            solape, agregarle 0.25 mm de diente lo baja a 18 % y se cae.
        desvanecer: en qué fracción de altura se apagan, para que no haya un
            corte brusco donde terminan.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `funcion_dz` es None y `paso_z` es None: este patrón no toca la Z, así que
    la pieza sube como una capa normal y la pared queda estanca.
    """
    fn: Mascara = resolver(
        mascara, ancho_grados=ancho_grados, centro_t=centro_t, alto_t=alto_t
    ) if not callable(mascara) else mascara

    def radio(angulo: float, t: float) -> float:
        base = silueta(t)
        # `angulo` viene acumulado a lo largo de toda la espiral, así que
        # dividirlo por 2pi da el número de vuelta y con eso se alterna.
        if alternar and int(angulo / TAU) % 2:
            return base
        peso = fn(angulo, t)
        if peso <= 0:
            return base
        if hasta_t < 1.0:
            if t >= hasta_t:
                return base
            if t > hasta_t - desvanecer:
                u = (hasta_t - t) / max(desvanecer, 1e-6)
                peso *= u * u * (3 - 2 * u)
        return base + amplitud * _triangulo(angulo * dientes) * peso

    # ~8 muestras por diente: menos y el triángulo sale redondeado, que es
    # justo lo que hace que la textura deje de leerse.
    return radio, None, max(240, dientes * 8), None
