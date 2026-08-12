"""
Bowls con patrones tejidos, generados por gcode.

Los cuatro diseños comparten toda la infraestructura (silueta, base sólida,
modo vaso, exportación) y se diferencian solo en el patrón:

- `cesta`   -> trenzado de cestería, tejas horizontales alternadas
- `malla`   -> malla fina de rombos
- `celosia` -> calado real, con agujeros pasantes
- `tramado` -> entramado diagonal, una tira pasa por encima de la otra
- `rizos`   -> bucles que sobresalen, tipo candelero "Dream of Glow"
- `zigzag`  -> textura en diente de sierra que dibuja una máscara (ver superficie.py)
- `ondas`   -> anillos horizontales ondulados, tipo cerámica torneada

Ninguno de los cuatro se puede hacer con un slicer: los tres primeros porque el
patrón cambia dentro de cada vuelta y de una vuelta a la otra, y la celosía
porque además mueve la Z dentro de la capa.
"""

from typing import Optional

from ..comun import Perfil, a_gcode, generar_pieza, guardar_gcode
from . import celosia, cesta, malla, ondas, rizos, siluetas, tramado, zigzag
from .siluetas import SILUETAS

DISENOS = {
    "cesta": cesta,
    "malla": malla,
    "celosia": celosia,
    "tramado": tramado,
    "rizos": rizos,
    "zigzag": zigzag,
    "ondas": ondas,
}


def pasos_bowl(
    diseno: str = "cesta",
    silueta = "bol",
    altura: float = 60.0,
    perfil: Optional[Perfil] = None,
    parametros: Optional[dict] = None,
    parametros_silueta: Optional[dict] = None,
    segmentos_por_capa: Optional[int] = None,
    base_solida: bool = True,
    hueco: float = 0.0,
    refuerzo_hueco: int = 0,
    capas_transicion: int = 6,
    capas_base: int = 1,
    cambios: Optional[dict] = None,
    modulacion: Optional[dict] = None,
    pintura: Optional[dict] = None,
    deformacion=None,
) -> list:
    """
    Arma los pasos de FullControl de un bowl.

    Args:
        diseno: uno de `DISENOS` ('cesta', 'malla', 'celosia', 'tramado').
        silueta: una de `SILUETAS` ('bol', 'copa', 'platillo', 'campana').
        altura: altura de la pared en mm (sin contar el espesor de la base).
        perfil: parámetros de impresión.
        parametros: kwargs propios del patrón (ver el `construir()` de cada uno).
        parametros_silueta: kwargs de la silueta (radio_base, radio_boca, ...).
        segmentos_por_capa: si es None se usa el que recomienda el patrón, que
            sale de su cantidad de lóbulos.
        base_solida: rellena el fondo. False deja el bowl abierto abajo.
        cambios: {altura_mm: bloque} para cambiar de color (ver colores.py).
        deformacion: `(angulo, t) -> mm`, los bultos grandes de la estructura.
            Se suma encima del patrón. Ver `lamparas/estructura.py`.
        capas_transicion: capas en las que el patrón nace desde un círculo liso.
        capas_base: primeras vueltas sin rampa de Z (anillos cerrados), para que
            el calado arranque desde algo macizo en vez de desde un solo cordón.
    """
    if diseno not in DISENOS:
        raise ValueError(f"diseño desconocido: {diseno!r}. Opciones: {sorted(DISENOS)}")
    # `silueta` puede venir ya hecha —la que sale de un DXF, ver
    # lamparas/perfil.py— o ser el nombre de una del catálogo. Los patrones no
    # notan la diferencia: reciben `radio(t)` y nada más.
    if callable(silueta):
        fn_silueta = silueta
    else:
        if silueta not in SILUETAS:
            raise ValueError(f"silueta desconocida: {silueta!r}. Opciones: {sorted(SILUETAS)}")
        fn_silueta = SILUETAS[silueta](**(parametros_silueta or {}))
    # Contrato de construir(): devuelve al menos
    #   (funcion_radio, funcion_dz, segmentos, paso_z)
    # y opcionalmente un quinto elemento, funcion_dangulo, que solo usan los
    # patrones cuyo trazo vuelve sobre sí mismo (rizos).
    resultado = DISENOS[diseno].construir(fn_silueta, altura=altura, **(parametros or {}))
    fn_radio, fn_dz, segmentos, paso_z = resultado[:4]
    fn_dangulo = resultado[4] if len(resultado) > 4 else None

    # La deformación de estructura se suma ENCIMA del radio que devolvió el
    # patrón, envolviéndolo. Así compone con todos los patrones sin que ninguno
    # tenga que enterarse, y con cualquier combinación futura. Ver
    # `lamparas/estructura.py`.
    if deformacion is not None:
        patron = fn_radio
        # Casi ninguna deformación necesita ver el radio de abajo; `aplanar` sí,
        # porque lo que hace es llevarlo a un valor. Se lo enchufa acá, que es el
        # único punto donde el patrón ya está armado y todavía no se generó nada.
        if getattr(deformacion, "necesita_patron", False):
            deformacion.patron = patron
        fn_radio = lambda a, t: patron(a, t) + deformacion(a, t)  # noqa: E731

    return generar_pieza(
        fn_radio,
        altura=altura,
        perfil=perfil,
        segmentos_por_capa=segmentos_por_capa or segmentos,
        funcion_dz=fn_dz,
        funcion_dangulo=fn_dangulo,
        base_solida=base_solida,
        hueco=hueco,
        refuerzo_hueco=refuerzo_hueco,
        capas_transicion=capas_transicion,
        capas_base=capas_base,
        cambios=cambios,
        modulacion=modulacion,
        pintura=pintura,
        paso_z=paso_z,
        # el voladizo se mide sobre la silueta lisa: el relieve del patrón hace
        # oscilar el radio medio y daría falsas alarmas
        silueta_referencia=fn_silueta,
    )


def generar_bowl(nombre: Optional[str] = None, guardar: bool = True, **kwargs) -> str:
    """
    Genera el gcode de un bowl y lo deja en `output/`.

    Acepta los mismos argumentos que `pasos_bowl()`. Devuelve el gcode.
    """
    perfil = kwargs.get("perfil")
    pasos = pasos_bowl(**kwargs)
    gcode = a_gcode(pasos, perfil)
    if guardar:
        nombre = nombre or f"bowl_{kwargs.get('diseno', 'cesta')}"
        ruta = guardar_gcode(gcode, nombre)
        print(f"Generado: {ruta} ({len(pasos)} pasos, {len(gcode.splitlines())} líneas)")
    return gcode


__all__ = ["DISENOS", "SILUETAS", "pasos_bowl", "generar_bowl", "siluetas"]
