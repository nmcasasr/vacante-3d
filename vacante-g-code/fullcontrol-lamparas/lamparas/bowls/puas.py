"""
Tubo cubierto de púas: la boquilla sale y entra en cada púa, y el dibujo
aparece donde las púas se apagan.

Es la lámpara de referencia. Vista de lejos parece un tejido o un cepillo;
de cerca son cientos de columnas de material que sobresalen de la pared, y
las flores no están pintadas ni caladas: **están lisas**. Es el mismo truco
de `bowls/zigzag.py` —la figura se dibuja cambiando la PIEL y no el color—
llevado a una textura mucho más densa. Ver `lamparas/superficie.py`.

## Qué hace distinto a `zigzag`

`zigzag` ondula el radio con un triángulo y alterna una vuelta con dientes y
otra lisa: el cordón liso de arriba marca el borde de los de abajo y se lee
como una raya. Acá se busca lo contrario, una púa que se APILE:

- La onda va **solo hacia afuera**. El valle vale exactamente la silueta, así
  que la superficie interior queda limpia y todo el relieve se va para afuera,
  que es lo que se ve en la referencia: por dentro el tubo es liso.
- **Todas las vueltas llevan púa y en la misma fase** (`deriva` en 0). Cada púa
  cae encima de la de la vuelta anterior y se apilan en una columna continua.
  Alternando, no habría columna: habría raya.
- El perfil es un **pulso trapecial**, no un triángulo. `ocupacion` dice qué
  fracción de cada paso ocupa la púa: con 0.5 la mitad del recorrido va afuera
  y la otra mitad pegada a la pared, que es lo que separa una púa de la
  siguiente. Un triángulo no separa nada — es una pared ondulada.

## La trampa que hay que respetar: el borde de la figura

En modo vaso el paso vertical es UNO SOLO por vuelta, y `comun.marcha_vertical`
lo achica hasta que la separación real vuelva a valer un cordón, mirando el
PEOR ángulo de la vuelta (ver `.agents/MAPA.md`). El borde de una flor es el
sitio donde la púa deja de existir: si ese borde es duro, dos vueltas vecinas
se llevan la amplitud entera de diferencia en ese ángulo, `marcha_vertical` lo
lee como una pared acostada y desploma el paso de LA PIEZA ENTERA al mínimo.

Por eso la máscara `flores` desvanece su borde en milímetros de superficie y
`construir()` mide el salto por vuelta antes de generar nada y avisa. No es
una precaución teórica: es el mismo mecanismo que en `glitch2` dejó el 26 % de
los cordones irrealizables.

Y por eso `deriva` viene en 0. Torcer las columnas significa que la púa de una
vuelta ya no cae sobre la de la vuelta anterior, o sea el salto entero de
amplitud en cada vuelta, en todos los ángulos a la vez. El módulo lo mide y lo
dice.
"""

import math
from typing import Optional, Tuple

from ..superficie import Mascara, resolver
from .siluetas import Silueta

TAU = 2 * math.pi


def _pulso(u: float, ocupacion: float, filo: float) -> float:
    """
    Perfil de una púa. `u` es la fase dentro del paso, en [0, 1).

    Vale 0 pegado a la pared y 1 en la punta. `ocupacion` es qué fracción del
    paso ocupa la púa y `filo` qué parte de esa fracción va en la meseta: con
    `filo=1` el flanco es vertical —la boquilla sale de golpe— y con `filo=0`
    la púa es un triangulito.
    """
    if u >= ocupacion:
        return 0.0
    meseta = ocupacion * filo
    rampa = (ocupacion - meseta) / 2
    if rampa <= 1e-9:
        return 1.0
    if u < rampa:
        return u / rampa
    if u < rampa + meseta:
        return 1.0
    return (ocupacion - u) / rampa


def _ventana(t: float, desde: float, hasta: float, suave: float) -> float:
    """
    0 fuera de la banda [desde, hasta], 1 adentro, con rampas suaves.

    `suave` viene en unidades de `t`, pero quien lo llama lo calcula desde
    MILÍMETROS y por un motivo físico, no estético: la rampa es una zona donde
    la púa crece de vuelta en vuelta, o sea exactamente el salto de radio que
    `marcha_vertical` mira para decidir el paso. Un "3 % de la altura" mide
    6 mm en un tubo de 200 y 0.7 mm en una prueba de 24 — dos vueltas— y ahí es
    un escalón duro que aplasta el paso de la prueba entera. Con la rampa en
    mm, la prueba chica se comporta como la pieza grande, que es justo para lo
    que sirve una prueba.
    """
    if t <= desde or t >= hasta:
        return 0.0
    subida = min(1.0, (t - desde) / suave) if suave > 0 else 1.0
    bajada = min(1.0, (hasta - t) / suave) if suave > 0 else 1.0
    u = min(subida, bajada)
    return u * u * (3 - 2 * u)


