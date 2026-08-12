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


def candelero(radio_base: float = 45.0, radio_boca: float = 14.0, alto_cuello: float = 0.15) -> Silueta:
    """
    Silueta de candelero: cuerpo acampanado que se va cerrando hacia arriba y
    termina en un cuello recto. Es la forma de las piezas "Dream of Glow".

    Al cerrarse con la altura no tiene nada de voladizo, así que es de las más
    fáciles de imprimir: cada vuelta apoya de sobra sobre la anterior.
    """

    def silueta(t: float) -> float:
        if t >= 1 - alto_cuello:
            return radio_boca
        u = t / (1 - alto_cuello)
        s = u * u * (3 - 2 * u)
        return radio_base + (radio_boca - radio_base) * s

    return silueta


def cilindro(
    radio_base: float = 45.0,
    radio_boca: float = None,
    vuelo: float = 0.0,
    vuelo_alto: float = 0.18,
    curva_vuelo: float = 1.0,
) -> Silueta:
    """
    Cilindro recto, o cono truncado si se le da un radio de boca distinto.

    `vuelo` abre el borde de arriba, como un ala, y `curva_vuelo` decide si es
    un cono suave (1) o un ala caída (2-3). Se aplica solo
    en la fracción final `vuelo_alto` de la altura y con un smoothstep, no con
    una recta: la derivada arranca en 0, así que el ala NACE del cilindro en vez
    de empezar con un quiebre. Un cambio de pendiente brusco a esa altura se ve
    como un defecto de impresión y no como parte del diseño.

    Ojo con el voladizo: el ala se abre `vuelo` mm en `vuelo_alto · altura` mm.
    Con 5 mm en el 18 % de una pieza de 150 son 27 mm de altura para 5 de radio,
    unos 10° — tranquilo. Pedile 20 mm de vuelo y se descuelga.

    Args:
        radio_base: radio del cilindro, en mm.
        radio_boca: si se le da otro valor, la pieza sale cónica en vez de recta.
        vuelo: cuántos mm se abre el borde de arriba. 0 lo apaga.
        vuelo_alto: en qué fracción final de la altura ocurre esa apertura. Más
            alto = el ala se abre en más altura y apoya mejor.
        curva_vuelo: 1 = ala cónica, se abre parejo. 2-3 = ala caída: arranca
            casi pegada al cilindro y se acuesta al final. Subirlo hace que el
            radio crezca más rápido en las últimas vueltas, que es exactamente
            lo que decide si apoya o se descuelga — mirá el aviso de voladizo.

    Es la silueta para una matera: pared vertical, sin voladizo en ninguna
    parte, y con base sólida queda un recipiente. Al no abrirse con la altura
    es la más fácil de imprimir de todas — cada vuelta apoya entera sobre la
    anterior — y por eso también es la mejor para probar patrones: si algo sale
    mal, no fue la silueta.
    """
    boca = radio_base if radio_boca is None else radio_boca

    def silueta(t: float) -> float:
        r = radio_base + (boca - radio_base) * t
        if vuelo and t > 1 - vuelo_alto:
            u = (t - (1 - vuelo_alto)) / max(vuelo_alto, 1e-6)
            # curva_vuelo = 1 -> smoothstep, el ala nace y termina horizontal.
            # > 1 -> potencia: el ala arranca casi pegada al cilindro y se va
            # acostando, que es lo que la hace ver caída. El precio está en la
            # derivada: el radio crece `vuelo·curva/vueltas` por vuelta al final,
            # o sea `curva` veces más rápido que con una recta, y eso es lo que
            # decide si apoya o se cae. Mirá el aviso de voladizo.
            r += vuelo * (u * u * (3 - 2 * u) if curva_vuelo == 1 else u ** curva_vuelo)
        return r

    return silueta


