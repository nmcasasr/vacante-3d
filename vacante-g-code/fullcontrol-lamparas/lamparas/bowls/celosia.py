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


DE QUÉ TAMAÑO SALEN LOS AGUJEROS
--------------------------------

Con el desfase de medio nodo, la vuelta de arriba va en contrafase con la de
abajo, así que la separación vertical entre las dos, en función del ángulo, es

    hueco(θ) = paso_z - 2*amplitud_z*sin(f*θ)

que va de `paso_z - onda` (≈ 0, la soldadura) hasta `paso_z + onda` (≈ 2*paso_z).
O sea:

    alto del agujero  ≈ 2*paso_z - diámetro del cordón
    ancho del agujero ≈ s = 2*pi*radio / n_nodos

**El alto del agujero lo manda el PASO, no la amplitud.** Subir `amplitud_z` sin
tocar `solape` sube las dos cosas a la vez porque `paso_z` sale de ella; subir
`solape` sube la amplitud SIN subir el paso, y lo único que consigue es que la
boquilla are (ver `solape` más abajo).

Contra la referencia: `Squeezy Fidget Toy.gcode` tiene paso 0.945 y cordón de
0.80, o sea agujeros de 1.09 de alto por 8.5 de ancho — lentejas de 8:1. Para
arcos redondos como los de las fotos de claywoven hay que ir a agujeros de
proporción ~2:1, y eso pide paso grande y nodos anchos en la misma medida.


HASTA DÓNDE SE PUEDE SUBIR: LA BOQUILLA
---------------------------------------

El límite no es el material, es el cono de la boquilla. En la A1 mide unos 5 mm
de alto por 10 de ancho, o sea 45°: para bajar `d` por debajo de material ya
impreso hacen falta `d` mm de despeje horizontal.

El punto más comprometido es el valle, que es el más bajo de la vuelta: la
cresta anterior quedó `onda ≈ paso_z` más arriba y a media distancia de nodo,
`s/2`. Entonces

    s/2 >= paso_z      ->      s >= 2*paso_z

Con eso, el agujero más alto que entra sin chocar mide `2*paso_z - cordón` de
alto por `2*paso_z` de ancho: **el arco redondo, 1:1, es exactamente el límite
geométrico de la boquilla.** Todo lo más ancho que eso sobra de despeje; todo lo
más alto raspa.

Conviene dejar margen y trabajar en `s ≈ 3*paso_z` (arcos de 3 de ancho por 2 de
alto), que además es la proporción de las fotos de referencia.

