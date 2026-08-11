"""
Pintar patrones sobre la superficie de una pieza en modo vaso.

La idea que pediste: una función que, dado un punto de la superficie, diga si
ahí va o no va el dibujo. En modo vaso cada punto del recorrido queda definido
por dos números —el ángulo alrededor del eje y la altura— así que una máscara
es exactamente eso:

    mascara(angulo_rad, t) -> 0.0 (fondo) .. 1.0 (dibujo)

donde `t` va de 0.0 en la base a 1.0 en el borde. Es el mismo par de argumentos
que ya reciben `funcion_radio` y `funcion_dz` en `comun.generar_pieza()`, así
que una máscara se enchufa directo en cualquier patrón sin tocar el generador.

## Cómo se dibuja la máscara sobre la pieza

Hay dos formas, y NO son intercambiables:

- **Como textura** (lo que hace `bowls/zigzag.py`): donde la máscara vale 1, el
  recorrido zigzaguea; donde vale 0, va liso. El dibujo se ve por relieve y por
  cómo pega la luz. Cuesta cero: es la misma cantidad de material, el mismo
  tiempo, y el cambio se decide punto por punto.

- **Como color**, cambiando de filamento al entrar y salir del dibujo. Se puede
  —`colores.cambio_ams()` está para eso— pero para un dibujo con detalle **no
  funciona**, por dos motivos independientes, los dos medidos:

  1. *Tiempo.* Cada cambio del AMS son ~56 s (29 s de descarga + 25 s de carga,
     números del propio perfil de Bambu). Una carita con ojos y boca, de 40 mm
     de alto, cruza unas 100 capas y necesita del orden de 10 cambios por capa:
     1000 cambios, casi 16 h **solo cambiando filamento**.

  2. *Sangrado*, que es peor y no se arregla con tiempo. A radio 40 una vuelta
     entera consume 33 mm de filamento, y un blanco→negro tarda ~70 mm en salir
     limpio: **2.1 vueltas**. Un ojo ocupa 15° de arco, o sea 0.04 vueltas. El
     color tardaría 50 veces más en limpiarse que lo que dura el detalle que
     querías pintar. Con purga se arregla el sangrado y se multiplica el tiempo.

  El color sí sirve para **bandas horizontales**: ahí el cambio dura una vuelta
  entera o más y el sangrado queda como un degradado de borde, que es
  justamente el efecto que busca `colores.py`.

O sea: **la forma se hace con textura, el color se hace por bandas.** Es lo que
combinan las piezas de referencia, y es lo que sale bien en una A1.

## Ver la máscara antes de imprimir

`rasterizar()` la dibuja en ASCII en la terminal. Iterar ahí cuesta
milisegundos; iterar generando gcode cuesta minutos.
"""

import math
from typing import Callable, List

# (angulo_rad, t) -> 0.0 (fondo) .. 1.0 (dibujo)
Mascara = Callable[[float, float], float]

TAU = 2 * math.pi


def _envolver(delta: float) -> float:
    """Lleva una diferencia de ángulos al rango [-pi, pi]."""
    return (delta + math.pi) % TAU - math.pi


def constante(valor: float = 1.0) -> Mascara:
    """Máscara uniforme. Útil como fondo o para desactivar el dibujo."""
    return lambda angulo, t: valor


def banda(desde_t: float, hasta_t: float) -> Mascara:
    """Franja horizontal entre dos alturas relativas."""
    return lambda angulo, t: 1.0 if desde_t <= t <= hasta_t else 0.0