def construir(
    silueta: Silueta,
    altura: float,
    puas: int = 150,
    amplitud: float = 0.9,
    ocupacion: float = 0.5,
    filo: float = 0.34,
    muestras: int = 6,
    mascara="flores",
    invertir: int = 1,
    suave_borde: float = 5.0,
    tomas: int = 5,
    deriva: float = 0.0,
    desde: float = 0.03,
    hasta: float = 0.99,
    suave_mm: float = 5.0,
    altura_capa: float = 0.4,
    **par_mascara,
) -> Tuple[callable, Optional[callable], int, Optional[float]]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura de la pared en mm.
        puas: cuántas púas entran en una vuelta. Lo que importa de verdad es el
            PASO que resulta, `2·pi·radio / puas`: por debajo de un cordón las
            púas vecinas se funden y vuelve a ser una pared ondulada. El módulo
            imprime el paso en mm para que no haya que hacer la cuenta.
        amplitud: cuánto sobresale la púa, en mm.
        ocupacion: qué fracción del paso ocupa la púa (0..1). 1 no deja valle:
            las púas se tocan y la textura desaparece. Se llama así y no
            "ancho" porque `--ancho-linea` ya es un ancho en mm y son cosas
            distintas: esto es una fracción del paso entre púas.
        filo: qué parte de la púa es meseta. 1 = flancos verticales.
        muestras: puntos de recorrido por púa. Con 6 y `ocupacion=0.5` el muestreo
            cae justo en los vértices del trapecio y la púa sale cuadrada; con
            menos, redondeada. Es lo que fija la resolución angular, así que
            también es lo que fija el tamaño del archivo.
        mascara: dónde va la figura. Por defecto 'flores'. Para mirar la
            textura sola, sin figura: `mascara=ninguna invertir=0`.
        invertir: 1 = la figura es la zona LISA y la púa es el fondo, que es lo
            que hace la pieza de referencia. 0 = al revés.
        suave_borde: en cuántos mm de ALTURA se desvanece el borde de la figura,
            y `tomas` con cuántas muestras. No es un parámetro estético: es lo
            que acota el salto de radio por vuelta. Ver abajo.
        deriva: vueltas que rota la textura a lo largo de la altura. **Dejalo en
            0**; ver el docstring del módulo.
        desde, hasta: en qué tramo de la altura (0..1) hay púas. El zócalo liso
            de abajo no es decorativo: es donde la pieza se agarra a la cama.
        suave_mm: en cuántos MILÍMETROS de altura encienden y apagan esas dos
            rampas. En mm y no en fracción a propósito: ver `_ventana`.
        altura_capa: solo para el aviso — cuánto sube una vuelta. No cambia la
            pieza, la altura real la fija `--altura-capa`.
        **par_mascara: se le pasan a la máscara (para 'flores': cantidad,
            petalos, tamano, corazon, borde_mm, semilla...).

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    `funcion_dz` y `paso_z` son None: la Z no se toca, así que la pared sube
    como una capa normal y el tubo queda estanco.
    """
    radio_medio = sum(silueta(k / 8) for k in range(9)) / 9
    fn: Mascara = resolver(mascara, radio_mm=radio_medio, altura_mm=altura,
                           **par_mascara)

    ocupacion = min(1.0, max(0.02, ocupacion))
    filo = min(1.0, max(0.0, filo))

    # --- el borde de la figura, promediado EN VERTICAL --------------------
    #
    # El problema, medido: con la máscara evaluada punto a punto, el borde de
    # una flor movía el radio 0.550 mm de una vuelta a la siguiente, y eso hace
    # que `marcha_vertical` achique el paso de la pieza ENTERA (el paso es uno
    # solo por vuelta). El culpable no era el desvanecido de la máscara sino la
    # muesca entre dos pétalos: ahí el contorno corre casi horizontal, así que
    # subir 0.4 mm lo corre 1.7 mm de costado y se come cualquier borde suave
    # que la máscara declare en el plano.
    #
    # Suavizar más la máscara no lo arregla —la cuenta da que harían falta
    # ~11 mm de desvanecido, o sea una flor sin contorno— y depende de la forma
    # de cada figura, así que el próximo dibujo volvería a romperlo.
    #
    # Lo que se hace en cambio es promediar la máscara a lo largo de `tomas`
    # alturas repartidas en `suave_borde` milímetros. Eso ACOTA POR
    # CONSTRUCCIÓN cuánto puede cambiar el peso al subir una vuelta —como mucho
    # lo que aporte una toma— sea cual sea la figura, y deja intactos los bordes
    # VERTICALES, que no cuestan nada porque el ángulo no cambia entre vueltas.
    # Es, además, lo que se ve en la pieza de referencia: las púas se van
    # acortando al acercarse a la flor en vez de cortarse de golpe.
    n = max(1, int(tomas))
    dt_borde = (suave_borde / max(altura, 1e-9)) / n if n > 1 else 0.0
    desplazamientos = [(k - (n - 1) / 2) * dt_borde for k in range(n)]

    def peso(angulo: float, t: float) -> float:
        m = 0.0
        for d in desplazamientos:
            m += fn(angulo, min(1.0, max(0.0, t + d)))
        m /= n
        if invertir:
            m = 1.0 - m
        return m * _ventana(t, desde, hasta, suave_mm / max(altura, 1e-9))

    def radio(angulo: float, t: float) -> float:
        p = peso(angulo, t)
        if p <= 0.0:
            return silueta(t)
        fase = angulo * puas / TAU + deriva * t * puas
        return silueta(t) + amplitud * p * _pulso(fase % 1.0, ocupacion, filo)

    _avisar(silueta, altura, radio_medio, peso, puas, amplitud, deriva, altura_capa)

    return radio, None, max(120, puas * max(3, muestras)), None


def _avisar(silueta, altura, radio_medio, peso, puas, amplitud, deriva,
            altura_capa) -> None:
    """
    Los dos números que deciden si esto se imprime, medidos antes de generar.

    Están acá y no en un verificador aparte porque los dos se contestan con la
    función de radio y sin gcode: esperar al gcode para enterarse cuesta
    minutos, y el veredicto sería el mismo.
    """
    paso_mm = TAU * radio_medio / max(puas, 1)
    print(f"Púas: {puas} por vuelta sobre radio ~{radio_medio:.1f} mm -> "
          f"paso {paso_mm:.2f} mm, {amplitud:.2f} mm de vuelo.")
    if paso_mm < 1.0:
        print(f"  AVISO: con un paso de {paso_mm:.2f} mm las púas vecinas se funden "
              f"con cualquier cordón de 0.8 o más. Bajá `puas` o subí el radio.")

    # Cuánto se corre el radio de una vuelta a la siguiente por culpa del
    # BORDE de la figura, en el peor punto de la pieza. Es exactamente lo que
    # `comun.marcha_vertical` va a mirar para decidir el paso vertical.
    N_A, N_T = 240, 300
    dt = altura_capa / max(altura, 1e-9)
    peor = 0.0
    for i in range(N_T):
        t = i / (N_T - 1)
        t2 = min(1.0, t + dt)
        for k in range(N_A):
            a = k / N_A * TAU
            peor = max(peor, abs(peso(a, t2) - peso(a, t)))
    salto = peor * amplitud
    # la silueta también se corre; se informa junta, que es como la ve el paso
    salto_silueta = max(abs(silueta(min(1.0, i / 200 + dt)) - silueta(i / 200))
                        for i in range(201))
    print(f"  borde de la figura: {salto:.3f} mm de radio por vuelta de "
          f"{altura_capa:.2f} mm (la silueta aporta {salto_silueta:.3f}).")
    if deriva:
        print(f"  AVISO: `deriva={deriva:g}` desalinea las púas entre vueltas. "
              f"Eso mete un salto de hasta {amplitud:.2f} mm en TODOS los ángulos, "
              f"no solo en el borde de la figura, y el paso vertical se desploma.")
    if salto > 0.25:
        print(f"  AVISO: {salto:.3f} mm por vuelta es mucho. `marcha_vertical` "
              f"acorta el paso de TODA la pieza hasta que la separación vuelva a "
              f"valer un cordón, así que un borde duro en una flor se paga en la "
              f"pieza entera. Subí `borde` en la máscara o bajá `amplitud`.")
