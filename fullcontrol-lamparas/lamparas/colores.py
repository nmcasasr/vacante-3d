"""
Cambios de color sin purgar.

La idea: cortar la impresión, meter el filamento nuevo y seguir. Lo que quedaba
del color viejo en la zona de fusión sale mezclado con el nuevo durante las
primeras vueltas, y esa mezcla es justamente el efecto que se busca.

## Cuánto dura la mezcla

El color viejo no desaparece de golpe: hay que empujarlo fuera del bloque
caliente. Los números que reporta la comunidad, en milímetros de filamento
hasta que el color sale limpio:

    blanco -> negro     60-80 mm
    gris   -> azul      ~48 mm
    negro  -> blanco    250-300 mm

Tapar claro con oscuro es rápido; al revés cuesta cuatro veces más. Para saber
cuánta altura de pieza es eso, usá `altura_de_mezcla()`.

## Las dos formas de hacerlo

- `pausa_manual()`: la impresora para, cambiás el rollo con la mano y reanudás.
  Usa `M400 U1`, que es el comando nativo de pausa de Bambu (M600 no existe en
  estas máquinas). No toca el AMS, no purga nada y no depende de ningún comando
  propietario. Es la opción segura.

- `cambio_ams()`: dispara un cambio de slot del AMS. Los comandos del AMS NO
  están documentados por Bambu; lo de acá es el patrón que reconstruyó la
  comunidad y **no está verificado**. Leé el aviso de la función.
"""

import math
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .comun import Perfil


def pausa_manual(nota: str = "") -> str:
    """
    Bloque que pausa la impresión para cambiar el filamento a mano.

    `M400 U1` es el comando de pausa de Bambu: vacía la cola de movimientos y
    espera a que el usuario reanude desde la pantalla. La impresora aparca el
    cabezal y lo devuelve sola al reanudar, así que no hace falta guardar ni
    restaurar la posición.

    No purga nada. Lo que quede del color anterior en la boquilla se va a
    mezclar con el nuevo durante las primeras vueltas.
    """
    comentario = f"; {nota}\n" if nota else ""
    return (
        ";----- CAMBIO DE FILAMENTO (pausa manual) -----\n"
        f"{comentario}"
        "M400 U1 ; pausar y esperar al usuario\n"
        "M83 ; por las dudas: extrusión relativa al reanudar\n"
        ";----- FIN DEL CAMBIO -----"
    )


def cambio_ams(slot: int, nota: str = "") -> str:
    """
    Cambio de slot del AMS, sin purga.

    ⚠️ SIN VERIFICAR. Bambu nunca documentó los comandos del AMS. Este es el
    patrón que la comunidad reconstruyó a partir de gcode laminado:

        M620 S{slot}A   -> abre el cambio
        T{slot}         -> selecciona el filamento
        M621 S{slot}A   -> cierra el cambio

    El bloque real que emite Bambu Studio tiene además corte, limpieza y purga
    (`M620.10 ... L{flush}`), que es exactamente lo que acá se omite. No hay
    garantía de que la máquina acepte la versión reducida.

    **Antes de usar esto en una pieza, sacá el bloque real de un gcode de dos
    colores laminado por tu Bambu Studio y pasalo por `quitar_purga()`.** Es la
    única forma de tener los comandos que tu firmware espera de verdad.
    """
    comentario = f"; {nota}\n" if nota else ""
    return (
        ";----- CAMBIO DE FILAMENTO (AMS, sin purga) -----\n"
        "; OJO: secuencia no verificada, ver cambio_ams() en lamparas/colores.py\n"
        f"{comentario}"
        f"M620 S{slot}A\n"
        f"T{slot}\n"
        f"M621 S{slot}A\n"
        "M83 ; extrusión relativa\n"
        ";----- FIN DEL CAMBIO -----"
    )


def quitar_purga(bloque: str, umbral_e: float = 5.0) -> str:
    """
    Saca las líneas de purga de un bloque de cambio de filamento real.

    Pensado para el bloque que exporta Bambu Studio: se le quitan los
    movimientos que extruyen mucho (`G1 E...` por encima de `umbral_e` mm) y el
    `M620.10`, que es el que lleva la longitud de flush.

    **Revisá el resultado antes de usarlo.** La función no entiende el bloque,
    solo filtra por patrón; si tu firmware necesita alguna de esas líneas para
    completar el cambio, el cambio va a fallar. Imprime lo que sacó para que se
    pueda auditar.
    """
    import re

    salida, quitadas = [], []
    for linea in bloque.splitlines():
        limpia = linea.split(";")[0].strip()
        es_purga = False
        if limpia.startswith("M620.10"):
            es_purga = True
        else:
            m = re.match(r"^G1\b(?!.*\b[XYZ])(?=.*\bE(-?\d+\.?\d*))", limpia)
            if m and float(m.group(1)) > umbral_e:
                es_purga = True
        (quitadas if es_purga else salida).append(linea)

    if quitadas:
        print(f"quitar_purga(): {len(quitadas)} línea(s) removidas —")
        for l in quitadas:
            print(f"    {l}")
    else:
        print("quitar_purga(): no se encontró ninguna línea de purga que quitar.")
    return "\n".join(salida)


def altura_de_mezcla(mm_filamento: float, radio: float, perfil: Optional["Perfil"] = None) -> float:
    """
    Cuánta altura de pieza sube mientras el color todavía está mezclándose.

    Args:
        mm_filamento: cuánto filamento tarda el color nuevo en salir limpio
            (ver la tabla del módulo).
        radio: radio de la pieza a la altura del cambio, en mm.

    Returns:
        La altura en mm a lo largo de la cual se ve la mezcla.
    """
    from .comun import Perfil

    perfil = perfil or Perfil()
    area_filamento = math.pi * (perfil.diametro_filamento / 2) ** 2
    filamento_por_vuelta = (2 * math.pi * radio) * perfil.area_extrusion / area_filamento
    return (mm_filamento / filamento_por_vuelta) * perfil.altura_capa


def alturas_regulares(desde: float, hasta: float, cantidad: int) -> List[float]:
    """Reparte `cantidad` cambios entre dos alturas, para encadenar un degradado."""
    if cantidad < 1:
        return []
    if cantidad == 1:
        return [(desde + hasta) / 2]
    paso = (hasta - desde) / (cantidad - 1)
    return [desde + i * paso for i in range(cantidad)]