def carita(
    feliz: bool = True,
    angulo_centro: float = 0.0,
    ancho_grados: float = 140.0,
    centro_t: float = 0.5,
    alto_t: float = 0.55,
    grosor: float = 0.16,
) -> Mascara:
    """
    Una carita, feliz o triste, centrada en un ángulo.

    El truco para que no se deforme: se trabaja en coordenadas LOCALES de la
    cara, `(u, v)`, las dos normalizadas a -1..1 dentro del recuadro que ocupa
    el dibujo. Así el ancho se mide en grados y el alto en fracción de la
    pieza, y la cara se estira o encoge con la pieza en vez de quedar pegada a
    un tamaño en mm que después no entra.

    Args:
        feliz: True sonríe, False está triste (la boca se invierte).
        angulo_centro: dónde va la cara, en radianes.
        ancho_grados: cuánto arco ocupa. 140° deja lugar para dos caras
            opuestas sin que se toquen.
        centro_t: altura relativa del centro de la cara (0..1).
        alto_t: qué fracción de la altura ocupa.
        grosor: espesor del trazo, en unidades locales.

    Returns:
        Una `Mascara`.
    """
    medio_ancho = math.radians(ancho_grados) / 2
    medio_alto = alto_t / 2

    def mascara(angulo: float, t: float) -> float:
        u = _envolver(angulo - angulo_centro) / medio_ancho
        v = (t - centro_t) / medio_alto
        # fuera del recuadro de la cara no hay nada que dibujar
        if abs(u) > 1.2 or abs(v) > 1.2:
            return 0.0

        # --- ojos: dos discos ---
        for ou in (-0.36, 0.36):
            if (u - ou) ** 2 + (v - 0.34) ** 2 < 0.15 ** 2:
                return 1.0

        # --- boca: un arco de circunferencia ---
        # Sonrisa: la MITAD DE ABAJO de un círculo alto. Tristeza: la mitad de
        # ARRIBA de un círculo bajo. Es el mismo arco espejado, y por eso las
        # dos caras salen del mismo código con un solo signo de diferencia.
        cv, radio_boca = (0.34, 0.62) if feliz else (-0.92, 0.62)
        d = math.hypot(u, v - cv)
        if abs(d - radio_boca) < grosor / 2:
            en_arco = (v - cv) < -0.12 if feliz else (v - cv) > 0.12
            if en_arco:
                return 1.0
        return 0.0

    return mascara


def caritas(angulo_feliz: float = 0.0, **kwargs) -> Mascara:
    """
    Feliz de un lado, triste del otro. Es `--p mascara=caritas`.

    La triste va a 180°, así que en la pieza terminada ves una cara por lado.
    """
    a = carita(feliz=True, angulo_centro=angulo_feliz, **kwargs)
    b = carita(feliz=False, angulo_centro=angulo_feliz + math.pi, **kwargs)
    return unir(a, b)


def parches(
    cantidad: int = 6,
    semilla: int = 0,
    ancho_grados: float = 70.0,
    alto_t: float = 0.10,
    borde: float = 0.25,
) -> Mascara:
    """
    Manchas sueltas repartidas por la pieza, para pintar con dos colores.

    Pensado para lo contrario de un degradado: en vez de un color y después el
    otro, parches del segundo color salpicados sobre el primero. Y pensado para
    ser BARATO, que es lo que un dibujo con detalle no puede ser.

    ## Qué lo hace barato

    Un cambio de filamento se paga por cada vez que el recorrido ENTRA o SALE
    de la figura. Una carita cuesta ~10 cambios por capa, porque una capa a la
    altura de los ojos cruza cuatro bordes por cara. Un parche cuesta 2 por
    capa, y solo en las capas que lo atraviesan.

    O sea que el costo es `2 · cantidad · (alto_t · n_capas)` y no depende de
    lo ancho que sea el parche. **Pocos parches y altos** sale barato; muchos y
    bajitos sale igual de caro que la carita. `generar_pieza` imprime el total
    antes de generar.

    Y el sangrado acá no molesta: un parche de 10 capas dura varias vueltas, y
    que sus bordes salgan difuminados es lo que lo hace ver orgánico en vez de
    recortado.

    Args:
        cantidad: cuántos parches.
        semilla: cambiala para otra distribución.
        ancho_grados: qué arco ocupa cada uno. No afecta el costo.
        alto_t: qué fracción de la altura ocupa cada uno. **Este sí** afecta el
            costo, linealmente.
        borde: cuánto del parche es transición suave (0 = borde duro).

    Returns:
        Una `Mascara`.
    """
    from .estructura import _fases

    r = _fases(semilla, cantidad * 3)
    centros = []
    for _ in range(cantidad):
        centros.append((
            next(r) * TAU,
            0.08 + next(r) * 0.84,
            0.7 + next(r) * 0.6,           # tamaños distintos, si no parece estampado
        ))
    sigma_a = math.radians(ancho_grados) / 2
    sigma_t = alto_t / 2

    def mascara(angulo: float, t: float) -> float:
        for centro_a, centro_t, escala in centros:
            da = _envolver(angulo - centro_a) / (sigma_a * escala)
            dt = (t - centro_t) / (sigma_t * escala)
            d = math.hypot(da, dt)
            if d <= 1.0 - borde:
                return 1.0
            if d < 1.0:
                return (1.0 - d) / max(borde, 1e-6)
        return 0.0

    return mascara


