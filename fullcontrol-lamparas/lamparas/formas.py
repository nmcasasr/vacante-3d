"""
Pinceles: la huella que deja un toque sobre la superficie desenrollada.

Un pincel se separa en dos cosas que no hay que confundir:

- **la forma**, que dice dónde termina la huella: círculo, cuadrado, estrella,
  banda... Se evalúa en coordenadas normalizadas `(u, v)`, donde el borde de la
  huella está siempre en distancia 1, sea cual sea la forma.
- **la caída**, que dice cómo se apaga desde el centro hasta ese borde.

    forma(u, v) -> d      0 en el centro, 1 en el borde, >1 afuera
    caida(d)    -> peso   1 en el centro, 0 en el borde

Separarlas es lo que permite tener seis formas y cuatro caídas sin escribir
veinticuatro funciones. Y las dos capas son las mismas para pintar (una máscara
de color) y para deformar (jalar la pared): un cuadrado es un cuadrado.

`u` es el eje del ángulo y `v` el de la altura, los dos ya divididos por el
radio del pincel. Quien llama se encarga de envolver el ángulo — acá `u` ya
llega bien.

## Ver un pincel antes de usarlo

    python -m lamparas.formas estrella --puntas 6
    python -m lamparas.formas cuadrado --caida plano --rotacion 45

Dibuja la huella en la terminal con una rampa de grises, así se ve la caída y
no solo el contorno.
"""

import math
from typing import Callable, Dict, List

# (u, v) -> distancia normalizada: 0 en el centro, 1 en el borde de la huella.
Forma = Callable[[float, float], float]
# distancia -> peso 0..1
Caida = Callable[[float], float]

TAU = 2 * math.pi


# --- formas ---------------------------------------------------------------
# Todas devuelven distancia normalizada, no peso. El truco de las formas con
# vértices (polígono, estrella) es el mismo: se calcula hasta dónde llega el
# borde EN ESA DIRECCIÓN y se divide el radio por eso. Así un hexágono y un
# círculo se apagan igual de parejo, cada uno contra su propio contorno.


def circulo() -> Forma:
    """La elipse de siempre. El pincel por defecto."""
    return lambda u, v: math.hypot(u, v)


def cuadrado() -> Forma:
    """Huella recta, con esquinas. Distancia de Chebyshev."""
    return lambda u, v: max(abs(u), abs(v))


def rombo() -> Forma:
    """Cuadrado parado en una punta. Distancia de Manhattan."""
    return lambda u, v: abs(u) + abs(v)


def poligono(lados: int = 6) -> Forma:
    """
    Polígono regular, con los vértices tocando el borde de la huella.

    Args:
        lados: 3 = triángulo, 5 = pentágono, 6 = hexágono...
    """
    n = max(3, int(lados))
    mitad = math.pi / n
    ap = math.cos(mitad)  # apotema de un polígono de circunradio 1

    def forma(u: float, v: float) -> float:
        r = math.hypot(u, v)
        if r < 1e-12:
            return 0.0
        ang = math.atan2(v, u) % (2 * mitad)
        return r * math.cos(ang - mitad) / ap

    return forma


def estrella(puntas: int = 5, hundido: float = 0.5) -> Forma:
    """
    Estrella: el contorno oscila entre la punta y el valle.

    Args:
        puntas: cuántas puntas tiene.
        hundido: qué tanto se mete el valle. 0 = círculo, 0.5 = estrella
            clásica, 0.8 = una araña.
    """
    n = max(2, int(puntas))
    h = min(max(hundido, 0.0), 0.95)

    def forma(u: float, v: float) -> float:
        r = math.hypot(u, v)
        if r < 1e-12:
            return 0.0
        ang = math.atan2(v, u)
        borde = (1 - h) + h * (1 + math.cos(n * ang)) / 2
        return r / max(borde, 1e-6)

    return forma


def banda() -> Forma:
    """
    Franja horizontal: da toda la vuelta y solo se apaga en altura.

    Es el pincel para un anillo, un cuello o un escalón — lo que en una pieza de
    revolución sale bien, porque no rompe la simetría que el modo vaso ya tiene.
    """
    return lambda u, v: abs(v)


def columna() -> Forma:
    """Franja vertical: una nervadura de la base a la boca."""
    return lambda u, v: abs(u)


def anillo(grosor: float = 0.4) -> Forma:
    """
    Aro: el peso máximo está sobre la circunferencia, no en el centro.

    Args:
        grosor: ancho del aro, como fracción del radio. 0.4 es un aro marcado.
    """
    g = min(max(grosor, 0.05), 1.0)
    centro = 1 - g / 2
    return lambda u, v: abs(math.hypot(u, v) - centro) / (g / 2)


def cruz(grosor: float = 0.35) -> Forma:
    """
    Cruz de dos brazos.

    Args:
        grosor: ancho de cada brazo, como fracción del radio.
    """
    g = min(max(grosor, 0.05), 1.0)
    return lambda u, v: min(max(abs(u), abs(v) / g), max(abs(u) / g, abs(v)))


FORMAS: Dict[str, Callable[..., Forma]] = {
    "circulo": circulo,
    "cuadrado": cuadrado,
    "rombo": rombo,
    "poligono": poligono,
    "estrella": estrella,
    "banda": banda,
    "columna": columna,
    "anillo": anillo,
    "cruz": cruz,
}