Lo que sí empeora al agrandar todo es el descuelgue: el vano libre mide `s` y la
flecha crece con `s²`. La pendiente de subida, en cambio, NO empeora — con
`s = k*paso_z` el cordón sube `paso_z` en `s/4`, o sea una pendiente que sólo
depende de `k`. Por eso la escalera de pruebas se hace variando `paso_z` con `k`
fijo: lo único que se está probando es cuánto vano aguanta el PETG en el aire.
"""

import math
from typing import Optional, Tuple

from .siluetas import Silueta


def construir(
    silueta: Silueta,
    altura: float,
    n_nodos: int = 60,
    amplitud_z: float = 0.7,
    mordida: float = 0.07,
    ondulacion_radial: float = 0.0,
    solape: Optional[float] = None,
) -> Tuple[callable, Optional[callable], int, float]:
    """
    Args:
        silueta: radio medio en función de t.
        altura: altura total de la pared en mm (sin uso acá, va por uniformidad).
        n_nodos: cruces por vuelta. Más nodos = agujeros más chicos y tramos
            colgados más cortos, o sea más fácil de imprimir. Con 60 nodos y un
            radio de 55 mm, cada tramo al aire mide unos 5.8 mm.

            El número tiene un MÍNIMO que lo pone la boquilla, no el gusto. Ver
            el encabezado del módulo: `s >= 2*paso_z`, con `s` el ancho de nodo
            medido sobre la pared. En nodos, `n_nodos <= pi*radio/paso_z`.
        amplitud_z: cuánto sube y baja la boquilla dentro de la vuelta, en mm.
            Es lo que abre el calado.
        mordida: cuánto se encaja cada vuelta en la de abajo, EN MILÍMETROS.
            `paso_z = 2*amplitud_z - mordida`, así que es literalmente cuánto le
            sobresale la cresta de una vuelta al valle de la siguiente.

            Es una interferencia física entre dos cordones: vale lo mismo para
            un arco de 1 mm que para uno de 5. Medido en `Squeezy Fidget Toy`,
            el archivo que sí imprime bien: onda 1.010, paso 0.945, mordida
            0.065 mm. Un beso, lo justo para soldar.

            ANTES ESTO ERA UNA FRACCIÓN (`solape`) y era un error de modelo. Con
            `paso = onda*(1-solape)` la mordida crecía con el arco: el mismo
            `solape=0.065` daba 0.065 mm en la referencia y 0.174 mm en un arco
            de 2.5 de paso, y con `solape=0.30` —lo que usaba la caperuza— daba
            0.54 mm, o sea la boquilla arando media altura de cordón dentro de
            material ya impreso en CADA nodo. Es el mismo defecto que el
            empaquetador cazaba con "la boquilla choca contra la pieza, el peor
            1.02 mm dentro del material" al subir `amplitud_z` a 1.3.

            Comprobación: con mordida en mm, `verificar_choques` da cero choques
            en toda la escalera de arcos, igual que en la referencia. Con
            `solape` fraccionario daba 394 muestras en choque a paso 2.5.
        ondulacion_radial: amplitud de la onda RADIAL, en mm. Dejalo en 0 y se
            calcula solo, que es lo que querés casi siempre: sale la mitad de lo
            que se abre la pared por vuelta, que es justo lo que hace falta para
            que cresta y valle se encuentren en una pieza acampanada. Ver el
            comentario dentro de `radio`. Un valor explícito lo pisa, y sirve
            sólo si buscás relieve radial por estética.

    Returns:
        (funcion_radio, funcion_dz, segmentos_por_capa, paso_z)

    El `paso_z` que devuelve es la clave de este diseño: la pieza sube
    2*amplitud_z por vuelta en vez de una altura de capa. Con el paso normal,
    la cresta de una vuelta queda por debajo del valle de la anterior y la
    boquilla vuelve a bajar sobre material ya impreso.
    """
    if solape is not None:
        raise ValueError(
            "`solape` ya no existe: la mordida entre vueltas se da en MILÍMETROS "
            f"con `mordida`, no en fracción de la onda. Pasaste solape={solape}, "
            f"que con amplitud_z={amplitud_z} equivalía a mordida="
            f"{2 * amplitud_z * solape:.3f}. La referencia usa mordida=0.065."
        )
    frecuencia = n_nodos + 0.5  # el medio nodo invierte la onda vuelta a vuelta
    paso_z = 2 * amplitud_z - mordida

    def _avance_radial(t: float) -> float:
        """Cuánto se abre la pared de una vuelta a la siguiente, en mm."""
        h = 1e-3
        t0, t1 = max(0.0, t - h), min(1.0, t + h)
        if t1 <= t0 or altura <= 0:
            return 0.0
        pendiente = (silueta(t1) - silueta(t0)) / ((t1 - t0) * altura)
        return paso_z * pendiente

    def radio(angulo: float, t: float) -> float:
        # La onda radial NO es decoración: es lo que mantiene soldada la celosía
        # en una pared que se abre.
        #
        # El nudo se forma cuando la cresta de una vuelta y el valle de la
        # siguiente caen en el mismo sitio. En Z eso ya lo garantiza
        # `2*amplitud_z ≈ paso_z`. Pero en una pieza acampanada la vuelta de
        # arriba está además `Δr = paso_z * dr/dz` más AFUERA, así que cresta y
        # valle se cruzan desplazadas en radio: si `Δr` pasa del ancho del
        # cordón, sencillamente no se tocan y la pieza se deshilacha.
        #
        # Es el techo que hacía saltar "el radio crece 1.28 mm por vuelta y el
        # cordón mide 1.25: la vuelta nueva NO TOCA la anterior" apenas se subía
        # el paso en la caperuza, cuya pared se abre de r 48.8 a r 65.0.
        #
        # Con la onda radial en fase con la de Z y de amplitud `Δr/2`, la cresta
        # sale `Δr/2` hacia afuera y el valle de arriba entra `Δr/2` hacia
        # adentro, y las dos se encuentran en `R + Δr/2`. La celosía se inclina
        # con el cono en vez de resbalar sobre él, y el paso deja de estar
        # limitado por la apertura de la pieza.
        #
        # Un valor explícito de `ondulacion_radial` manda por encima de esto,
        # para el caso en que se quiera relieve radial por estética.
        c = ondulacion_radial if ondulacion_radial else _avance_radial(t) / 2
        if c:
            return silueta(t) + c * math.sin(frecuencia * angulo)
        return silueta(t)

    def dz(angulo: float, t: float) -> float:
        # La onda se apoya en el VALLE, no se centra en la vuelta: va de 0 a
        # 2*amplitud_z, no de -amplitud_z a +amplitud_z.
        #
        # No es cosmético. `comun` suma esto a `z_capa`, que es la altura a la
        # que llegó la vuelta anterior. Centrada, la primera vuelta de pared
        # hundía su valle `amplitud_z` POR DEBAJO del piso macizo: con paso 4.5
        # eran 2.29 mm de boquilla dentro del suelo, y `verificar_choques` lo
        # cazaba como 272 muestras GRAVES. Arriba se notaba menos porque el valle
        # caía sobre la cresta hueca de la vuelta anterior, pero era el mismo
        # error: el valle es el punto que SUELDA y tiene que quedar exactamente
        # sobre lo que ya está impreso, no medio arco más abajo.
        #
        # Apoyada en el valle, el arranque sale solo: los pies de la primera
        # vuelta se sueldan al piso y los arcos crecen hacia arriba. Y la
        # transición también, porque `mezcla` escala la onda entera y el valle se
        # queda en 0 sea cual sea la mezcla — las vueltas de transición son arcos
        # cada vez más altos con los pies siempre apoyados, en vez de una onda
        # centrada que se hunde más cuanto más crece.
        #
        # En régimen no cambia nada: desplazar TODAS las vueltas lo mismo deja
        # igual la relación entre la cresta de una y el valle de la siguiente,
        # que es la que define el nudo.
        return amplitud_z * (1 + math.sin(frecuencia * angulo))

    return radio, dz, max(240, int(n_nodos * 8)), paso_z
