"""
Deformaciones de la ESTRUCTURA: los bultos grandes que doblan el cuerpo entero.

Es otra escala que los patrones de `bowls/`. Un patrón es textura —décimas de
milímetro, muchos ciclos por vuelta, se ve de cerca. Una deformación de
estructura son varios milímetros y uno o dos ciclos en toda la pieza: cambia la
silueta, y las líneas de capa la revelan al curvarse alrededor.

Y por eso mismo se COMBINAN en vez de competir: la estructura mueve el cuerpo,
el patrón raya la superficie de ese cuerpo. Una deformación se suma encima del
radio que devuelva el patrón que sea, sin que el patrón se entere:

    radio_final(a, t) = patron(a, t) + deformacion(a, t)

Ver `bowls/__init__.pasos_bowl(deformacion=...)`.

## Por qué se anula arriba y abajo

Todos los modos van con `sin(k·π·t)`, que vale 0 en `t=0` y en `t=1`. O sea que
la deformación nace y muere sola: la base queda plana y redonda para apoyar en
la cama, y la boca también. Sin eso, un bulto en la primera capa levanta la
pieza de un lado, y un bulto en la boca deja un borde ondulado que se ve
descuidado en vez de intencional.
"""

import math
from typing import Callable

# (angulo_rad, t) -> cuánto se corre el radio en mm, positivo hacia afuera
Deformacion = Callable[[float, float], float]


def _fases(semilla: int, n: int):
    """
    Fases y frecuencias reproducibles a partir de una semilla.

    Generador propio y no `random`: así la misma semilla da la misma pieza en
    cualquier máquina y en cualquier versión de Python, que es lo que uno
    quiere cuando encontró un bulto que le gusta y lo quiere volver a imprimir.
    """
    x = (semilla * 2654435761 + 1013904223) & 0xFFFFFFFF
    for _ in range(n):
        x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
        yield x / 0xFFFFFFFF


def _valor(ix: int, iy: int, nu: int, semilla: int) -> float:
    """
    Ruido de valor en un punto de la grilla, en [-1, 1].

    `ix` se toma módulo `nu` — o sea que la grilla es PERIÓDICA alrededor del
    eje. Sin eso el ruido no cierra en 0°/360° y queda una costura vertical
    visible en toda la altura de la pieza, que es el error clásico al mapear
    ruido sobre un sólido de revolución.
    """
    x = (ix % nu) * 374761393 + iy * 668265263 + semilla * 2147483647
    x = (x ^ (x >> 13)) & 0xFFFFFFFF
    x = (x * 1274126177) & 0xFFFFFFFF
    x = (x ^ (x >> 16)) & 0xFFFFFFFF
    return (x / 0x7FFFFFFF) - 1.0


def _suave(a: float, b: float, t: float) -> float:
    """Interpolación con smoothstep: derivada 0 en los extremos, sin aristas."""
    s = t * t * (3 - 2 * t)
    return a + (b - a) * s


def _ruido(u: float, v: float, nu: int, nv: int, semilla: int) -> float:
    """Ruido de valor 2D, periódico en `u` (el ángulo) y no en `v` (la altura)."""
    fu, fv = u * nu, v * nv
    iu, iv = math.floor(fu), math.floor(fv)
    du, dv = fu - iu, fv - iv
    a = _suave(_valor(iu, iv, nu, semilla), _valor(iu + 1, iv, nu, semilla), du)
    b = _suave(_valor(iu, iv + 1, nu, semilla), _valor(iu + 1, iv + 1, nu, semilla), du)
    return _suave(a, b, dv)