# --- caídas ---------------------------------------------------------------
# Todas valen exactamente 1 en d=0 y exactamente 0 en d=1. Que la gaussiana
# llegue a cero de verdad importa: una gaussiana cruda deja una cola infinita,
# y en una pieza eso es una deformación de 0.05 mm en TODA la superficie, que
# se ve como una capa de suciedad y no como un toque.

_K = 2.3  # exp(-K) ~ 0.10: la cola que se recorta


def _gauss(d: float) -> float:
    if d >= 1.0:
        return 0.0
    g = math.exp(-_K * d * d)
    return (g - math.exp(-_K)) / (1 - math.exp(-_K))


def _suave(d: float) -> float:
    if d >= 1.0:
        return 0.0
    s = 1 - d
    return s * s * (3 - 2 * s)


def _pico(d: float) -> float:
    return max(0.0, 1 - d)


def _plano(d: float) -> float:
    return 1.0 if d <= 1.0 else 0.0


def _meseta(d: float) -> float:
    """Plana por dentro y suave en el borde. La que quiere 'aplanar'."""
    if d <= 0.6:
        return 1.0
    if d >= 1.0:
        return 0.0
    s = (1 - d) / 0.4
    return s * s * (3 - 2 * s)


CAIDAS: Dict[str, Caida] = {
    "gauss": _gauss,
    "suave": _suave,
    "meseta": _meseta,
    "pico": _pico,
    "plano": _plano,
}


def resolver(forma="circulo", caida: str = "gauss", rotacion: float = 0.0,
             **kwargs) -> Callable[[float, float], float]:
    """
    Arma el pincel completo: `(u, v) -> peso 0..1`.

    Args:
        forma: nombre en `FORMAS`, o una `Forma` ya hecha.
        caida: nombre en `CAIDAS`.
        rotacion: grados que gira la huella. Sirve para parar un cuadrado en
            una punta o alinear una estrella.
        **kwargs: parámetros de la forma (`lados`, `puntas`, `grosor`...).
    """
    if callable(forma):
        f = forma
    else:
        if forma not in FORMAS:
            raise ValueError(
                f"forma desconocida: {forma!r}. Opciones: {', '.join(sorted(FORMAS))}"
            )
        fabrica = FORMAS[forma]
        # Cada forma acepta solo lo suyo; pasarle `puntas` a un cuadrado es un
        # error del que llama, no algo para ignorar en silencio.
        acepta = fabrica.__code__.co_varnames[: fabrica.__code__.co_argcount]
        sobra = [k for k in kwargs if k not in acepta]
        if sobra:
            raise ValueError(
                f"la forma {forma!r} no acepta {', '.join(sorted(sobra))}"
                + (f"; acepta {', '.join(acepta)}" if acepta else "; no lleva parámetros")
            )
        f = fabrica(**kwargs)

    if caida not in CAIDAS:
        raise ValueError(
            f"caída desconocida: {caida!r}. Opciones: {', '.join(sorted(CAIDAS))}"
        )
    c = CAIDAS[caida]

    if not rotacion:
        return lambda u, v: c(f(u, v))

    rad = math.radians(rotacion)
    cs, sn = math.cos(rad), math.sin(rad)
    return lambda u, v: c(f(u * cs + v * sn, -u * sn + v * cs))


# --- ver el pincel --------------------------------------------------------

_RAMPA = " ·-=+*#@"


def rasterizar(pincel: Callable[[float, float], float], ancho: int = 61,
               alto: int = 25, margen: float = 1.25) -> str:
    """
    Dibuja la huella en ASCII con una rampa de grises.

    En grises y no en blanco y negro a propósito: el contorno de un pincel se
    adivina, pero la caída —que es la mitad del pincel— no se ve con un umbral.
    """
    filas: List[str] = []
    for f in range(alto):
        v = margen * (1 - 2 * f / (alto - 1))
        fila = []
        for c in range(ancho):
            u = margen * (2 * c / (ancho - 1) - 1)
            w = min(max(pincel(u, v), 0.0), 1.0)
            fila.append(_RAMPA[min(len(_RAMPA) - 1, int(w * len(_RAMPA)))])
        filas.append("".join(fila))
    return "\n".join(filas)


def _cli() -> None:
    """
    Ver un pincel en la terminal:

        python -m lamparas.formas estrella --puntas 6 --hundido 0.6
        python -m lamparas.formas cuadrado --rotacion 45 --caida plano
        python -m lamparas.formas anillo --grosor 0.25
    """
    import argparse

    p = argparse.ArgumentParser(prog="lamparas.formas", description=_cli.__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("forma", nargs="?", default="circulo", choices=sorted(FORMAS))
    p.add_argument("--caida", default="gauss", choices=sorted(CAIDAS))
    p.add_argument("--rotacion", type=float, default=0.0)
    p.add_argument("--lados", type=int)
    p.add_argument("--puntas", type=int)
    p.add_argument("--hundido", type=float)
    p.add_argument("--grosor", type=float)
    p.add_argument("--cols", type=int, default=61)
    p.add_argument("--filas", type=int, default=25)
    args = p.parse_args()

    extra = {k: v for k, v in
             (("lados", args.lados), ("puntas", args.puntas),
              ("hundido", args.hundido), ("grosor", args.grosor))
             if v is not None}
    try:
        pincel = resolver(args.forma, caida=args.caida, rotacion=args.rotacion, **extra)
    except ValueError as e:
        p.error(str(e))
    print(f"pincel '{args.forma}' con caída '{args.caida}'"
          + (f", girado {args.rotacion:g}°" if args.rotacion else ""))
    print(rasterizar(pincel, ancho=args.cols, alto=args.filas))


if __name__ == "__main__":
    _cli()