def unir(*mascaras: Mascara) -> Mascara:
    """Une varias máscaras: el dibujo es la suma de todas."""
    return lambda angulo, t: max(m(angulo, t) for m in mascaras)


def invertir(mascara: Mascara) -> Mascara:
    """Intercambia dibujo y fondo."""
    return lambda angulo, t: 1.0 - mascara(angulo, t)


MASCARAS = {
    "caritas": caritas,
    "parches": parches,
    "feliz": lambda **kw: carita(feliz=True, **kw),
    "triste": lambda **kw: carita(feliz=False, **kw),
    "ninguna": lambda **kw: constante(1.0),
}


def resolver(nombre, **kwargs) -> Mascara:
    """
    Convierte el nombre que llega por `--p mascara=...` en una `Mascara`.

    Si ya viene una máscara (uso como librería) la deja pasar tal cual.
    """
    if callable(nombre):
        return nombre
    if nombre not in MASCARAS:
        raise ValueError(
            f"máscara desconocida: {nombre!r}. Opciones: {', '.join(sorted(MASCARAS))}"
        )
    return MASCARAS[nombre](**kwargs)


def rasterizar(mascara: Mascara, ancho: int = 100, alto: int = 30,
               relleno: str = "#", vacio: str = "·") -> str:
    """
    Dibuja la máscara en ASCII: el ángulo en horizontal, la altura en vertical.

    Es el desenrollado de la superficie, o sea la pieza abierta y aplanada. La
    fila de arriba es el borde (t=1) y la de abajo la base (t=0).

    Sirve para ajustar una cara en milisegundos en vez de generar un gcode de
    35 000 líneas para descubrir que la boca quedó fuera del recuadro.
    """
    filas: List[str] = []
    for f in range(alto):
        t = 1.0 - f / (alto - 1)
        fila = "".join(
            relleno if mascara(c / ancho * TAU, t) > 0.5 else vacio
            for c in range(ancho)
        )
        filas.append(fila)
    return "\n".join(filas)


def _cli() -> None:
    """
    Ver una máscara en la terminal:

        python -m lamparas.superficie caritas
        python -m lamparas.superficie feliz --ancho-grados 100 --alto-t 0.7
        python -m lamparas.superficie triste --centrar

    Iterar acá cuesta milisegundos; iterar generando gcode cuesta minutos.
    """
    import argparse

    p = argparse.ArgumentParser(prog="lamparas.superficie", description=_cli.__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mascara", nargs="?", default="caritas", choices=sorted(MASCARAS))
    p.add_argument("--ancho-grados", type=float, default=140.0)
    p.add_argument("--centro-t", type=float, default=0.5)
    p.add_argument("--alto-t", type=float, default=0.55)
    p.add_argument("--cols", type=int, default=96, help="ancho del dibujo en caracteres")
    p.add_argument("--filas", type=int, default=32, help="alto del dibujo en caracteres")
    p.add_argument("--centrar", action="store_true",
                   help="rotar media vuelta, para que un dibujo que cae en 0° no quede "
                        "partido entre los dos bordes del desenrollado")
    args = p.parse_args()

    m = resolver(args.mascara, ancho_grados=args.ancho_grados,
                 centro_t=args.centro_t, alto_t=args.alto_t)
    if args.centrar:
        base = m
        m = lambda a, t: base((a + math.pi) % TAU, t)  # noqa: E731
    print(f"máscara '{args.mascara}' — la pieza desenrollada, 0°..360° de izquierda a derecha")
    print(rasterizar(m, ancho=args.cols, alto=args.filas))


if __name__ == "__main__":
    _cli()