def arrugas(
    amplitud: float = 1.6,
    escala: int = 5,
    octavas: int = 4,
    persistencia: float = 0.55,
    semilla: int = 0,
    borde: float = 0.10,
) -> Deformacion:
    """
    Pliegues finos por toda la superficie, tipo papel arrugado o tela apretada.

    Es otra cosa que `hoyuelos()`, y la diferencia se ve enseguida: un hoyuelo
    es UN hundido con un centro y un borde, y se leen como puntos sueltos. Una
    arruga no tiene centro — es una cresta que corre, se bifurca y se apaga.
    Eso no sale de sumar gaussianas: sale de ruido fractal, varias octavas de
    ruido suave, cada una del doble de frecuencia y con menos amplitud.

    La octava gruesa da las ondulaciones grandes y las finas les agregan los
    quiebres. Bajar `persistencia` deja la superficie más suave; subirla la
    vuelve áspera.

    El ruido es **periódico en el ángulo**: si no, no cierra en la costura y
    queda una línea vertical marcada a lo largo de toda la pieza.

    Args:
        amplitud: cuánto se mete o sale la pared, en mm. 1.5-2 es la referencia.
        escala: cuántas celdas de ruido entran en una vuelta, en la octava más
            gruesa. Más = arrugas más chicas.
        octavas: cuántos niveles de detalle se suman. 4 alcanza; más no se ve.
        persistencia: cuánta amplitud conserva cada octava respecto de la
            anterior. 0.5 = suave, 0.7 = áspero.
        semilla: cambiala para otra pieza con el mismo carácter.
        borde: fracción de la altura, arriba y abajo, donde las arrugas se
            apagan. Deja la base plana para apoyar y la boca limpia.

    Returns:
        Una `Deformacion`.
    """
    if octavas < 1:
        raise ValueError("`octavas` tiene que ser >= 1")

    capas = []
    amp, nu, nv = 1.0, max(2, escala), max(2, escala)
    total = 0.0
    for o in range(octavas):
        capas.append((amp, nu, nv, semilla + o * 101))
        total += amp
        amp *= persistencia
        nu *= 2
        nv *= 2

    def deformacion(angulo: float, t: float) -> float:
        u = (angulo % (2 * math.pi)) / (2 * math.pi)
        n = 0.0
        for a, nu_, nv_, sem in capas:
            n += a * _ruido(u, min(max(t, 0.0), 1.0), nu_, nv_, sem)
        n /= total
        # Apagado suave en la base y en la boca.
        env = 1.0
        if t < borde:
            env = t / borde
        elif t > 1 - borde:
            env = (1 - t) / borde
        env = env * env * (3 - 2 * env)
        return amplitud * n * env

    return deformacion


def hoyuelos(
    cantidad: int = 9,
    amplitud: float = 3.0,
    ancho_grados: float = 55.0,
    alto: float = 0.12,
    semilla: int = 0,
    hacia_adentro: float = 0.6,
) -> Deformacion:
    """
    Bultos y hundidos LOCALIZADOS, como dedos apretando la pieza en puntos sueltos.

    La diferencia con `bultos()` importa y es la que me costó ver: `bultos()`
    suma senoidales GLOBALES, o sea `sin(n·ángulo)`, y una senoidal ocupa toda
    la vuelta — da unos pocos lóbulos amplios y simétricos, una pieza que
    "respira" pareja. Un hundido de verdad es LOCAL: hay un punto donde la
    pared se mete y a 40° de ahí ya no pasa nada. Eso no se puede escribir como
    una senoidal de baja frecuencia, hay que ponerlo donde va.

    Cada hoyuelo es una gaussiana en (ángulo, altura), así que decae suave y no
    deja borde. La envolvente `sin(π·t)` los apaga en la base y en la boca, por
    lo mismo que en `bultos()`.

    Args:
        cantidad: cuántos hoyuelos se reparten por la pieza.
        amplitud: cuánto mete o saca cada uno, en mm.
        ancho_grados: qué tan ancho es cada uno alrededor. 55° da hundidos que
            se leen sueltos; con 120° se pisan entre sí y vuelve a parecer
            `bultos()`.
        alto: qué fracción de la altura ocupa cada uno.
        semilla: cambiala para otra distribución con el mismo carácter.
        hacia_adentro: fracción de hoyuelos que hunden en vez de sobresalir.
            0.6 = mayoría hundidos, que es lo que da el aspecto de tela
            apretada en vez de globo inflado.

    Returns:
        Una `Deformacion`.
    """
    if cantidad < 1:
        raise ValueError("`cantidad` tiene que ser >= 1")

    r = _fases(semilla, cantidad * 4)
    puntos = []
    for _ in range(cantidad):
        centro_a = next(r) * 2 * math.pi
        centro_t = 0.12 + next(r) * 0.76      # nunca pegados a la base ni a la boca
        signo = -1.0 if next(r) < hacia_adentro else 1.0
        escala = 0.6 + next(r) * 0.8          # que no salgan todos del mismo tamaño
        puntos.append((centro_a, centro_t, signo, escala))

    sigma_a = math.radians(ancho_grados) / 2
    sigma_t = alto / 2

    def deformacion(angulo: float, t: float) -> float:
        total = 0.0
        for centro_a, centro_t, signo, escala in puntos:
            da = (angulo - centro_a + math.pi) % (2 * math.pi) - math.pi
            dt = t - centro_t
            e = (da / sigma_a) ** 2 + (dt / sigma_t) ** 2
            if e > 12:            # más allá de ~3.5 sigmas no aporta nada
                continue
            total += signo * escala * amplitud * math.exp(-e / 2)
        return total * math.sin(math.pi * t)

    return deformacion