def huevo(
    radio_max: float = 45.0,
    radio_base: float = 20.0,
    radio_boca: float = 27.0,
    t_panza: float = 0.36,
) -> Silueta:
    """
    Silueta de huevo o gota: base angosta, panza abajo y cuello que se cierra.

    Se arma con dos smoothsteps que se encuentran en la panza. La gracia de
    usar smoothstep y no una recta o un seno es que la derivada vale 0 justo en
    `t_panza`: las dos mitades se empalman con tangente horizontal y no queda
    una arista a media altura, que es lo que delata una silueta armada a
    pedazos.

    El voladizo vive en la parte de abajo, donde el radio crece. `generar_pieza`
    lo mide y avisa; si se pasa de 45°, subí `t_panza` (la panza sube y la
    apertura se reparte en más altura) o agrandá `radio_base`.

    Args:
        radio_max: radio de la panza, el punto más ancho.
        radio_base: radio del apoyo. Angosto se ve mejor y es más inestable.
        radio_boca: radio de la boca.
        t_panza: a qué altura relativa está la panza. 0.36 = abajo del medio,
            que es lo que la hace leer como gota y no como barril.
    """

    def silueta(t: float) -> float:
        if t <= t_panza:
            u = t / max(t_panza, 1e-6)
            s = u * u * (3 - 2 * u)
            return radio_base + (radio_max - radio_base) * s
        u = (t - t_panza) / max(1 - t_panza, 1e-6)
        s = u * u * (3 - 2 * u)
        return radio_max + (radio_boca - radio_max) * s

    return silueta


def trompeta(
    radio_base: float = 26.0,
    radio_bulbo: float = 34.0,
    radio_cuello: float = 15.0,
    radio_ala: float = 62.0,
    t_bulbo: float = 0.22,
    t_cuello: float = 0.55,
    curva_ala: float = 2.2,
) -> Silueta:
    """
    Bulbo abajo, cuello angosto y ala ancha arriba — la forma de hongo o copa.

    El ala es la parte difícil y `curva_ala` es la perilla que decide si sale o
    no. Controla la concavidad: con 1.0 el ala es un cono recto y el radio crece
    parejo; subiéndolo el ala arranca casi vertical y se va acostando, que es lo
    que la hace ver caída en vez de un embudo.

    **Y ahí está la trampa.** Acostarse significa que el radio crece MÁS por
    vuelta al final. En modo vaso cada vuelta apoya sobre la de abajo, así que
    si el radio crece más que el ancho del cordón entre una vuelta y la
    siguiente, la nueva queda en el aire y se descuelga. Bajar la velocidad
    ayuda a que el cordón cuaje antes de que le pasen por encima, pero **no
    cambia el apoyo**: eso es geometría, no tiempo. El techo real es

        Δradio por vuelta < ancho del cordón

    y con 50 % de solape o más se imprime tranquilo. `generar_pieza` lo mide y
    lo reporta; mirá ese número antes de mandar a imprimir, no el ángulo.

    Args:
        radio_base: radio del apoyo.
        radio_bulbo: radio máximo del bulbo de abajo.
        radio_cuello: radio del cuello, el punto más angosto.
        radio_ala: radio del borde del ala.
        t_bulbo: altura relativa del bulbo.
        t_cuello: altura relativa del cuello, donde arranca el ala.
        curva_ala: 1 = ala cónica; 2-3 = ala caída, más exigente de imprimir.
    """

    def silueta(t: float) -> float:
        if t <= t_bulbo:
            u = t / max(t_bulbo, 1e-6)
            s = u * u * (3 - 2 * u)
            return radio_base + (radio_bulbo - radio_base) * s
        if t <= t_cuello:
            u = (t - t_bulbo) / max(t_cuello - t_bulbo, 1e-6)
            s = u * u * (3 - 2 * u)
            return radio_bulbo + (radio_cuello - radio_bulbo) * s
        u = (t - t_cuello) / max(1 - t_cuello, 1e-6)
        return radio_cuello + (radio_ala - radio_cuello) * (u ** curva_ala)

    return silueta


SILUETAS = {
    "bol": bol,
    "trompeta": trompeta,
    "huevo": huevo,
    "cilindro": cilindro,
    "copa": copa,
    "platillo": platillo,
    "campana": campana,
    "candelero": candelero,
}