def bultos(
    modos: int = 3,
    amplitud: float = 4.0,
    semilla: int = 0,
    n_max: int = 3,
    k_max: int = 3,
) -> Deformacion:
    """
    Bultos suaves y orgánicos: suma de unos pocos modos de baja frecuencia.

    Cada modo es `sin(n·ángulo + φ) · sin(k·π·t)` con `n` y `k` chicos, así que
    lo que sale son unas pocas panzas y hundidos amplios, no una superficie
    rugosa. Subir `modos` no hace bultos más chicos sino más irregulares.

    Args:
        modos: cuántos modos se suman. 1 da una pieza que solo se inclina; 3-4
            es el "tela colgando" de la referencia; más de 6 se emparejan entre
            sí y la pieza vuelve a parecer redonda.
        amplitud: cuánto se corre el radio como máximo, en mm. Es el total, se
            reparte entre los modos.
        semilla: cambiala para obtener otra pieza con el mismo carácter.
        n_max: frecuencia angular máxima. 3 = a lo sumo tres panzas alrededor.
        k_max: frecuencia vertical máxima. 3 = a lo sumo tres a lo alto.

    Returns:
        Una `Deformacion`.
    """
    if modos < 1:
        raise ValueError("`modos` tiene que ser >= 1")

    r = _fases(semilla, modos * 3)
    partes = []
    for _ in range(modos):
        n = 1 + int(next(r) * n_max)          # 1..n_max panzas alrededor
        k = 1 + int(next(r) * k_max)          # 1..k_max a lo alto
        fase = next(r) * 2 * math.pi
        partes.append((n, k, fase))

    peso = amplitud / modos

    def deformacion(angulo: float, t: float) -> float:
        total = 0.0
        for n, k, fase in partes:
            total += peso * math.sin(n * angulo + fase) * math.sin(k * math.pi * t)
        return total

    return deformacion


def ninguna() -> Deformacion:
    """Sin deformación. Para poder pedir 'nada' desde la línea de comandos."""
    return lambda angulo, t: 0.0


ESTRUCTURAS = {
    "bultos": bultos,
    "hoyuelos": hoyuelos,
    "arrugas": arrugas,
    "ninguna": lambda **kw: ninguna(),
}


def resolver(nombre, **kwargs) -> Deformacion:
    """Convierte el nombre que llega por `--estructura` en una `Deformacion`."""
    if callable(nombre):
        return nombre
    if nombre not in ESTRUCTURAS:
        raise ValueError(
            f"estructura desconocida: {nombre!r}. Opciones: {', '.join(sorted(ESTRUCTURAS))}"
        )
    return ESTRUCTURAS[nombre](**kwargs)
